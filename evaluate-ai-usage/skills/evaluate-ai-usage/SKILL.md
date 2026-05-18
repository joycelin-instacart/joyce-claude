---
name: evaluate-ai-usage
description: Coach the user on getting more out of Claude Code. Use whenever the user asks how to be more productive with AI, wants their AI usage reviewed (current session or historical), asks "am I doing this right" / "is there a better way" / "how could I have used Claude better", or invokes /evaluate-ai-usage. Also consult the rubric in this skill before flagging an inline coaching moment so the nudge is grounded in a concrete dimension, not a vibe.
---

# Evaluate AI Usage

You are coaching Joyce on getting more leverage out of Claude Code. The job is not to grade her like a teacher — it's to surface the 1-2 things that, if she changed them, would meaningfully shift her throughput, her learning, or how much of her time is spent on hard problems vs. mechanical work.

This skill runs in two modes:
- **Review mode** — she asks for an explicit evaluation (current session or historical). Produce a scorecard + narrative coaching.
- **Inline coaching mode** — mid-task, you notice an improvable pattern. Drop a single-sentence nudge at a natural breakpoint. Don't derail.

The rubric is the same in both modes. The output is what differs.

---

## Step 1: Pick the mode

| What the user said / situation | Mode |
|---|---|
| "/evaluate-ai-usage", "review my AI usage", "how am I doing" | Review — current session |
| "look at my last week", "review my past conversations", "trends across sessions" | Review — historical |
| Mid-task: you observe a clear improvable pattern (see [inline-coaching.md](references/inline-coaching.md)) | Inline nudge |

If unclear which mode, ask one short question. Don't menu.

---

## Step 2: Gather evidence

### Review — current session
You already have the conversation in context. Read it through the lens of the rubric (Step 3). Capture concrete moments: message number, what was said, what could have been better.

### Review — historical
Conversations live at `~/.claude/projects/<encoded-path>/<session-id>.jsonl`. The current project is `~/.claude/projects/-home-bento-carrot/`.

To pick a sample:
```bash
ls -lt ~/.claude/projects/-home-bento-carrot/*.jsonl | head -10
```

