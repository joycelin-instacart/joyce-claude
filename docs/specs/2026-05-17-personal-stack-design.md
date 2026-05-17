# joyce-claude — Personal Claude Stack

**Date:** 2026-05-17
**Status:** Design approved, implementation pending
**Owner:** Joyce Lin

## Goal

A personal git repo that mirrors and packages Joyce's personal Claude Code skills and commands, modeled after [bostondv/bdvstack](https://github.com/bostondv/bdvstack). The repo serves two purposes simultaneously:

1. **Marketplace** — installable on any machine via `/plugin marketplace add joycelin-instacart/joyce-claude` and `/plugin install <name>@joyce-claude`.
2. **Backup** — a verbatim mirror of `~/.claude/skills/` and `~/.claude/commands/` for easy diff and restore.

The local source of truth stays at `~/.claude/`. The repo is downstream — sync is one-way (`~/.claude` → repo). Sync runs automatically at the end of every Claude turn via a global `Stop` hook.

## Scope

In scope:

- Repo at `github.com/joycelin-instacart/joyce-claude` (private).
- Local clone at `~/joyce-claude`.
- Six personal skills packaged as plugins, each in its own folder: `ai-fluency`, `commit-and-push`, `create-branch`, `create-pr`, `daniel`, `find-skill-candidates`.
- One personal command (`find-skill-candidates.md`) bundled into the matching plugin.
- Raw mirror of all six skills + commands under `backup/`.
- Auto-generated `.claude-plugin/marketplace.json` registering every plugin.
- A `sync.sh` script that packages, mirrors, commits, and pushes.
- A global `Stop` hook in `~/.claude/settings.json` that invokes `sync.sh` after every turn.

Out of scope:

- Modifying the contents of any personal skill.
- Symlinking or removing the originals in `~/.claude/skills/` — they stay as-is.
- Touching anything from installed marketplaces (`bdvstack`, `claude-plugins-official`, `instacart`).
- Multi-machine restore tooling (manual `git clone` is fine for now).
- Promoting `find-skill-candidates`'s `evals/` or `scripts/` into separate plugins — they ride along with the parent skill.

## Repo Layout

```
joyce-claude/                          # github.com/joycelin-instacart/joyce-claude (private)
├── README.md                          # Install instructions + plugin table (bdvstack-style)
├── .claude-plugin/
│   └── marketplace.json               # Auto-generated; registers all plugins
├── ai-fluency/                        # Plugin 1
│   ├── .claude-plugin/plugin.json
│   └── skills/ai-fluency/SKILL.md     # + sibling files (evals/, scripts/, etc.)
├── commit-and-push/                   # Plugin 2 — same shape
├── create-branch/                     # Plugin 3
├── create-pr/                         # Plugin 4
├── daniel/                            # Plugin 5
├── find-skill-candidates/             # Plugin 6
│   ├── .claude-plugin/plugin.json
│   ├── commands/find-skill-candidates.md   # Thin wrapper command
│   └── skills/find-skill-candidates/       # SKILL.md + evals/ + scripts/
├── backup/                            # Raw mirror — easy diff/restore
│   ├── skills/                        # Verbatim copy of personal ~/.claude/skills/
│   └── commands/                      # Verbatim copy of ~/.claude/commands/
├── docs/specs/                        # Design docs (this file lives here)
└── scripts/
    └── sync.sh                        # Stop hook invokes this
```

**Layout decisions:**

- **One skill = one plugin.** No thematic grouping. Plugin name = skill name. Lets `/plugin install ai-fluency@joyce-claude` work on any machine without bundling unrelated skills.
- **`backup/` duplicates the plugin folders.** Pure cost; the upside is a single flat tree that's easy to grep, diff, and restore from without walking plugin folders.
- **`docs/specs/` lives inside the repo.** The repo documents its own design.

## Sync Mechanism

### Script: `~/joyce-claude/scripts/sync.sh`

Behavior, in order:

1. **Fast-path no-op.** Hash `~/.claude/skills/` and `~/.claude/commands/` (e.g., `find ... -exec sha256sum {} +` piped to a single hash, or `mtime`-based check). Compare against the last-run hash stored at `~/joyce-claude/.sync-state`. If unchanged, exit 0 immediately. Stop hooks fire every turn — the common case must be sub-100ms.
2. **Enumerate personal skills.** Every top-level directory under `~/.claude/skills/` is personal by definition — marketplace-installed skills live under `~/.claude/plugins/cache/<marketplace>/<plugin>/skills/`, not here. No hand-maintained seed list; the directory walk is authoritative, so a new skill added later (`~/.claude/skills/foo/`) gets packaged on the next sync automatically.
3. **For each personal skill:**
   - `rsync -a --delete` it to `backup/skills/<name>/`.
   - `rsync -a --delete` it to `<name>/skills/<name>/` (the plugin folder).
   - If `<name>/.claude-plugin/plugin.json` doesn't exist, scaffold it from the skill's SKILL.md frontmatter (name, description, version defaulting to `1.0.0`).
