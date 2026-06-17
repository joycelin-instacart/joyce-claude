---
name: push-to-personal-staging
description: Deploys a branch or PR to Joyce's personal ISC staging stack (the `icapp` app under user `joycelin`, via `isc staging create-stack` / `isc launch` on the remote `staging` env). Trigger whenever Joyce wants to put her branch or a PR onto her own personal/joycelin staging — including "push to my staging", "push it to my joycelin stack", "throw this PR on my staging", "get this onto my personal staging", "deploy current branch to my staging", "stand up my personal stack from this branch", "rebuild my joycelin stack with this branch", "tear it down and redeploy", "blow away my joycelin and spin it back up", "stale stack fresh feature — redeploy". The words "joycelin", "my joycelin stack", "my personal staging", "my icapp staging", or "my staging" plus a deploy/push/throw/stand-up/rebuild/redeploy/blow-away verb always mean THIS remote ISC stack — not local bento dev services. Do NOT trigger when Joyce asks to set up a DIFFERENT named stack (e.g. "name it ictc-pilot, not joycelin"), when she wants to view/debug existing stack state without redeploy, when she only wants to delete without redeploy, on isc doc/concept questions, or on pure git work (rebase, push to origin, open PR).
---

# Push a PR or branch to Joyce's personal staging stack

Joyce uses one personal staging stack (`icapp`, user `joycelin`, on the `staging` environment). The workflow she wants every time:

1. Tear it all down (`isc staging delete-stack icapp --user joycelin --yes`).
2. Stand it back up with every service on `master` (`isc staging create-stack icapp --user joycelin --branch master`).
3. Override the single service her branch changes so it deploys her branch instead (`isc launch -e staging joycelin.<service> icapp@<branch>`).

The reason she insists on a full delete/recreate (rather than a targeted patch) is that personal-stack state drifts — old launches, stale conf, half-failed deploys — and starting from a known-clean master baseline is faster than triaging whatever the stack looked like last week. So **never skip the delete step** to "save time."

These steps cost real money and real wall-clock time (create-stack is ~20–40 min). The skill must confirm before each destructive step and **must not** auto-run them in series without checking in.

## Inputs

The user invocation may name:

- a branch (`joyce/my-feature`), with or without a `joycelin/` style prefix,
- a PR number (`812948`),
- a full PR URL (`https://github.com/instacart/carrot/pull/812948`), or
- nothing — meaning "use my current branch."

Resolve to a canonical branch name before anything else:

- Number or URL → `gh pr view <num> --json headRefName -q .headRefName` (URL: parse the number out first).
- Branch name → verify it exists locally or on `origin`; `git fetch origin <branch>` if needed.
- Empty → `git rev-parse --abbrev-ref HEAD`. If that is `master`, stop and ask Joyce what branch she meant — there is nothing to override.

## Detect the service

The skill assumes it runs from the `carrot` repo (`/home/bento/carrot`). If `pwd` is elsewhere, `cd` there first.

Use the bundled helper — it walks up from each changed file to the nearest `.isc/config.yml` and prints unique owning service directory names:

```bash
scripts/detect_service.sh <branch>
```

Interpret the result:

| Output | What to do |
|---|---|
| Exactly one service name | Show Joyce: "Detected service: `<name>`. Override this one on `<branch>`?" Wait for y/N before proceeding. |
| Two or more service names | Print the list, ask Joyce which one to override. `isc staging` overrides one service at a time, and forcing a guess here is exactly the kind of "AI assumed" failure that wastes a 30-min stack rebuild. |
| Exit code 1 ("no ISC service…") | Print the changed files and stop. The branch only touches shared code / docs / CI — there is no service to override, so the whole workflow doesn't apply. Suggest Joyce either narrow the change or run `isc staging create-stack` herself if she just wants a fresh master stack. |

**Don't guess from filenames or directory names alone** — the `.isc/config.yml` walk-up is the authoritative mapping. A file under `customers/store/` that lives inside a sub-tree with its own `.isc/config.yml` belongs to *that* sub-service, not to `store`. The helper handles this correctly; second-guessing it from the path will pick the wrong service.

## Show the plan, then run it with confirmation gates

Before running anything, print the full plan so Joyce can sanity-check it once. Format:

```
Plan
  Branch:   joyce/my-feature
  Service:  store          (detected from 3 changed files under customers/store/)
  Stack:    icapp / user=joycelin / env=staging

Steps
  1. isc -e staging staging delete-stack icapp --user joycelin --yes
  2. isc -e staging staging create-stack icapp --user joycelin --branch master
  3. isc launch -e staging joycelin.store icapp@joyce/my-feature
```

Then execute the steps one at a time, asking before each. Each step is a separate, blocking gate:

1. Ask "Run step 1 (delete-stack)? [y/N]". On yes, run it and stream output. On no, stop entirely — don't skip ahead.
2. After step 1 finishes, ask "Run step 2 (create-stack on master)?". On yes, run and stream. This is the long one; let it finish before continuing.
3. After step 2 finishes, ask "Run step 3 (override `<service>` to `<branch>`)?". On yes, run and stream.

Stop and surface any non-zero exit code from any step — don't continue with the next step if the previous one failed.

## Defaults the skill should keep

- `--user joycelin` is fixed. It's Joyce's personal stack name; don't parameterize it.
- `-e staging` on every `isc` invocation. The `isc staging` warning about needing `-e` is real — without it you get noise and possibly the wrong environment.
- `icapp` is the only stack `isc staging` supports here. Don't try to abstract it.
- `--yes` on `delete-stack` is intentional: the confirmation gate is the skill's own y/N prompt, not isc's interactive one (which is hard to drive over a non-tty pipe).

## What to report at the end

After all three steps succeed, write a short summary:

- The personal-staging URL pattern Joyce uses to reach the stack (if known from `create-stack` output — surface whatever URL/host isc printed).
- The branch the override is running.
- The total wall-clock time, so Joyce knows what to expect next time.

If a step failed, report which step, paste the last ~20 lines of its output, and stop. Don't try to "fix" a failed stack rebuild — Joyce will want to look at it herself.
