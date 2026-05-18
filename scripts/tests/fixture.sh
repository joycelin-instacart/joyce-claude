#!/usr/bin/env bash
# Build a fake CLAUDE_HOME and STACK_REPO in $TMP_ROOT for testing sync.sh.
#
# Usage: source fixture.sh; build_fixture
# After: $CLAUDE_HOME and $STACK_REPO are set and populated.

set -euo pipefail

build_fixture() {
  TMP_ROOT="$(mktemp -d -t joyce-claude-test.XXXXXX)"
  export TMP_ROOT
  export CLAUDE_HOME="$TMP_ROOT/claude"
  export STACK_REPO="$TMP_ROOT/repo"

  export STATE_FILE="$STACK_REPO/.sync-state"

  mkdir -p "$CLAUDE_HOME/skills" "$CLAUDE_HOME/commands"
  mkdir -p "$STACK_REPO"

  # Init the stack repo as a git repo with a bare remote so push works
  git -C "$STACK_REPO" init -b main -q
  git -C "$STACK_REPO" config user.email "test@example.com"
  git -C "$STACK_REPO" config user.name "Test"

  local remote="$TMP_ROOT/remote.git"
  git init -b main -q --bare "$remote"
  git -C "$STACK_REPO" remote add origin "$remote"

  # Initial commit so push has somewhere to go
  echo "# test" > "$STACK_REPO/README.md"
  git -C "$STACK_REPO" add README.md
  git -C "$STACK_REPO" commit -q -m "init"
  git -C "$STACK_REPO" push -q -u origin main
}

# Add a personal skill with a single-line description.
# Usage: add_skill <name> [description]
add_skill() {
  local name="$1"
  local desc="${2:-Test skill $name}"
  mkdir -p "$CLAUDE_HOME/skills/$name"
  cat > "$CLAUDE_HOME/skills/$name/SKILL.md" <<EOF
---
name: $name
description: $desc
---

# $name

Test skill body.
EOF
}

# Add a command file.
# Usage: add_command <name>
add_command() {
  local name="$1"
  cat > "$CLAUDE_HOME/commands/$name.md" <<EOF
---
description: Test command $name
---

Test command body.
EOF
}

teardown_fixture() {
  if [[ -n "${TMP_ROOT:-}" && -d "$TMP_ROOT" ]]; then
    rm -rf "$TMP_ROOT"
  fi
}
