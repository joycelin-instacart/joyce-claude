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

# --- plugin folders ---
for name in "${personal_skills[@]}"; do
  plugin_dir="$STACK_REPO/$name"
  mkdir -p "$plugin_dir/.claude-plugin" "$plugin_dir/skills"

  # Mirror skill content into the plugin folder
  rsync -a --delete "$CLAUDE_HOME/skills/$name/" "$plugin_dir/skills/$name/"

  # Scaffold plugin.json if missing (preserves any hand-edited version on subsequent runs)
  pj="$plugin_dir/.claude-plugin/plugin.json"
  if [[ ! -f "$pj" ]]; then
    "$SCRIPT_DIR/parse_frontmatter.py" "$CLAUDE_HOME/skills/$name/SKILL.md" > "$pj"
  fi
done

# Prune plugin folders for deleted skills.
# A directory at the repo root is "managed" iff it has .claude-plugin/plugin.json
# AND its name appears (or used to appear) as a personal skill. To stay safe, only
# prune directories that match a known sync-managed shape and are no longer present.
while IFS= read -r -d '' dir; do
  name="$(basename "$dir")"
  # Skip non-plugin top-level dirs
  [[ -f "$dir/.claude-plugin/plugin.json" ]] || continue
  keep=0
  for s in "${personal_skills[@]:-}"; do
    [[ "$s" == "$name" ]] && { keep=1; break; }
  done
  (( keep == 0 )) && rm -rf "$dir"
done < <(find "$STACK_REPO" -mindepth 1 -maxdepth 1 -type d \
  ! -name '.git' ! -name '.claude-plugin' ! -name 'backup' \
  ! -name 'docs' ! -name 'scripts' -print0)

# --- bundle matching commands into plugin folders ---
if [[ -d "$CLAUDE_HOME/commands" ]]; then
  while IFS= read -r -d '' cmd; do
    base="$(basename "$cmd" .md)"
    matched=0
    for s in "${personal_skills[@]:-}"; do
      if [[ "$s" == "$base" ]]; then
        mkdir -p "$STACK_REPO/$base/commands"
        cp "$cmd" "$STACK_REPO/$base/commands/$base.md"
        matched=1
        break
      fi
    done
    (( matched == 0 )) && log "unmatched command: $base (in backup/ only)"
  done < <(find "$CLAUDE_HOME/commands" -mindepth 1 -maxdepth 1 -type f -name '*.md' -print0)
fi

touch "$STATE_FILE"
log "sync complete"
