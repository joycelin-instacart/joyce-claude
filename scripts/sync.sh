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

# --- enumerate personal skills ---
# Everything in $CLAUDE_HOME/skills/ is personal (marketplace-installed skills
# live under ~/.claude/plugins/cache/, not here).
personal_skills=()
if [[ -d "$CLAUDE_HOME/skills" ]]; then
  while IFS= read -r -d '' dir; do
    personal_skills+=("$(basename "$dir")")
  done < <(find "$CLAUDE_HOME/skills" -mindepth 1 -maxdepth 1 -type d -print0)
fi

# --- backup mirror ---
mkdir -p "$STACK_REPO/backup/skills" "$STACK_REPO/backup/commands"

# Sync each personal skill into backup (with --delete to handle removals).
# Then prune backup/skills/ entries that no longer exist in CLAUDE_HOME.
for name in "${personal_skills[@]}"; do
  rsync -a --delete "$CLAUDE_HOME/skills/$name/" "$STACK_REPO/backup/skills/$name/"
done

# Prune deleted skills from backup
if [[ -d "$STACK_REPO/backup/skills" ]]; then
  while IFS= read -r -d '' dir; do
    name="$(basename "$dir")"
    keep=0
    for s in "${personal_skills[@]:-}"; do
      [[ "$s" == "$name" ]] && { keep=1; break; }
    done
    (( keep == 0 )) && rm -rf "$dir"
  done < <(find "$STACK_REPO/backup/skills" -mindepth 1 -maxdepth 1 -type d -print0)
fi

# Mirror commands (single rsync with --delete handles add/update/remove)
if [[ -d "$CLAUDE_HOME/commands" ]]; then
  rsync -a --delete "$CLAUDE_HOME/commands/" "$STACK_REPO/backup/commands/"
fi

touch "$STATE_FILE"
log "sync complete"
