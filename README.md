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
