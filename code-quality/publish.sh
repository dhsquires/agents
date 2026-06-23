#!/usr/bin/env bash
# Publish this self-contained project to a brand-new private repo.
#
# The token wired into the Claude Code web session is scoped to a single repo
# and cannot create new repositories, so this is meant to be run from a machine
# where you are authenticated with a token that has repo-creation rights
# (GitHub CLI logged in, or a classic PAT with `repo` scope / fine-grained PAT
# with Administration:write).
#
# Usage:
#   cd code-quality
#   ./publish.sh                       # creates dhsquires/code-quality (private)
#   ./publish.sh myorg/code-quality    # custom owner/name
set -euo pipefail

target="${1:-dhsquires/code-quality}"
owner="${target%%/*}"
name="${target##*/}"

echo "Publishing to private repo: $owner/$name"

# Initialise git here if needed (this folder becomes the repo root).
if [ ! -d .git ]; then
  git init -q
  git checkout -q -b main
fi
git add -A
git commit -q -m "Initial commit: code-quality plugin + workflow" || true

if command -v gh >/dev/null 2>&1; then
  gh repo create "$target" --private --source . --remote origin --push
  echo "Done. https://github.com/$owner/$name"
else
  echo "GitHub CLI not found. Create the repo in the UI, then run:"
  echo "  git remote add origin git@github.com:$owner/$name.git"
  echo "  git push -u origin main"
fi
