#!/usr/bin/env bash
set -euo pipefail

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to run this script." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "The GitHub CLI (gh) is required to create pull requests." >&2
  exit 1
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "${REPO_ROOT}" ]]; then
  echo "This script must be run inside a git repository." >&2
  exit 1
fi

cd "$REPO_ROOT"

PR_FILE="$REPO_ROOT/generated_pr.md"
if [[ ! -f "$PR_FILE" ]]; then
  echo "generated_pr.md not found at $PR_FILE." >&2
  exit 1
fi

# Nothing to do?
if ! git status --porcelain | grep -q .; then
  echo "No changes detected; nothing to commit." >&2
  exit 0
fi

REMOTE=${REMOTE:-origin}
DEFAULT_BRANCH=${DEFAULT_BRANCH:-$(git rev-parse --abbrev-ref "$REMOTE/HEAD" 2>/dev/null | cut -d/ -f2- || echo main)}

# Unique branch name for LLM commits
BRANCH="llm/update-$(date +%Y%m%d-%H%M%S)-$RANDOM"

git checkout -b "$BRANCH"

# Stage tracked modifications/deletions
git add -u

# Stage new (untracked) files, excluding anything ignored by .gitignore
git ls-files --others --exclude-standard -z | while IFS= read -r -d '' file; do
  git add -- "$file"
done

if git diff --cached --quiet; then
  echo "No staged changes to commit." >&2
  exit 0
fi

PR_TITLE=$(head -n 1 "$PR_FILE" | tr -d '\r')
if [[ -z "$PR_TITLE" ]]; then
  echo "generated_pr.md must contain a PR title on its first line." >&2
  exit 1
fi

COMMIT_MESSAGE="$PR_TITLE"

git commit -m "$COMMIT_MESSAGE"

git push "$REMOTE" "$BRANCH"

# Use the remainder of generated_pr.md as the PR body (avoids duplicating title in body).
PR_BODY_TMP=$(mktemp)
trap 'rm -f "$PR_BODY_TMP"' EXIT

tail -n +2 "$PR_FILE" >"$PR_BODY_TMP" || true

gh pr create \
  --head "$BRANCH" \
  --base "$DEFAULT_BRANCH" \
  --title "$PR_TITLE" \
  --body-file "$PR_BODY_TMP"
