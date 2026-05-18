# joyce-claude Personal Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the sync infrastructure that mirrors `~/.claude/skills/` and `~/.claude/commands/` into the `joyce-claude` repo as both a plugin marketplace and a raw backup, and wire it to run automatically at the end of every Claude turn.

**Architecture:** A single bash script (`scripts/sync.sh`) enumerates personal skills/commands from `$CLAUDE_HOME` (default `~/.claude`), mirrors them into `$STACK_REPO` (default `~/joyce-claude`) as both `<name>/skills/<name>/` plugin folders and a flat `backup/` tree, regenerates `.claude-plugin/marketplace.json` from the directory listing, and commits + pushes if there's a diff. A global `Stop` hook in `~/.claude/settings.json` invokes the script after every Claude turn. A small Python helper extracts SKILL.md frontmatter (PyYAML is already available). Tests run sync.sh against a fixture HOME built in a temp dir, asserting on the resulting repo state.

**Tech Stack:** bash 5+, rsync, git, jq, python3 + PyYAML.

**Reference spec:** `docs/specs/2026-05-17-personal-stack-design.md`

---

## File Structure

**Files to create:**

| Path | Responsibility |
|---|---|
| `~/joyce-claude/.gitignore` | Ignore `.sync-state`, `.sync.log`. |
| `~/joyce-claude/scripts/sync.sh` | Main entrypoint. Reads `$CLAUDE_HOME`, writes to `$STACK_REPO`. |
| `~/joyce-claude/scripts/parse_frontmatter.py` | Extract `name`/`description`/`version` from a SKILL.md. Output JSON on stdout. |
| `~/joyce-claude/scripts/tests/fixture.sh` | Build a fake `$CLAUDE_HOME` + `$STACK_REPO` in a temp dir. |
| `~/joyce-claude/scripts/tests/run_tests.sh` | Run all test cases against fixture. Exits nonzero on any failure. |

**Files to modify (by sync.sh at runtime):**

- `~/joyce-claude/.claude-plugin/marketplace.json` — auto-generated.
- `~/joyce-claude/<plugin>/.claude-plugin/plugin.json` — scaffolded per plugin.
- `~/joyce-claude/<plugin>/skills/<name>/` — rsynced from `~/.claude/skills/<name>/`.
- `~/joyce-claude/<plugin>/commands/<name>.md` — if matching command exists.
- `~/joyce-claude/backup/skills/` and `backup/commands/` — verbatim mirror.

**Files to modify manually:**

- `~/joyce-claude/README.md` — replace placeholder with plugin table.
- `~/.claude/settings.json` — add Stop hook (last step, so hook never fires against half-built repo).

**Decomposition rationale:** `sync.sh` stays as one file with internal functions because the steps are tightly coupled (every step shares state about which skills are personal). `parse_frontmatter.py` is split out because YAML parsing in bash is fragile and Python's PyYAML is reliable. Tests live in their own subdir so they don't pollute the script directory.

---

## Task 1: `.gitignore`

Empty subdirs are skipped — they'll appear naturally as Tasks 2–5 add files.

**Files:**
- Create: `~/joyce-claude/.gitignore`

- [ ] **Step 1: Write `.gitignore`**

```
# Sync state — local-only, regenerated each run
.sync-state
.sync.log

# Editor scratch
.DS_Store
*.swp
```

- [ ] **Step 2: Commit**

```bash
cd ~/joyce-claude
git add .gitignore
git commit -m "chore: add .gitignore"
```

---

## Task 2: Frontmatter parser (`parse_frontmatter.py`)

Skills have YAML frontmatter between `---` markers. We need `name`, `description`, and optionally `version`. Description can be a single line or a `|` block scalar (multi-line). Python + PyYAML handles both reliably.

**Files:**
- Create: `~/joyce-claude/scripts/parse_frontmatter.py`
- Test: inline (run against real SKILL.md files in `~/.claude/skills/`).

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Extract YAML frontmatter from a SKILL.md.

