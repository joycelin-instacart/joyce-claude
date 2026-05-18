---
name: create-branch
description: Use when the user wants to create a new feature branch from a ticket number or description, or invokes /create-branch
---

# Create Branch

Create and check out a new branch off master with a consistent naming convention.

## Workflow

1. **Get GitHub username**:
   - Run `gh api user --jq '.login'` to get the GitHub username
   - Use it as-is (e.g., `joycelin-instacart`)

2. **Parse the input** (`$ARGUMENTS`):
   - Input may be a ticket number (e.g., `PROJ-123`), descriptive text (e.g., `add retry logic to checkout`), or a ticket number followed by descriptive text (e.g., `PROJ-123 add retry logic`)
   - If only a ticket number is given, use it as context to infer a descriptive slug (look up the ticket title if possible, or ask the user for a description)
   - From any descriptive text, derive a short (2-5 word) meaningful slug
   - Do NOT include the ticket number in the branch name

3. **Generate branch name**:
   - Format: `{username}/{description-slug}`
   - The slug should be lowercase, hyphen-separated, concise, and descriptive
   - Keep the total branch name under 60 characters when possible

4. **Confirm with the user**:
   - Show the proposed branch name
   - Ask for confirmation before creating

5. **Create the branch**:
   - `git fetch origin master`
   - `git checkout -b {branch-name} origin/master`

## Examples

| Input | Branch Name |
|-------|------------|
| `CXP-12345` | `joycelin-instacart/ei-backfill-error-handling` (inferred from ticket title) |
| `fix flaky rspec tests in checkout domain` | `joycelin-instacart/fix-flaky-checkout-specs` |
| `add retry logic` | `joycelin-instacart/add-retry-logic` |
