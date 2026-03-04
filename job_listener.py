#!/usr/bin/env python3
"""Poll the Prompter API for new instructions.

Downloads these files for the given area (front-end/back-end/testing):
  - instructions.md
  - completed_instructions.md

It compares remote contents to the last-downloaded local copies and only
writes to disk when the contents changed.

Example:
  python job_listener.py front-end --base-url http://localhost:3050
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

import requests


FILES = ("instructions.md", "completed_instructions.md")
PI_TOOLS = "read,bash,edit,write"


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_area(area: str) -> str:
    a = area.strip().lower()
    aliases = {
        "frontend": "front-end",
        "front-end": "front-end",
        "front_end": "front-end",
        "fe": "front-end",
        "backend": "back-end",
        "back-end": "back-end",
        "back_end": "back-end",
        "be": "back-end",
        "testing": "testing",
        "test": "testing",
        "qa": "testing",
    }
    if a not in aliases:
        raise ValueError(
            f"Invalid area '{area}'. Expected one of: front-end, back-end, testing."
        )
    return aliases[a]


def read_text_if_exists(path: str) -> str | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def fetch_files(base_url: str, project: str, area: str, timeout_s: int = 10) -> Dict[str, str]:
    base_url = base_url.rstrip("/")
    out: Dict[str, str] = {}

    for name in FILES:
        url = f"{base_url}/api/instructions/{project}/{area}/{name}"
        resp = requests.get(url, timeout=timeout_s)
        resp.raise_for_status()
        out[name] = resp.text

    return out


def compare_and_write(downloaded: Dict[str, str], out_dir: str, area: str) -> Tuple[bool, Dict[str, bool]]:
    """Return (any_changed, per_file_changed)."""

    any_changed = False
    per_file: Dict[str, bool] = {}

    for name, remote_text in downloaded.items():
        local_path = os.path.join(out_dir, area, name)
        local_text = read_text_if_exists(local_path)
        changed = local_text != remote_text
        per_file[name] = changed

        if changed:
            write_text(local_path, remote_text)
            any_changed = True

    return any_changed, per_file


def run_pi(instructions_path: str) -> int:
    """Run pi against the given instructions.md path."""

    cmd = [
        "pi",
        "-p",
        "--no-session",
        "--tools",
        PI_TOOLS,
        instructions_path,
    ]

    print(f"[{_utc_ts()}] Running: {' '.join(cmd)}")

    try:
        proc = subprocess.run(cmd, text=True, capture_output=True)
    except FileNotFoundError:
        print(f"[{_utc_ts()}] Error: 'pi' command not found in PATH", file=sys.stderr)
        return 127

    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)

    if proc.returncode != 0:
        print(f"[{_utc_ts()}] pi exited with status {proc.returncode}", file=sys.stderr)

    return proc.returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Poll the Prompter API for instructions.md updates")
    p.add_argument(
        "area",
        help="Which area to listen for (front-end, back-end, testing)",
    )
    p.add_argument(
        "--base-url",
        default=os.environ.get("PROMPTER_BASE_URL", "http://localhost:3050"),
        help="Prompter API base URL (default: http://localhost:3050). Can also set PROMPTER_BASE_URL.",
    )
    p.add_argument(
        "--project",
        default=os.environ.get("PROMPTER_PROJECT", "default"),
        help="Project name used for persistence (default: default). Can also set PROMPTER_PROJECT.",
    )
    p.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("PROMPTER_POLL_INTERVAL", "60")),
        help="Polling interval in seconds (default: 60). Can also set PROMPTER_POLL_INTERVAL.",
    )
    p.add_argument(
        "--output-dir",
        default=os.environ.get("PROMPTER_OUTPUT_DIR", ".job_listener"),
        help="Where to store downloaded files (default: .job_listener). Can also set PROMPTER_OUTPUT_DIR.",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll and exit (no loop).",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        area = normalize_area(args.area)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    base_url: str = args.base_url
    project: str = (args.project or "default").strip() or "default"
    interval: int = max(1, int(args.interval))
    out_dir: str = args.output_dir

    print(
        f"[{_utc_ts()}] Listening for '{project}/{area}' on {base_url} (interval={interval}s)"
    )
    print(f"[{_utc_ts()}] Saving files under: {os.path.abspath(out_dir)}/{area}/")

    while True:
        try:
            downloaded = fetch_files(base_url, project, area)
            any_changed, per_file = compare_and_write(downloaded, out_dir, area)

            if any_changed:
                changed_list = ", ".join([k for k, v in per_file.items() if v])
                print(f"[{_utc_ts()}] Updated: {changed_list}")
            else:
                print(f"[{_utc_ts()}] No changes")

            # If instructions.md changed (including first download), trigger pi.
            if per_file.get("instructions.md"):
                # Prefer the canonical persistence path if present (matches the command:
                #   pi -p --no-session --tools read,bash,edit,write /persistence/<project>/<area>/instructions.md
                preferred_path = f"/persistence/{project}/{area}/instructions.md"
                if os.path.exists(preferred_path):
                    instructions_path = preferred_path
                else:
                    instructions_path = os.path.abspath(
                        os.path.join(out_dir, area, "instructions.md")
                    )
                run_pi(instructions_path)

        except requests.RequestException as e:
            print(f"[{_utc_ts()}] Request error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[{_utc_ts()}] Unexpected error: {e}", file=sys.stderr)

        if args.once:
            return 0

        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
