- Generate a script for committing code to github.com.
  - The main script should be created as `bin/git_push.sh`.
  - Create a unique new branch name for LLM commits.
  - Add any new files that have been created in the directory tree except for those that are in the `.gitignore`.
  - Commit the changes to the new branch.
  - Push the branch to the GitHub repository.
  - Use the `generated_pr.md` file (previously generated) to create a PR (Pull Request).
  - Run `scripts/git_push.sh` (a thin wrapper around `bin/git_push.sh`) to actually push the changes to GitHub.

Notes:
- Requires `git` and the GitHub CLI (`gh`).
- `generated_pr.md` must exist at the repo root and should have the PR title on the first line.
