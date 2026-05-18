---
name: commit-and-push
description: Use when the user wants to review changes, commit with a conventional commit message, and push to the current branch, or invokes /commit-and-push
---

# Commit and Push

Review current changes, write a conventional commit message, commit, and push to the current branch.

## Workflow

1. **Gather context** (run in parallel):
   - `git status` — see what's changed
   - `git diff` and `git diff --staged` — understand the actual changes
   - `git log --oneline -10` — see recent commit style
   - `git branch --show-current` — confirm current branch

2. **Review changes**:
   - Summarize what changed and why to the user
   - Flag any files that look sensitive (.env, credentials, tokens) — ask before staging those
   - If there are no changes to commit, tell the user and stop

3. **Coverage check, scoped to changed files** (Ruby projects with SimpleCov only — skip if no `Gemfile`):
   - Build the changed-source list from `git diff --name-only HEAD` + untracked Ruby files. Keep only app/lib code (e.g. `app/**/*.rb`, `lib/**/*.rb`, `engines/*/{app,lib}/**/*.rb`, `domains/*/app/**/*.rb`). Skip pure spec/doc/config-only changes — if nothing remains, skip this step.
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
   - If either is below 100, STOP. Do not commit. Report which lines/branches are uncovered (parse `coverage/.resultset.json` or surface gaps from the HTML report) and ask the user how to proceed.
   - If specs fail, STOP and report — never commit on red.

4. **Stage and commit**:
   - Stage relevant changed files by name (prefer explicit file names over `git add -A`)
   - Write a conventional commit message following the [Conventional Commits](https://www.conventionalcommits.org/) format:
     - `feat:` for new features
     - `fix:` for bug fixes
     - `refactor:` for refactoring
     - `test:` for test changes
     - `docs:` for documentation
     - `chore:` for maintenance tasks
     - `style:` for formatting changes
     - `perf:` for performance improvements
     - Include a scope when obvious, e.g. `feat(auth):` or `fix(cart):`
     - Subject line: imperative mood, lowercase, no period, under 72 characters
     - Add a body if the change is non-trivial (separated by blank line)
   - End with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
   - Always use a HEREDOC for the commit message

5. **Push**:
   - Push to the current branch: `git push origin HEAD`
   - Use `-u` flag if the branch has no upstream tracking yet
   - If push fails due to divergence, inform the user and ask how to proceed — never force-push

6. **Confirm** — show the user the commit hash and that the push succeeded.

## Rules

- Never force-push or amend existing commits.
- Never push to main/master — warn and stop if on those branches.
- Never skip pre-commit hooks (no `--no-verify`).
- Ask before committing files that look sensitive.
- If a pre-commit hook fails, fix the issue and create a NEW commit (do not amend).
