#!/usr/bin/env bash
# Detect which ISC services a branch's changes belong to.
#
# Usage: detect_service.sh <branch-or-ref> [<base-ref>]
#   base-ref defaults to origin/master
#
# Prints one service name per line (the basename of the directory that
# owns a .isc/config.yml file ancestor of any changed file). De-duplicated.
# Exits 0 if at least one service was detected, 1 if none, 2 on misuse.

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: detect_service.sh <branch-or-ref> [<base-ref>]" >&2
  exit 2
fi

BRANCH="$1"
BASE="${2:-origin/master}"

# Make sure refs exist; fetch if needed.
if ! git rev-parse --verify --quiet "$BRANCH" >/dev/null; then
  git fetch --quiet origin "$BRANCH:refs/remotes/origin/$BRANCH" 2>/dev/null \
    || git fetch --quiet origin "$BRANCH" 2>/dev/null \
    || true
fi
if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  git fetch --quiet origin master 2>/dev/null || true
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Files added/changed on BRANCH since it diverged from BASE.
mapfile -t FILES < <(git diff --name-only "${BASE}...${BRANCH}" 2>/dev/null)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "no changes between $BASE and $BRANCH" >&2
  exit 1
fi

declare -A SERVICES=()

for f in "${FILES[@]}"; do
  # Walk up from the file's directory looking for .isc/config.yml.
  dir="$REPO_ROOT/$(dirname "$f")"
  while [[ "$dir" == "$REPO_ROOT"* && "$dir" != "/" ]]; do
    if [[ -f "$dir/.isc/config.yml" ]]; then
      SERVICES["$(basename "$dir")"]=1
      break
    fi
    dir="$(dirname "$dir")"
  done
done

if [[ ${#SERVICES[@]} -eq 0 ]]; then
  echo "no ISC service (no .isc/config.yml ancestor) owns any changed file" >&2
  exit 1
fi

for s in "${!SERVICES[@]}"; do
  echo "$s"
done | sort
