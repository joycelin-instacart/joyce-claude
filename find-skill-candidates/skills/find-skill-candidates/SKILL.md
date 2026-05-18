---
name: find-skill-candidates
description: Use when the user wants to analyze their Claude Code prompt history to find recurring asks that could be automated into skills. Triggers on phrases like "find skill candidates", "what should I automate?", "analyze my prompts", "are there skills I should create?", "look at my recent Claude usage and suggest skills", or "/find-skill-candidates". Surfaces clusters of semantically similar prompts, dedupes against skills/commands the user already has, and offers to hand each accepted candidate off to skill-creator with a pre-filled brief.
---

# find-skill-candidates

Find recurring patterns in the user's Claude Code prompt history and propose skills to automate them.

## When to invoke

The user wants to know what repetitive AI work they're doing — what they keep typing variations of — and whether any of it should become a reusable skill. They typically aren't naming a specific problem; they're asking you to look at their behavior and surface candidates.

## The workflow

### 1. Find the transcripts directory

Claude Code stores transcripts at `~/.claude/projects/<cwd-with-slashes-as-dashes>/*.jsonl`. Derive the path from the current working directory:

```bash
echo "$HOME/.claude/projects/$(pwd | sed 's|/|-|g')"
```

If that directory doesn't exist, fall back to asking the user which project to analyze, or list available dirs under `~/.claude/projects/` so they can pick.

By default analyze **only the current project** — the user picked that scope intentionally because cross-project signal is noisy.

### 2. Run the extraction script

```bash
python3 ~/.claude/skills/find-skill-candidates/scripts/extract_prompts.py <transcripts_dir>
```

Useful flags:
- `--days N` — only keep prompts from the last N days
- `--min-chars N` — raise the minimum prompt length (default 10)
- `--max-chars N` — truncate each prompt to this length (default 2000). Long prompts are usually pasted CI logs or error blobs; the leading text is all you need for clustering. Truncated prompts are flagged with `"truncated": true`.

The script filters out tool results, skill content blocks, slash-command bodies, system reminders, hooks, continuation noise ("ok", "yes"), and bare slash invocations. What remains is the user's genuine ad-hoc typing.

If you get more than ~500 prompts back, suggest `--days 30` or `--days 60` to keep the analysis tractable.

### 3. Load the existing-skills inventory

Always pass `--project-root` set to the **cwd** (not the git root — in a monorepo the subproject sits below the root). The script walks up from there collecting every `.claude/skills/` and `.claude/commands/` it finds, so passing the deepest dir captures both subproject-level and repo-level skills.

```bash
python3 ~/.claude/skills/find-skill-candidates/scripts/list_existing_skills.py --project-root "$(pwd)"
```

The inventory covers user-level skills, plugin skills (deduped across cached versions), project-level skills, and slash commands from both user-level and project-level. You'll need this to avoid recommending duplicates and to flag the more interesting case: **the user keeps typing X but already has a skill for X and isn't using it.**

### 4. Cluster the prompts semantically

Read the prompts and group them by *intent*, not by wording. Examples of valid clustering:

- "rebase onto master and push", "rebase on latest master", "could you rebase onto latest master and push again?" → **rebase-and-push**
- "run rspec for these files", "run tests on the changed file", "test this" → **run-tests-for-changes**
- "create a worktree for X", "spin up a new worktree to do Y", "graft a worktree for Z" → **create-worktree**

Skip clusters that are clearly:
- One-off questions ("what does this function do?")
- Conversational follow-ups ("can you explain that more?")
- Project-specific work that won't recur ("update the Kroger discount yaml")
- Things any LLM does fine without a skill (general code questions)

You're looking for **workflows** — sequences of steps, conventions, or domain-specific setup — not single questions.

### 5. Apply the qualification filter

A cluster qualifies as a skill candidate when **all** of:

- It has **≥3 prompts** across **≥2 sessions** (default; tune if the user asked for stricter or looser)
- The work has structure beyond "ask LLM a question" — there's a recipe, a checklist, a sequence, or domain-specific knowledge that would otherwise be re-derived each time
- An existing **installed** skill doesn't already cover it (per the inventory from step 3). If one does, classify the cluster as one of:
  - **🔁 Underused existing skill** — the user has the skill but keeps typing the long-form prompt instead of invoking it. Worth surfacing because the fix is probably "make the existing skill trigger better" or "use a slash alias", not "build a new skill".
  - **🛠 Existing skill needs improvement** — they have it but the cluster shows recurring frustration ("retry", "that didn't work, try X"). Surface as an improvement candidate.
  - **✅ Already covered, working fine** — drop it.

### 5.5. Check the marketplace for clusters that survived the local check

For every cluster still classified as a *new* skill candidate after step 5, check whether the Instacart plugin marketplace already ships something that would solve it. The local inventory only covers what the user has installed; the marketplace covers what's available to install — and recommending "build a skill" when "install a plugin" would do is the worst possible outcome.

