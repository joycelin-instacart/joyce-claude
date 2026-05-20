---
name: stacked-pr
description: Use when the user wants to split a branch into a stack of dependent PRs using plain git + gh (no Graphite/stax). Triggers on "stacked PR", "stack this branch", "split this PR", "break into smaller PRs", "stack of PRs", "chain of PRs", "dependent PRs", or anytime the user has work on one branch that should land as multiple reviewable slices. Use even if the user doesn't say "stack" explicitly — if they have a large branch and want it split into smaller reviewable PRs, this skill applies.
---

# Stacked PR (plain git + gh)

Take work that currently lives on one branch and split it into a stack of small, dependent PRs using plain `git` and `gh` — no Graphite, no `stax`, no custom CLI required.

The goal is **reviewable slices**. Each PR in the stack is small, focused on one concern, and targets the branch below it (the bottom PR targets `master`/`main`).

## When this skill applies

- User has a branch with multiple logical changes mashed together and wants to split it
- User says "stacked PR", "stack this", "split this PR", "break this up", "this PR is too big"
- User wants a chain of dependent PRs but isn't using a stacking CLI

If the user explicitly asks for `stax` or Graphite, use the `stax` skill instead — this skill is for the plain `git + gh` flow.

## Pre-flight

Before touching anything, gather state in parallel:

```bash
git status                           # uncommitted work? clean?
git rev-parse --abbrev-ref HEAD      # current branch name
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'   # base branch (master vs main)
git log --oneline $(git merge-base HEAD <base>)..HEAD   # commits on this branch
git diff --stat $(git merge-base HEAD <base>)..HEAD     # rough file footprint
gh auth status                       # gh is authenticated
```

**Bail-outs:**
- **Uncommitted changes**: ask the user whether to commit, stash, or include them in the split before proceeding. Never silently discard work.
- **Already on base branch**: ask which branch they meant to split.
- **`gh` not authenticated**: stop and tell the user to run `gh auth login`.
- **Only one trivial commit**: there's nothing to stack — tell the user and stop.

## The workflow

### Step 1 — Understand the diff

Read the full diff (`git diff <base>...HEAD`) and group changes by **logical concern**, not by file boundary alone. Useful axes for grouping:

- Schema / migration vs. application logic vs. tests vs. config
- Independent features that just happen to be on the same branch
- "Plumbing" (refactor, new helper) vs. "behavior" (the actual change)
- Gate/flag wiring vs. the gated code
- Each commit's existing scope (if commits are already clean, honor them)

**Order matters.** Each slice must be a valid, mergeable change on its own assuming everything below it has landed. If slice 2 depends on a function added in slice 1, slice 1 must come first. Migrations come before code that reads new columns.

### Step 2 — Propose the split

Present a plan to the user **before changing any branches**. Format:

```
Proposed stack (bottom → top):

1. <branch-name-1>  — <one-line description>
   Files: <key files>
   Commits: <commit hashes if cleanly aligned, else "rework from diff">

2. <branch-name-2>  — <one-line description>
   Files: <key files>
   Commits: <...>

3. <branch-name-3>  — <one-line description>
   ...
```

Ask the user to confirm or adjust before you proceed. They may want to merge two slices, reorder, or pull something out. Honor their changes.

### Step 3 — Branch naming

Derive the user prefix from the current branch (the part before `/`). Number each slice and add a short slug:

```
<user-prefix>/<feature>-1-<slug>
<user-prefix>/<feature>-2-<slug>
<user-prefix>/<feature>-3-<slug>
```

Example: current branch is `joycelin-instacart/peacock-redemption-eligibility` → stack becomes `joycelin-instacart/peacock-redemption-1-gate`, `…-2-eligibility`, `…-3-tests`.

If the current branch has no `/` prefix, ask the user for a stack name and use `<name>-1-…` style.

### Step 4 — Safety net before executing

**Always create a backup branch** that mirrors the current state, so the original work is recoverable if the split goes sideways:

```bash
git branch <current-branch>.backup-$(date +%Y%m%d-%H%M%S)
```

Tell the user the backup branch name. Do not delete it — let them clean up later.

### Step 5 — Build the stack

For each slice, in order from bottom to top:

1. **Branch off the right parent.** Slice 1 branches off the base (`master`/`main`). Slice N branches off slice N-1.
   ```bash
   git checkout <parent-branch>
   git checkout -b <slice-branch>
   ```