4. **For each personal command** under `~/.claude/commands/`: mirror to `backup/commands/`. If a command's basename matches a skill name, also copy it into that plugin's `commands/` folder. Otherwise it lives in `backup/` only — the script logs a warning so Joyce can decide whether to promote it to a standalone plugin later.
5. **Regenerate `.claude-plugin/marketplace.json`** from the plugin directories that exist. New plugin folder → new entry. Deleted plugin folder → entry dropped. Each entry: `name`, `source: ./<name>`, `description` (from plugin.json), `version` (from plugin.json), `author: { name: "Joyce Lin" }`.
6. **Commit + push** if there's a diff: `git add -A && git commit -m "sync: <changed skill names>" && git push`. If push fails (offline, auth expired), log and exit nonzero. The next successful turn re-syncs with accumulated changes.
7. **Logging.** Append to `~/joyce-claude/.sync.log` with timestamp, action summary, and exit status. Failures are debuggable without polluting the Claude chat.

### Hook: `~/.claude/settings.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "~/joyce-claude/scripts/sync.sh", "timeout": 30 }
        ]
      }
    ]
  }
}
```

Scope: **global** (fires for every Claude session in every project, including work repos like `carrot/customers-backend`). The 30s timeout caps worst-case impact; the no-op fast-path keeps the common case under ~100ms. Hook failures don't break Claude — they only mean the next turn re-syncs.

### Edge Cases

| Case | Behavior |
|---|---|
| Push fails (offline, auth) | Log + exit nonzero; next successful turn pushes accumulated changes. |
| Edits made outside Claude | Caught on next turn's Stop hook (script diffs against `~/.claude/`, not against what Claude touched). |
| Skill renamed in `~/.claude/skills/` | Old plugin folder dropped, new one added on next sync (directory walk is authoritative). |
| Skill deleted in `~/.claude/skills/` | Plugin folder + `backup/skills/<name>/` removed; marketplace.json entry dropped. |
| First run on fresh machine | Empty repo → every personal skill gets packaged + backed up in one initial commit. |
| New skill added to `~/.claude/skills/` | Auto-detected on next sync, packaged as a new plugin, marketplace.json updated. |
| Skill installed via someone's marketplace (e.g., bdvstack) | Excluded — those live under `~/.claude/plugins/cache/`, not `~/.claude/skills/`. |

## Bootstrap (One-Time Setup)

1. ✅ Create GitHub repo: `gh repo create joycelin-instacart/joyce-claude --private`.
2. ✅ Init local repo at `~/joyce-claude` with `main` branch, add `git@github.com:joycelin-instacart/joyce-claude.git` as `origin`.
3. ✅ Write README placeholder and this design spec; commit and push the initial commit.
4. ⏳ Write `scripts/sync.sh` per the spec above. Make executable.
5. ⏳ Run `sync.sh` once manually. Verify the diff (6 plugin folders, `backup/`, generated `marketplace.json`) looks correct before pushing.
6. ⏳ Push the seed commit.
7. ⏳ Wire up the Stop hook in `~/.claude/settings.json` via the `update-config` skill. This is the last step so the hook never fires against a half-built repo.
8. ⏳ Smoke test: touch a file in `~/.claude/skills/ai-fluency/`, let a turn end, confirm the hook fires, the script commits + pushes, and the change reflects on the remote.

## Testing

- **Script unit-level:** run `sync.sh` manually in five states — empty repo, no changes, one skill changed, new skill added, skill deleted — and verify the diff each time.
- **Hook integration:** trigger a Claude turn after each script-level test; confirm the hook runs the script and the script outcome matches.
- **Idempotency:** run `sync.sh` twice in a row with no changes — second invocation must be a fast-path no-op (no commit, no push, no log noise beyond a single "no-op" line).
- **Failure mode:** simulate a push failure (e.g., temporarily rename `~/.ssh/known_hosts`); confirm the script exits nonzero, logs the failure, and the next successful run catches up.

## Open Questions

None at design time. All choices made during brainstorming:

- Repo host: `joycelin-instacart` (work account, private repo).
- Repo name: `joyce-claude`.
- Repo shape: marketplace + backup.
- Sync trigger: global `Stop` hook.
- Commit prefix: `sync: ...`.
- Seed: all six existing personal skills + the one command.
