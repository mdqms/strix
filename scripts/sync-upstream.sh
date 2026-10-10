#!/usr/bin/env bash
# Weekly upstream sync for the Strix fork (decision D7, see FORK.md).
# Fetches and merges upstream/main, then STOPS and prints the gate commands.
# It never declares the merge good: the test suite and the XBEN benchmark are
# the gate, and only a human (or hosted CI) runs those.
set -euo pipefail

branch="${1:-main}"

if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "No 'upstream' remote. Add it: git remote add upstream https://github.com/usestrix/strix" >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree is dirty. Commit or stash before syncing." >&2
  exit 1
fi

# A shallow clone can't merge upstream history; deepen it once.
if [ -f "$(git rev-parse --git-path shallow)" ]; then
  echo "Shallow clone detected; unshallowing upstream history..."
  git fetch --unshallow upstream "$branch" || git fetch upstream "$branch"
else
  git fetch upstream "$branch"
fi

git merge "upstream/${branch}" --no-edit

cat <<'EOF'

Merge applied. NOT done yet — run both gates before trusting this on main:
  1. uv run pytest
  2. XBEN benchmark (Docker + LLM key; compare pass count to the pre-merge run)

A drop in either blocks the merge; fix or revert on a branch first. See FORK.md.
EOF