Invoke the `find-plugin` skill (via the `Skill` tool) once per surviving cluster, passing a natural-language query that captures the cluster's intent. Phrase the query the way a real user would search — use the recipe/example prompts as raw material, not the kebab-case name you assigned. For example, for a cluster you internally called `rebase-and-push`, query find-plugin with something like *"rebase the current branch onto master and push"* rather than *"rebase-and-push"*.

You can batch these as parallel `Skill` invocations if there are several candidates — they're independent lookups.

For each marketplace response, judge match strength yourself:

- **High confidence** — a plugin's skill description clearly covers the cluster's intent (overlapping verbs/nouns, same workflow shape). Reclassify the cluster as **📦 Available in marketplace** and capture the plugin name plus the install command.
- **Low confidence / no match** — keep the cluster as a 🆕 new candidate.
- **Partial match** — a plugin exists but only covers part of the cluster. Keep the cluster as 🆕 but note the related plugin in the report so the user knows about the adjacent tool.

Don't over-trust find-plugin: it returns the *top few* matches by semantic similarity, which can include weak matches when nothing strong exists. If the returned plugin's description doesn't actually solve what the user keeps typing about, treat it as no match.

### 6. Present the report

Use this exact structure so the user can scan it quickly:

```markdown
# Skill candidates from <N> prompts across <M> sessions

## 🆕 New skill candidates

### 1. <kebab-case-name> — <one-line description>
**Frequency:** <count> prompts across <session-count> sessions
**Recipe:** <2-3 sentence summary of what the skill would do>
**Example prompts:**
- "<example 1>"
- "<example 2>"
- "<example 3>"
**Why it's skill-worthy:** <what makes this more than a one-line LLM ask>

### 2. ...

## 📦 Available in marketplace (install instead of build)

### <plugin-name> · <team or "Org-wide">
Matches your cluster of <count> prompts about <topic>.
**Plugin skill(s):** <skill names returned by find-plugin>
**Install:** `/plugin install <plugin-name>@instacart`

## 🔁 Underused existing skills

### <existing-skill-name>
You have the `<name>` skill but typed <count> long-form variants instead of invoking it.
**Suggested fix:** <e.g., "add 'X' phrasing to the description", "alias as /<name>", "stop redundant typing">

## 🛠 Skills worth improving

### <existing-skill-name>
<short reason>

## Drops (not surfaced)
<one-line summary: "skipped N one-off questions, N trivial single-tool calls">
```

Omit any section that has no entries — don't print an empty "📦 Available in marketplace" header.

### 7. Ask which to act on

End the report with a question. Always use plain text — the candidate list typically exceeds the `AskUserQuestion` 4-option cap, and users want to be able to pick several or say "none". Phrase it like:

> Which would you like to build? You can pick several by number, or say "none" to just keep the analysis.

### 8. Hand off to skill-creator

For each candidate the user accepts, invoke the `skill-creator:skill-creator` skill with a brief like:

```
I want to create a skill named <name>. Based on prompt-history analysis,
here's what it should do:

Purpose: <description from report>
Trigger phrases (real examples from history):
  - "<example 1>"
  - "<example 2>"
  - "<example 3>"
Recipe: <recipe from report>

Please proceed with the skill-creator workflow.
```

Don't try to write the skill yourself — let skill-creator drive its own interview/draft/eval flow. You're just feeding it a warm start.

For "🔁 Underused existing skill" hits, don't hand off to skill-creator. Instead, suggest a direct fix to the existing skill's description or an alias — and ask the user if they want you to make that edit.

For "📦 Available in marketplace" hits, don't hand off to skill-creator either. Show the `/plugin install <name>@instacart` command and ask if they want you to run it (or run `/find-plugin <plugin-name>` for more detail before deciding).

## Things to avoid

- **Don't surface every cluster.** If there's nothing skill-worthy, say so plainly. A short honest "I looked at your 80 recent prompts and didn't find anything that warrants a skill" is more useful than padding the report.
- **Don't recommend a skill for something the LLM already does fine.** "Explain this Ruby method" doesn't need a skill. "Walk through our specific 6-step domain-event consumer migration" does.
- **Don't dump raw prompt examples without redacting.** If a prompt contains an internal URL, a ticket ID, or a customer name, paraphrase it in the report unless that detail is load-bearing.
- **Don't conflate frequency with value.** "run git status" might appear 50 times — it's not a skill candidate; it's a one-tool command.

## Tuning notes

The default threshold (≥3 prompts, ≥2 sessions) is conservative to keep the report short. If the user wants a wider net, they'll say so — drop it to ≥2 prompts. If they want stricter, raise to ≥5.

The current-project default is intentional. If the user wants cross-project analysis, they need to point the script at a parent dir or iterate through several projects — surface that as an option, don't auto-do it.