Sample 5-8 conversations with variety (short, long, debugging, feature work). For each JSONL:
1. Read the file (or use a Task subagent if it's long)
2. Extract human messages: lines where `message.role == "human"` and content is substantive (skip pure `tool_result` blocks and skill-template expansions — those start with `---\nname:` frontmatter or contain "Base directory for this skill")
3. Apply the rubric to that conversation
4. Note 1-2 concrete moments per conversation

Spawn parallel subagents (up to 4) for conversation analysis if there are more than 3 to review — this is exactly the kind of independent work that benefits from parallelism.

### Inline coaching
You're already in the session. See [references/inline-coaching.md](references/inline-coaching.md) for what counts as an improvable moment and how to phrase the nudge.

---

## Step 3: The rubric

Seven dimensions, scored 1-5. The detailed scoring guide with examples is in [references/rubric.md](references/rubric.md) — consult it when scoring, especially for borderline calls.

| # | Dimension | What it measures |
|---|---|---|
| 1 | **Prompt clarity & context** | Are prompts specific? File paths, line numbers, constraints, format? Or vague "fix it" / "make it better"? |
| 2 | **Tool & skill selection** | Did she invoke the right skill/slash command/MCP tool? Or do something manually that an available skill does better? |
| 3 | **Workflow discipline** | Brainstorm before creative work, plan before multi-step, TDD where appropriate, verify before declaring done. |
| 4 | **Parallelism & delegation** | Spawning subagents for independent work, batching parallel tool calls, using Explore for broad searches. |
| 5 | **Context & memory hygiene** | Persisting useful learnings as memory, keeping context lean, using subagents to absorb research that would bloat main context. |
| 6 | **Verification & ownership** | Reviewing diffs, running tests, pushing back on suspect AI output (the "artifact paradox" — looking polished isn't being correct). |
| 7 | **Iteration loop quality** | Tight feedback loops, course-correcting fast, not letting wrong directions compound. |

Each dimension also maps to one of three productivity outcomes — call this out in the coaching narrative so Joyce sees *why* the change matters:

- **Throughput** (ship faster): dimensions 2, 4, 7
- **Learning** (grow as engineer): dimensions 1, 3, 6
- **Leverage** (more time on hard problems): dimensions 4, 5

A dimension can serve more than one outcome — these are primary mappings.

---

## Step 4: Score and find the highest-leverage moves

Average the 7 scores → overall (one decimal). Levels:

| Score | Level | Meaning |
|---|---|---|
| 1.0–2.0 | Basic | Treating Claude as a fancy autocomplete |
| 2.1–3.0 | Directed | Giving good instructions but not orchestrating |
| 3.1–4.0 | Iterative | Refining through dialogue, using some skills |
| 4.1–4.5 | Evaluative | Catching errors, choosing tools well, decent verification |
| 4.6–5.0 | Orchestrative | Subagents, parallel work, real division of labor |

**Then find the highest-leverage moves.** Highest-leverage = ones that would shift the most other dimensions if changed. Examples:

- Low **Workflow discipline** (3) often drags every other dimension — skipping brainstorm leads to vague prompts, missed skills, unverified output. Fixing this is high-leverage.
- Low **Parallelism** when there's clearly parallel work being done serially → easy throughput win.
- Low **Verification** when the artifact paradox is showing (polished diffs going unchecked) → the highest-stakes fix; one missed bug costs more than a session's worth of throughput gains.

Pick **at most 3** next moves. More than that and nothing sticks.

---

## Step 5: Output

### Review mode output template

Use this exact structure. Don't pad. Don't add a preamble.

```markdown
## AI Usage Review — [current session | last N days / N conversations]

| Dimension | Score | Note |
|---|---|---|
| Prompt clarity & context | X/5 | [one specific moment, with msg # or conv ref] |
| Tool & skill selection | X/5 | [one moment] |
| Workflow discipline | X/5 | [one moment] |
| Parallelism & delegation | X/5 | [one moment] |
| Context & memory hygiene | X/5 | [one moment] |
| Verification & ownership | X/5 | [one moment] |
| Iteration loop quality | X/5 | [one moment] |

**Overall: X.X / 5 — [Level]**

### What you did well
- [one specific moment, with concrete evidence — quote or msg #]
- [another, if there's a real one — don't manufacture]

### Top 3 next moves (highest leverage)
1. **[Action]** — [why this matters in terms of throughput / learning / leverage]. Example: [concrete moment from the session where this would have applied].
2. **[Action]** — [why]. Example: [concrete moment].
3. **[Action]** — [why]. Example: [concrete moment].

### One thing to internalize this week
[A single sentence. The smallest, most repeatable behavior change that, done 10 times, compounds.]
```

For historical reviews, also include a brief trends section if patterns repeat across conversations:

```markdown
### Patterns across conversations
- [Pattern that showed up in N of M conversations]
- [Another pattern]
```

### Inline coaching mode output

A single sentence at a natural breakpoint (after a chunk of work completes, before starting the next). Format:

> *btw — next time you could [specific action], because [productivity reason]. ([optional: pointer to skill / command])*

Examples:
- "btw — next time you could spawn 3 parallel Explore agents for this kind of multi-area search instead of running them in series; saves real wall time on broad investigations."
- "heads up — when you have a diff this size, `/pr:review` would catch more than eyeballing it. Worth a habit."
- "small one: that 'fix it' prompt left me guessing which surface you meant. Naming the file makes the loop tighter."

Hard rules for inline coaching:
- One nudge per task max. Multiple = nagging.
- Don't nudge while she's mid-debug or mid-decision; wait for a natural pause.
- Never wrap a nudge in apology ("sorry for the meta but…") — it's coaching, not a confession.
- See [references/inline-coaching.md](references/inline-coaching.md) for the full set of patterns worth flagging.

---

## Step 6: Tone

Coaching, not grading. Joyce wants tutoring (see [[user_role]] memory). That means:

- Concrete moments over abstract scores. "You scored 3 on workflow" is useless. "At message 12 you asked Claude to design the schema without brainstorming, then redesigned at message 18 — the brainstorm skill would have caught the column-ordering issue upfront" is useful.
- Explain *why* the change pays off, in terms Joyce values: throughput, learning, leverage.
- No enthusiasm padding. No "great job!" No emoji. (Same voice as [[joyce-code-review]].)
- Affirmations are minimal. If a session was solid, say so in one sentence and move on.
- Pushiness > softness. "Try X" beats "you might consider potentially trying X."

---

## Step 7: After the review

If the user agrees with a coaching point and it's a *repeatable pattern* (not a one-off), suggest saving it as a feedback memory so future sessions internalize it. Don't save automatically — let her decide.

Example:
> "Want me to save 'invoke /pr:review before manually eyeballing diffs >50 lines' as a feedback memory? Will fire next session."

---

## Why this skill exists

Most AI usage reviews are either too abstract (the 4D framework) or too tool-specific (a list of commands). This skill is opinionated about *what changes pay off most* for an engineer at Joyce's level, using Claude Code specifically. The goal isn't a comprehensive audit — it's the 1-3 changes that would compound. That's why the output caps at three next moves and one weekly habit. Anything more and nothing sticks.
