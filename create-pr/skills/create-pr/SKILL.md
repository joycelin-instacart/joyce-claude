---
name: create-pr
description: Use when the user wants to commit current changes and open a pull request in one step, or invokes /create-pr
---

# Create PR

Commit all current changes and open a pull request with a well-crafted title and description.

## Workflow

1. **Gather context** (run in parallel):
   - `git status` — see what's changed
   - `git diff` and `git diff --staged` — understand the actual changes
   - `git log --oneline -10` — match commit message style
   - `git log --oneline main..HEAD` (or master) — see all branch commits so far
   - Identify the base branch (main or master)

2. **Coverage check, scoped to changed files** (Ruby projects with SimpleCov only — skip if no `Gemfile`):
   - Build the changed-source list from `git diff --name-only $(git merge-base HEAD <base-branch>)..HEAD` + uncommitted + untracked Ruby files. Keep only app/lib code (e.g. `app/**/*.rb`, `lib/**/*.rb`, `engines/*/{app,lib}/**/*.rb`, `domains/*/app/**/*.rb`). Skip pure spec/doc/config-only changes — if nothing remains, skip this step.
   - Map each changed source file to its matching spec (mirror the path under `spec/` or `engines/*/spec/`, with `_spec.rb`). If any changed source file has no spec, STOP and ask the user.
   - For customers-backend (and similar Rails-engines projects) run:
     ```
     DISABLE_SIMPLECOV=0 REQUIRED_ENGINES=<engines-csv> \
       SIMPLECOV_INCLUDE_FILTER=<changed-source-files-csv> \
       bundle exec rspec <matching-spec-files>
     ```
     Derive `REQUIRED_ENGINES` from spec paths (e.g. `engines/graph/...` → `graph`; combine multiple as comma-separated). For projects without engines, omit `REQUIRED_ENGINES`. See `.claude/commands/run-tests.md` if present.
   - Then run `open coverage/index.html`.
   - Read `coverage/.last_run.json` and verify both `line` and `branch` are `100.0` (since `SIMPLECOV_INCLUDE_FILTER` restricts tracking to the changed files, this is per-changed-file 100%).
   - If either is below 100, STOP. Do not commit or open a PR. Report which lines/branches are uncovered (parse `coverage/.resultset.json` or surface gaps from the HTML report) and ask the user how to proceed.
   - If specs fail, STOP and report — never open a PR on red.

3. **Stage and commit**:
   - Stage all relevant changed files (prefer explicit file names over `git add -A`)
   - Do NOT stage files that look like secrets (.env, credentials, tokens)
   - Write a concise commit message summarizing the changes
   - End with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

4. **Push and create PR**:
   - Push the branch to origin with `-u` if needed
   - Create the PR using `gh pr create` targeting the base branch
   - PR title: short, under 70 characters, descriptive of the overall change
   - PR body format: refer to existing PRs for the body format

4. **Return the PR URL** to the user.

## Rules

- If there are no changes to commit, skip the commit step and just create the PR from existing commits.
- If already on main/master, ask the user for a branch name first.
- Always use a HEREDOC for multi-line commit messages and PR bodies.
- Never force-push or amend existing commits.
- Ask before committing files that look sensitive.
