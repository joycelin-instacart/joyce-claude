#!/usr/bin/env bash
# Mirror personal Claude skills and commands from $CLAUDE_HOME into $STACK_REPO,
# as both a plugin marketplace and a raw backup. Commit and push if there's a diff.
#
# Invoked by a global Stop hook in ~/.claude/settings.json after every Claude turn.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
STACK_REPO="${STACK_REPO:-$HOME/joyce-claude}"
STATE_FILE="$STACK_REPO/.sync-state"
LOG_FILE="$STACK_REPO/.sync.log"

log() {
  printf '[%s] %s\n' "$(date -Iseconds)" "$*" >> "$LOG_FILE"
}

# Fast-path: if nothing in CLAUDE_HOME/{skills,commands} is newer than the
# state file, exit without scanning further. Sub-100ms in the common case.
if [[ -f "$STATE_FILE" ]]; then
  if ! find "$CLAUDE_HOME/skills" "$CLAUDE_HOME/commands" \
       -newer "$STATE_FILE" -type f -print -quit 2>/dev/null | grep -q .; then
    log "no-op (no changes since last sync)"
    echo "no-op"
    exit 0
  fi
fi

log "sync starting"

# (Subsequent tasks fill in the actual work here)

touch "$STATE_FILE"
log "sync complete"
