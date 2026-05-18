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

# --- end test cases ---

echo
echo "Results: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
  printf 'Failed:\n'
  printf '  - %s\n' "${FAILED_TESTS[@]}"
  exit 1
fi