Usage: parse_frontmatter.py <path-to-SKILL.md>
Output: JSON with keys name, description, version (version defaults to "1.0.0").
Exits 1 if no frontmatter or required fields missing.
"""
import json
import sys
import yaml

if len(sys.argv) != 2:
    print("usage: parse_frontmatter.py <SKILL.md>", file=sys.stderr)
    sys.exit(2)

text = open(sys.argv[1]).read()
if not text.startswith("---"):
    print(f"{sys.argv[1]}: no frontmatter", file=sys.stderr)
    sys.exit(1)

# Split on first two --- markers
parts = text.split("---", 2)
if len(parts) < 3:
    print(f"{sys.argv[1]}: malformed frontmatter", file=sys.stderr)
    sys.exit(1)

meta = yaml.safe_load(parts[1]) or {}
name = meta.get("name")
if not name:
    print(f"{sys.argv[1]}: missing 'name'", file=sys.stderr)
    sys.exit(1)

# Description may be a multi-line block scalar — normalize to single line
desc = (meta.get("description") or f"Personal Claude skill: {name}").strip().replace("\n", " ")
version = str(meta.get("version") or "1.0.0")

json.dump({"name": name, "description": desc, "version": version}, sys.stdout)
```

- [ ] **Step 2: Make executable**

```bash
chmod +x ~/joyce-claude/scripts/parse_frontmatter.py
```

- [ ] **Step 3: Verify against a single-line-description skill**

Run: `~/joyce-claude/scripts/parse_frontmatter.py ~/.claude/skills/commit-and-push/SKILL.md`
Expected output: `{"name": "commit-and-push", "description": "Use when the user wants to review changes, commit with a conventional commit message, and push to the current branch, or invokes /commit-and-push", "version": "1.0.0"}`

- [ ] **Step 4: Verify against a multi-line-description skill**

Run: `~/joyce-claude/scripts/parse_frontmatter.py ~/.claude/skills/ai-fluency/SKILL.md`
Expected: JSON with `"name": "ai-fluency"`, `"version": "4.0.0"`, and a single-line description starting with `"Analyze your past Claude Code conversations..."` (newlines collapsed to spaces).

- [ ] **Step 5: Commit**

```bash
cd ~/joyce-claude
git add scripts/parse_frontmatter.py
git commit -m "feat: add parse_frontmatter.py helper for SKILL.md metadata"
```

---

## Task 3: Test fixture builder (`tests/fixture.sh`)

The fixture builds a fake `$CLAUDE_HOME` and `$STACK_REPO` in a temp dir, so `sync.sh` can be tested in isolation from the real `~/.claude/`. Every subsequent task uses this.

**Files:**
- Create: `~/joyce-claude/scripts/tests/fixture.sh`

- [ ] **Step 1: Write the fixture builder**

```bash
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
```

- [ ] **Step 2: Smoke-test the fixture builder**

```bash
cd ~/joyce-claude
bash -c 'source scripts/tests/fixture.sh; build_fixture; add_skill foo "foo desc"; add_command foo; ls -R "$CLAUDE_HOME"; teardown_fixture'
```

Expected: directory listing showing `claude/skills/foo/SKILL.md` and `claude/commands/foo.md`, then clean exit.

- [ ] **Step 3: Commit**

```bash
cd ~/joyce-claude
git add scripts/tests/fixture.sh
git commit -m "test: add fixture builder for sync.sh isolation tests"
```

---

## Task 4: Test runner skeleton (`tests/run_tests.sh`)

A driver that runs each test case in a fresh fixture and reports pass/fail. Subsequent tasks add test cases to this file.

**Files:**
- Create: `~/joyce-claude/scripts/tests/run_tests.sh`

- [ ] **Step 1: Write the runner skeleton**

```bash
#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/tests/fixture.sh"

PASS=0
FAIL=0
FAILED_TESTS=()

run_test() {
  local name="$1"
  local fn="$2"
  build_fixture
  if ( set -e; "$fn" ); then
    echo "PASS  $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL  $name"
    FAIL=$((FAIL + 1))
    FAILED_TESTS+=("$name")
  fi
  teardown_fixture
}

# --- test cases (added by later tasks) ---

# (none yet)

# --- end test cases ---

echo
echo "Results: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
  printf 'Failed:\n'
  printf '  - %s\n' "${FAILED_TESTS[@]}"
  exit 1
fi
```

- [ ] **Step 2: Make executable and run (expect 0 tests)**

```bash
chmod +x ~/joyce-claude/scripts/tests/run_tests.sh
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected output: `Results: 0 passed, 0 failed`, exit 0.

- [ ] **Step 3: Commit**

```bash
cd ~/joyce-claude
git add scripts/tests/run_tests.sh
git commit -m "test: add test runner skeleton"
```

---

## Task 5: `sync.sh` skeleton with fast-path no-op

**Files:**
- Create: `~/joyce-claude/scripts/sync.sh`
- Modify: `~/joyce-claude/scripts/tests/run_tests.sh` (add no-op test)

- [ ] **Step 1: Write the failing test in `run_tests.sh`**

Insert before `# --- end test cases ---`:

```bash
test_noop_on_unchanged() {
  add_skill foo
  bash "$ROOT/sync.sh"
  # Second invocation must be a fast-path no-op
  local out
  out=$(bash "$ROOT/sync.sh" 2>&1)
  [[ "$out" == *"no-op"* ]] || { echo "expected 'no-op' in output, got: $out"; return 1; }
}
run_test "noop on unchanged" test_noop_on_unchanged
```

- [ ] **Step 2: Run the test (expect fail — sync.sh doesn't exist yet)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: `FAIL  noop on unchanged`.

- [ ] **Step 3: Write the sync.sh skeleton**

```bash
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
```

- [ ] **Step 4: Make executable and run the test (expect pass)**

```bash
chmod +x ~/joyce-claude/scripts/sync.sh
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: `PASS  noop on unchanged`. Results: 1 passed.

- [ ] **Step 5: Commit**

```bash
cd ~/joyce-claude
git add scripts/sync.sh scripts/tests/run_tests.sh
git commit -m "feat: sync.sh skeleton with fast-path no-op"
```

---

## Task 6: Personal skills enumeration and backup mirror

`backup/skills/` is the simplest output to produce — pure rsync, no scaffolding. Doing this first means we have a verified end-to-end loop (input → output → assertion) before adding plugin folder complexity.

**Files:**
- Modify: `~/joyce-claude/scripts/sync.sh`
- Modify: `~/joyce-claude/scripts/tests/run_tests.sh`

- [ ] **Step 1: Add the failing test**

Insert before `# --- end test cases ---`:

```bash
test_backup_mirrors_skills() {
  add_skill foo "foo desc"
  add_skill bar "bar desc"
  bash "$ROOT/sync.sh"
  [[ -f "$STACK_REPO/backup/skills/foo/SKILL.md" ]] || { echo "missing foo SKILL.md in backup"; return 1; }
  [[ -f "$STACK_REPO/backup/skills/bar/SKILL.md" ]] || { echo "missing bar SKILL.md in backup"; return 1; }
}
run_test "backup mirrors skills" test_backup_mirrors_skills

test_backup_mirrors_commands() {
  add_skill foo
  add_command foo
  bash "$ROOT/sync.sh"
  [[ -f "$STACK_REPO/backup/commands/foo.md" ]] || { echo "missing foo.md in backup"; return 1; }
}
run_test "backup mirrors commands" test_backup_mirrors_commands

test_backup_drops_deleted_skill() {
  add_skill foo
  add_skill bar
  bash "$ROOT/sync.sh"
  rm -rf "$CLAUDE_HOME/skills/bar"
  touch "$STATE_FILE"; rm -f "$STATE_FILE"   # force re-run
  bash "$ROOT/sync.sh"
  [[ ! -d "$STACK_REPO/backup/skills/bar" ]] || { echo "deleted skill 'bar' still in backup"; return 1; }
}
run_test "backup drops deleted skill" test_backup_drops_deleted_skill
```

- [ ] **Step 2: Run tests (expect 3 failures)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: previous noop test still passes; 3 new tests fail.

- [ ] **Step 3: Implement backup mirror in sync.sh**

Replace `# (Subsequent tasks fill in the actual work here)` with:

```bash
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
```

- [ ] **Step 4: Run tests (expect all pass)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: 4 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
cd ~/joyce-claude
git add scripts/sync.sh scripts/tests/run_tests.sh
git commit -m "feat: backup mirror for personal skills and commands"
```

---

## Task 7: Plugin folder population with `plugin.json` scaffold

Each personal skill gets its own plugin folder: `<name>/.claude-plugin/plugin.json` plus `<name>/skills/<name>/` containing the skill files.

**Files:**
- Modify: `~/joyce-claude/scripts/sync.sh`
- Modify: `~/joyce-claude/scripts/tests/run_tests.sh`

- [ ] **Step 1: Add the failing test**

```bash
test_plugin_folder_has_skill() {
  add_skill foo "foo desc"
  bash "$ROOT/sync.sh"
  [[ -f "$STACK_REPO/foo/skills/foo/SKILL.md" ]] || { echo "missing skill in plugin folder"; return 1; }
}
run_test "plugin folder has skill" test_plugin_folder_has_skill

test_plugin_json_scaffold() {
  add_skill foo "foo desc"
  bash "$ROOT/sync.sh"
  local pj="$STACK_REPO/foo/.claude-plugin/plugin.json"
  [[ -f "$pj" ]] || { echo "missing plugin.json"; return 1; }
  local name desc version
  name=$(jq -r .name "$pj")
  desc=$(jq -r .description "$pj")
  version=$(jq -r .version "$pj")
  [[ "$name" == "foo" ]] || { echo "wrong name: $name"; return 1; }
  [[ "$desc" == "foo desc" ]] || { echo "wrong desc: $desc"; return 1; }
  [[ "$version" == "1.0.0" ]] || { echo "wrong version: $version"; return 1; }
}
run_test "plugin.json scaffolded" test_plugin_json_scaffold

test_plugin_folder_pruned_on_delete() {
  add_skill foo
  add_skill bar
  bash "$ROOT/sync.sh"
  rm -rf "$CLAUDE_HOME/skills/bar"
  rm -f "$STATE_FILE"
  bash "$ROOT/sync.sh"
  [[ ! -d "$STACK_REPO/bar" ]] || { echo "plugin folder for deleted skill still exists"; return 1; }
}
run_test "plugin folder pruned on delete" test_plugin_folder_pruned_on_delete
```

- [ ] **Step 2: Run tests (expect 3 new failures)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

- [ ] **Step 3: Add plugin folder logic to sync.sh**

Append after the backup mirror block:

```bash
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
```

- [ ] **Step 4: Run tests (expect all pass)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: 7 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
cd ~/joyce-claude
git add scripts/sync.sh scripts/tests/run_tests.sh
git commit -m "feat: scaffold plugin folders with plugin.json from SKILL.md frontmatter"
```

---

## Task 8: Bundle matching commands into plugin folders

When a command's basename matches a skill name (e.g., `commands/find-skill-candidates.md` ↔ `skills/find-skill-candidates/`), copy it into the plugin folder's `commands/` subdir. Unmatched commands stay in `backup/commands/` only and log a warning.

**Files:**
- Modify: `~/joyce-claude/scripts/sync.sh`
- Modify: `~/joyce-claude/scripts/tests/run_tests.sh`

- [ ] **Step 1: Add the failing test**

```bash
test_matching_command_bundled() {
  add_skill foo
  add_command foo
  bash "$ROOT/sync.sh"
  [[ -f "$STACK_REPO/foo/commands/foo.md" ]] || { echo "matching command not bundled"; return 1; }
}
run_test "matching command bundled" test_matching_command_bundled

test_unmatched_command_warns() {
  add_skill foo
  add_command orphan
  local out
  out=$(bash "$ROOT/sync.sh" 2>&1)
  [[ -f "$STACK_REPO/backup/commands/orphan.md" ]] || { echo "orphan missing from backup"; return 1; }
  [[ ! -f "$STACK_REPO/orphan/commands/orphan.md" ]] || { echo "orphan unexpectedly bundled into plugin"; return 1; }
  # Verify warning landed in log
  grep -q "unmatched command: orphan" "$LOG_FILE" || { echo "no warning logged for orphan command"; return 1; }
}
run_test "unmatched command warns" test_unmatched_command_warns
```

- [ ] **Step 2: Run tests (expect 2 new failures)**

- [ ] **Step 3: Add command bundling to sync.sh**

Append after the plugin folder block:

```bash
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
```

- [ ] **Step 4: Run tests (expect all pass)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: 9 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
cd ~/joyce-claude
git add scripts/sync.sh scripts/tests/run_tests.sh
git commit -m "feat: bundle matching commands into plugin folders, warn on orphans"
```

---

## Task 9: Regenerate `.claude-plugin/marketplace.json`

Walk the plugin folders that exist, build a JSON document, write to `.claude-plugin/marketplace.json`. Hand-edits to individual `plugin.json` files (e.g., bumping a version) are preserved because we read from them rather than overwrite them.

**Files:**
- Modify: `~/joyce-claude/scripts/sync.sh`
- Modify: `~/joyce-claude/scripts/tests/run_tests.sh`

- [ ] **Step 1: Add the failing test**

```bash
test_marketplace_json_lists_plugins() {
  add_skill foo "foo desc"
  add_skill bar "bar desc"
  bash "$ROOT/sync.sh"
  local mp="$STACK_REPO/.claude-plugin/marketplace.json"
  [[ -f "$mp" ]] || { echo "missing marketplace.json"; return 1; }
  local names
  names=$(jq -r '.plugins[].name' "$mp" | sort | tr '\n' ',')
  [[ "$names" == "bar,foo," ]] || { echo "wrong plugin list: $names"; return 1; }
  local name desc src
  src=$(jq -r '.plugins[] | select(.name == "foo") | .source' "$mp")
  desc=$(jq -r '.plugins[] | select(.name == "foo") | .description' "$mp")
  [[ "$src" == "./foo" ]] || { echo "wrong source for foo: $src"; return 1; }
  [[ "$desc" == "foo desc" ]] || { echo "wrong desc for foo: $desc"; return 1; }
}
run_test "marketplace.json lists plugins" test_marketplace_json_lists_plugins

test_marketplace_json_drops_deleted() {
  add_skill foo
  add_skill bar
  bash "$ROOT/sync.sh"
  rm -rf "$CLAUDE_HOME/skills/bar"
  rm -f "$STATE_FILE"
  bash "$ROOT/sync.sh"
  local names
  names=$(jq -r '.plugins[].name' "$STACK_REPO/.claude-plugin/marketplace.json" | sort | tr '\n' ',')
  [[ "$names" == "foo," ]] || { echo "deleted plugin still in marketplace.json: $names"; return 1; }
}
run_test "marketplace.json drops deleted" test_marketplace_json_drops_deleted
```

- [ ] **Step 2: Run tests (expect 2 new failures)**

- [ ] **Step 3: Add marketplace.json regeneration to sync.sh**

Append after the command bundling block:

```bash
# --- regenerate marketplace.json ---
mkdir -p "$STACK_REPO/.claude-plugin"
mp_tmp="$(mktemp)"

# Build the plugins array from existing plugin folders
plugins_json="[]"
while IFS= read -r -d '' pj; do
  plugin_dir="$(dirname "$(dirname "$pj")")"
  plugin_name="$(basename "$plugin_dir")"
  entry=$(jq -c \
    --arg name "$plugin_name" \
    --arg source "./$plugin_name" \
    --arg author "Joyce Lin" \
    '{name: $name, source: $source, description: .description, version: .version, author: {name: $author}}' \
    "$pj")
  plugins_json=$(echo "$plugins_json" | jq -c --argjson e "$entry" '. + [$e]')
done < <(find "$STACK_REPO" -mindepth 3 -maxdepth 3 -name plugin.json -path '*/.claude-plugin/*' -print0)

jq -n \
  --arg name "joyce-claude" \
  --arg desc "Joyce's personal Claude skills and plugins" \
  --argjson plugins "$plugins_json" \
  '{name: $name, description: $desc, owner: {name: "Joyce Lin"}, plugins: $plugins}' \
  > "$mp_tmp"

mv "$mp_tmp" "$STACK_REPO/.claude-plugin/marketplace.json"
```

- [ ] **Step 4: Run tests (expect all pass)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: 11 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
cd ~/joyce-claude
git add scripts/sync.sh scripts/tests/run_tests.sh
git commit -m "feat: regenerate marketplace.json from plugin folders"
```

---

## Task 10: Git commit + push on diff

The last step of sync.sh: stage everything, commit with a message naming the affected skills, push. Skip if no diff. Catch push failures and exit nonzero so the next turn retries.

**Files:**
- Modify: `~/joyce-claude/scripts/sync.sh`
- Modify: `~/joyce-claude/scripts/tests/run_tests.sh`

- [ ] **Step 1: Add the failing test**

```bash
test_sync_commits_and_pushes() {
  add_skill foo "foo desc"
  bash "$ROOT/sync.sh"
  # Commit landed locally
  local subject
  subject=$(git -C "$STACK_REPO" log -1 --format=%s)
  [[ "$subject" == sync:* ]] || { echo "no sync commit; got subject: $subject"; return 1; }
  # And was pushed to origin
  local remote_head local_head
  remote_head=$(git -C "$STACK_REPO" rev-parse origin/main)
  local_head=$(git -C "$STACK_REPO" rev-parse HEAD)
  [[ "$remote_head" == "$local_head" ]] || { echo "remote not in sync with local"; return 1; }
}
run_test "sync commits and pushes" test_sync_commits_and_pushes

test_sync_no_commit_when_no_diff() {
  add_skill foo
  bash "$ROOT/sync.sh"
  local before_sha
  before_sha=$(git -C "$STACK_REPO" rev-parse HEAD)
  rm -f "$STATE_FILE"   # force re-run despite no actual content changes
  bash "$ROOT/sync.sh"
  local after_sha
  after_sha=$(git -C "$STACK_REPO" rev-parse HEAD)
  [[ "$before_sha" == "$after_sha" ]] || { echo "unexpected commit when no diff"; return 1; }
}
run_test "sync no commit when no diff" test_sync_no_commit_when_no_diff

test_sync_recovers_after_push_failure() {
  add_skill foo
  # Break the remote so push fails
  git -C "$STACK_REPO" remote set-url origin "$TMP_ROOT/no-such-remote.git"
  if bash "$ROOT/sync.sh" 2>/dev/null; then
    echo "expected sync.sh to exit nonzero on push failure"; return 1
  fi
  grep -q "push failed" "$LOG_FILE" || { echo "push failure not logged"; return 1; }
  # Local commit landed
  local subject
  subject=$(git -C "$STACK_REPO" log -1 --format=%s)
  [[ "$subject" == sync:* ]] || { echo "expected local sync commit even on push failure"; return 1; }
  # Restore the remote; next run should successfully push the existing commit
  git -C "$STACK_REPO" remote set-url origin "$TMP_ROOT/remote.git"
  rm -f "$STATE_FILE"
  bash "$ROOT/sync.sh"
  local remote_head local_head
  remote_head=$(git -C "$STACK_REPO" rev-parse origin/main)
  local_head=$(git -C "$STACK_REPO" rev-parse HEAD)
  [[ "$remote_head" == "$local_head" ]] || { echo "recovery push did not catch up remote"; return 1; }
}
run_test "sync recovers after push failure" test_sync_recovers_after_push_failure
```

- [ ] **Step 2: Run tests (expect 3 new failures)**

- [ ] **Step 3: Add commit + push to sync.sh**

Replace the final two lines (`touch "$STATE_FILE"` and `log "sync complete"`) with:

```bash
# --- commit and push if anything changed ---
cd "$STACK_REPO"
git add -A
if ! git diff --cached --quiet; then
  # Build a commit message from the changed plugin names
  changed=$(git diff --cached --name-only | awk -F/ '{print $1}' | sort -u | grep -Ev '^(\.|backup|scripts|docs|README\.md|\.gitignore)$' | paste -sd, -)
  msg="sync: ${changed:-update}"
  git commit -q -m "$msg"
  if git push -q origin main; then
    log "pushed: $msg"
    touch "$STATE_FILE"
    log "sync complete"
  else
    log "push failed; next run will retry"
    exit 1
  fi
else
  touch "$STATE_FILE"
  log "no diff; nothing to commit"
fi
```

- [ ] **Step 4: Run tests (expect all pass)**

```bash
~/joyce-claude/scripts/tests/run_tests.sh
```

Expected: 14 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
cd ~/joyce-claude
git add scripts/sync.sh scripts/tests/run_tests.sh
git commit -m "feat: commit and push from sync.sh on diff, retry on push failure"
```

---

## Task 11: Initial seed run against real `~/.claude/`

Now run sync.sh against the real home dir for the first time. Verify the diff before letting it push.

**Files:**
- Modify: `~/joyce-claude/` (script runs and creates plugin folders, backup, marketplace.json)

- [ ] **Step 1: Pre-flight check**

```bash
ls ~/.claude/skills/
```

Expected: `ai-fluency  commit-and-push  create-branch  create-pr  daniel  find-skill-candidates`.

- [ ] **Step 2: Run sync.sh against the real home (it will commit + push on success)**

```bash
cd ~/joyce-claude && bash scripts/sync.sh
```

Expected output: `no-op` is unlikely on first run; instead script runs silently to completion. On failure, check `~/joyce-claude/.sync.log`.

- [ ] **Step 3: Verify the repo state**

```bash
ls ~/joyce-claude/
cat ~/joyce-claude/.claude-plugin/marketplace.json | jq '.plugins | length, [.[].name]'
ls ~/joyce-claude/backup/skills/ ~/joyce-claude/backup/commands/
```

Expected:
- Top-level dirs include: `ai-fluency`, `commit-and-push`, `create-branch`, `create-pr`, `daniel`, `find-skill-candidates`, `backup`, `docs`, `scripts`, plus `.claude-plugin/`.
- marketplace.json has 6 plugins matching the skill names.
- `backup/skills/` has 6 dirs; `backup/commands/` has `find-skill-candidates.md`.
- `find-skill-candidates/commands/find-skill-candidates.md` exists (the only matching command).

- [ ] **Step 4: Verify the push landed**

```bash
gh repo view joycelin-instacart/joyce-claude --web 2>/dev/null || \
  echo "Browse to https://github.com/joycelin-instacart/joyce-claude"
git -C ~/joyce-claude log --oneline -5
```

Expected: latest commit is a `sync: ...` commit, pushed to origin/main.

- [ ] **Step 5: Run sync.sh again to verify the fast-path no-op**

```bash
time bash ~/joyce-claude/scripts/sync.sh
```

Expected: outputs `no-op`, real time < 100ms. No new commit.

---

## Task 12: README plugin table

Replace the placeholder README with a bdvstack-style table listing the seeded plugins.

**Files:**
- Modify: `~/joyce-claude/README.md`

- [ ] **Step 1: Write the new README**

```markdown
# joyce-claude

Joyce's personal Claude Code skills and plugins. Auto-synced from `~/.claude/skills/` and `~/.claude/commands/` after every Claude turn.

## Install

Add the marketplace, then install whichever plugins you want.

```text
/plugin marketplace add joycelin-instacart/joyce-claude
```

Then install individual plugins:

```text
/plugin install ai-fluency@joyce-claude
/plugin install commit-and-push@joyce-claude
/plugin install create-branch@joyce-claude
/plugin install create-pr@joyce-claude
/plugin install daniel@joyce-claude
/plugin install find-skill-candidates@joyce-claude
```

## Plugins

| Plugin | What it does |
|--------|--------------|
| `ai-fluency` | Analyze past Claude conversations to measure AI fluency across the 4D framework. |
| `commit-and-push` | Review changes, write a conventional commit message, commit, and push. |
| `create-branch` | Create a new feature branch from a ticket number or description. |
| `create-pr` | Commit current changes and open a pull request in one step. |
| `daniel` | Multi-personality PR review pipeline (Daniel, Kye, Gilfoyle, Repo Practices). |
| `find-skill-candidates` | Mine prompt history for recurring asks that could be automated into skills. |

## Backup

The full source tree of every personal skill and command also lives under [`backup/`](backup/) as a verbatim mirror — useful for grep, diff, and restore.

## Update

```text
/plugin marketplace update joyce-claude
```

## How sync works

See [`docs/specs/2026-05-17-personal-stack-design.md`](docs/specs/2026-05-17-personal-stack-design.md).
```

- [ ] **Step 2: Commit and push manually (sync.sh would also pick this up next turn)**

```bash
cd ~/joyce-claude
git add README.md
git commit -m "docs: replace README placeholder with plugin table"
git push
```

---

## Task 13: Wire the Stop hook into `~/.claude/settings.json`

The current `~/.claude/settings.json` already has a `hooks` object with `SessionStart` and `PreToolUse` entries. We add `Stop` to that object. **Use the `update-config` skill** — it knows how to merge into the existing structure safely.

**Files:**
- Modify: `~/.claude/settings.json` (via update-config skill)

- [ ] **Step 1: Show the user the planned change for confirmation**

The diff that will be applied to `~/.claude/settings.json`:

```diff
   "hooks": {
     "SessionStart": [ ... ],
-    "PreToolUse": [ ... ]
+    "PreToolUse": [ ... ],
+    "Stop": [
+      {
+        "matcher": "",
+        "hooks": [
+          { "type": "command", "command": "/home/bento/joyce-claude/scripts/sync.sh", "timeout": 30 }
+        ]
+      }
+    ]
   }
```

The hook fires globally — every Claude session in every project. Confirm with the user before applying.

- [ ] **Step 2: Invoke the `update-config` skill**

Use the Skill tool with `update-config`. Request: add a `Stop` hook to `~/.claude/settings.json` that runs `/home/bento/joyce-claude/scripts/sync.sh` with a 30s timeout, merged into the existing `hooks` object.

- [ ] **Step 3: Verify the change**

```bash
jq '.hooks.Stop' ~/.claude/settings.json
```

Expected: the new Stop hook entry as JSON.

---

## Task 14: End-to-end smoke test

Touch a personal skill, let a Claude turn complete, confirm the hook fires and pushes.

**Files:** None new — observational only.

- [ ] **Step 1: Make a trivial visible edit to a personal skill**

```bash
# Append a harmless trailing newline (or comment) to one SKILL.md to create a diff
printf '\n<!-- sync test: %s -->\n' "$(date -Iseconds)" >> ~/.claude/skills/commit-and-push/SKILL.md
```

- [ ] **Step 2: End the current turn (this happens naturally when the agent finishes responding)**

In the Claude session: type a no-op message like `ok` or finish whatever you're doing. The Stop hook fires when the turn ends.

- [ ] **Step 3: Verify the sync ran**

```bash
tail -5 ~/joyce-claude/.sync.log
git -C ~/joyce-claude log --oneline -3
```

Expected: log shows a recent `pushed: sync: commit-and-push` line; git log shows the new commit.

- [ ] **Step 4: Verify the remote**

```bash
git -C ~/joyce-claude log origin/main --oneline -3
```

Expected: the new commit is on origin/main.

- [ ] **Step 5: Clean up the test edit**

```bash
# Revert the test marker (use the actual edit you made)
sed -i '/<!-- sync test:/d' ~/.claude/skills/commit-and-push/SKILL.md
```

Wait for next turn to land the cleanup commit, or run `bash ~/joyce-claude/scripts/sync.sh` manually.

---

## Notes for the executor

- **`set -euo pipefail` is critical** for sync.sh. A silently-failing step that still triggers a commit could push garbage. If any step fails, the script should exit nonzero and the next turn retries with full state.
- **The fast-path no-op MUST stay sub-100ms.** This is a Stop hook — it runs on every turn in every project. A slow sync turns into a slow Claude session.
- **rsync `--delete` only inside specific destinations.** Never run `rsync --delete` against `$STACK_REPO` directly — that would obliterate `docs/`, `scripts/`, `README.md`, etc. Always target a leaf dir (`backup/skills/<name>/` or `<plugin>/skills/<name>/`).
- **Don't `git add -A` until commit time.** If something fails mid-script, we don't want partial state staged.
- **Don't auto-edit plugin.json after first scaffold.** The user may hand-edit a description or bump a version; we shouldn't clobber that. Only create plugin.json if it doesn't exist.
- **Bash array gotcha:** when `personal_skills` is empty, iterating `"${personal_skills[@]:-}"` produces an empty string element which can confuse comparisons. Use `${#personal_skills[@]} -gt 0` checks where needed.
