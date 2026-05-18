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

test_noop_on_unchanged() {
  add_skill foo
  bash "$ROOT/sync.sh"
  # Second invocation must be a fast-path no-op
  local out
  out=$(bash "$ROOT/sync.sh" 2>&1)
  [[ "$out" == *"no-op"* ]] || { echo "expected 'no-op' in output, got: $out"; return 1; }
}
run_test "noop on unchanged" test_noop_on_unchanged

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

test_sync_commits_and_pushes() {
  add_skill foo "foo desc"
  bash "$ROOT/sync.sh"
  local subject
  subject=$(git -C "$STACK_REPO" log -1 --format=%s)
  [[ "$subject" == sync:* ]] || { echo "no sync commit; got subject: $subject"; return 1; }
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
  rm -f "$STATE_FILE"
  bash "$ROOT/sync.sh"
  local after_sha
  after_sha=$(git -C "$STACK_REPO" rev-parse HEAD)
  [[ "$before_sha" == "$after_sha" ]] || { echo "unexpected commit when no diff"; return 1; }
}
run_test "sync no commit when no diff" test_sync_no_commit_when_no_diff

test_sync_recovers_after_push_failure() {
  add_skill foo
  git -C "$STACK_REPO" remote set-url origin "$TMP_ROOT/no-such-remote.git"
  if bash "$ROOT/sync.sh" 2>/dev/null; then
    echo "expected sync.sh to exit nonzero on push failure"; return 1
  fi
  grep -q "push failed" "$LOG_FILE" || { echo "push failure not logged"; return 1; }
  local subject
  subject=$(git -C "$STACK_REPO" log -1 --format=%s)
  [[ "$subject" == sync:* ]] || { echo "expected local sync commit even on push failure"; return 1; }
  git -C "$STACK_REPO" remote set-url origin "$TMP_ROOT/remote.git"
  rm -f "$STATE_FILE"
  bash "$ROOT/sync.sh"
  local remote_head local_head
  remote_head=$(git -C "$STACK_REPO" rev-parse origin/main)
  local_head=$(git -C "$STACK_REPO" rev-parse HEAD)
  [[ "$remote_head" == "$local_head" ]] || { echo "recovery push did not catch up remote"; return 1; }
}
run_test "sync recovers after push failure" test_sync_recovers_after_push_failure

# --- end test cases ---

echo
echo "Results: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
  printf 'Failed:\n'
  printf '  - %s\n' "${FAILED_TESTS[@]}"
  exit 1
fi