2. **Bring in the changes for this slice.** Choose the approach that matches reality:
   - **Cherry-pick** if commits are cleanly aligned: `git cherry-pick <sha>...<sha>`
   - **Patch apply** if slicing within commits: build the slice from the original branch using `git checkout <original-branch> -- <paths>` then commit only the relevant chunks
   - **Manual reconstruction** if changes are tangled: open the files, leave only this slice's lines, commit

3. **Commit with a clear message** for that slice (don't blindly reuse the original commit message — it described the whole branch). Use the project's existing commit style (see `git log --oneline` from pre-flight).

4. **Push with `-u`**:
   ```bash
   git push -u origin <slice-branch>
   ```

### Step 6 — Open the PRs

Open PRs **from bottom to top**, so each one can correctly target the branch below it.

```bash
gh pr create \
  --base <parent-branch> \
  --head <slice-branch> \
  --title "<short title>" \
  --body "$(cat <<'EOF'
<body with stack table — see below>
EOF
)"
```

The bottom PR targets `master` (or `main`). Each subsequent PR targets the branch directly below it in the stack.

Capture each PR's number/URL as you create them — you'll need them for the stack table.

### Step 7 — Add the stack table

After all PRs are open, update each PR body to include the stack position table. The current PR is bolded:

```markdown
## Stack

| # | PR | Branch | Status |
|---|------|--------|--------|
| 1 | #101 | `joycelin-instacart/peacock-1-gate` | Open |
| 2 | **#102 (this PR)** | `joycelin-instacart/peacock-2-eligibility` | Open |
| 3 | #103 | `joycelin-instacart/peacock-3-tests` | Draft |

## Summary
…
```

Update with `gh pr edit <number> --body "$(cat <<'EOF' … EOF)"`. The summary/test-plan content goes below the stack table — keep the rest of your normal PR body conventions.

### Step 8 — Wrap up

Tell the user:
- The backup branch name
- Each PR URL with one-line summary
- Which branch they're currently on
- The next action: review the PRs, then merge bottom-up. After the bottom PR merges, run `git fetch && git rebase origin/<base>` on slice 2 and force-push (since its base in GitHub will auto-retarget once bottom merges).

## PR body conventions

- Title: short (under 70 chars), describes that single slice only
- Body: stack table at top, then `## Summary` and `## Test plan` (or the project's existing convention — check recent merged PRs with `gh pr list --state merged --limit 5`)
- End commit messages with `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`

## After PRs are open: handling updates

If the user requests changes on a mid-stack PR:

1. Check out that branch
2. Make the changes, commit (a new commit, not amend — easier to review)
3. Push the branch
4. **Rebase every branch above it** onto the updated branch:
   ```bash
   git checkout <slice-above>
   git rebase <updated-slice>
   git push --force-with-lease    # safer than --force
   ```
5. Repeat for each higher branch in order

Use `--force-with-lease`, never plain `--force`, on stack branches. This avoids overwriting someone else's push.

## After bottom PR merges

When PR 1 lands:

1. `git fetch origin`
2. GitHub auto-retargets PR 2's base to `master` once PR 1 merges (since the source branch is gone), but the branch itself still needs to be rebased onto `master`:
   ```bash
   git checkout <slice-2-branch>
   git rebase origin/master
   git push --force-with-lease
   ```
3. Repeat for higher slices as their parents merge.

## Don'ts

- **Don't** force-push without `--force-with-lease` on stacked branches.
- **Don't** delete the backup branch until the stack is fully merged.
- **Don't** rewrite history on the original branch — leave it alone; build the stack on new branches.
- **Don't** open all PRs as a single multi-branch push and hope `gh` figures it out — open them one at a time, bottom-up, so each `--base` is correct.
- **Don't** put the entire original PR body into every slice — each PR description should be about its own slice.
- **Don't** combine unrelated changes back into one slice just because they touch the same file. File overlap is fine; concept overlap is what matters.
- **Don't** invoke this skill if the user is using `stax` or Graphite — defer to those tools' skills.

## Quick reference

| Step | Command |
|------|---------|
| Backup current branch | `git branch <branch>.backup-$(date +%Y%m%d-%H%M%S)` |
| Create slice branch | `git checkout <parent> && git checkout -b <slice>` |
| Cherry-pick commits | `git cherry-pick <sha1> <sha2>` |
| Take files from another branch | `git checkout <branch> -- <paths>` |
| Push slice | `git push -u origin <slice>` |
| Create stacked PR | `gh pr create --base <parent> --head <slice> --title "…" --body "…"` |
| Update PR body | `gh pr edit <number> --body "…"` |
| Safe force-push after rebase | `git push --force-with-lease` |
