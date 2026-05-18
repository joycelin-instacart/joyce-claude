# Detailed Rubric

Use this when scoring borderline cases. Each dimension has anchored examples drawn from Claude Code workflows so the score reflects observable behavior, not a hunch.

---

## 1. Prompt clarity & context

What you're checking: does each prompt give Claude what it needs to act with judgment, or does it leave Claude guessing?

| Score | Pattern |
|---|---|
| 1 | Single-word or fragment prompts ("fix it", "broken", "help"). No file refs, no constraints, no context. |
| 2 | States the *what* but not the *where*, *why*, or constraints. "Add validation to the user form." |
| 3 | Names files/areas, sometimes adds constraints. "Add email validation to `app/forms/signup_form.rb`, the same way password validation works." |
| 4 | Includes constraints, format expectations, and the *why*. Points to precedent. Anticipates one likely confusion. |
| 5 | Pre-written mini-spec for non-trivial work: file paths with line numbers, acceptance criteria, scope boundary ("don't touch X"), and a note on which approach was rejected and why. |

**Red flags:**
- Asking the same question 3 times with slightly different words instead of adding context.
- "Make it better" without saying what "better" means.
- Pasting code with no instruction beyond "thoughts?"

**Boost signals:**
- File:line refs in the prompt itself.
- Saying what *not* to do, not just what to do.
- Pre-empting an obvious wrong direction.

---

## 2. Tool & skill selection

What you're checking: does she invoke the right skill / slash command / MCP tool, or do things manually that an installed skill does better?

| Score | Pattern |
|---|---|
| 1 | Doesn't use any skills. Doesn't know they exist. Does everything by hand. |
| 2 | Uses 1-2 familiar skills (e.g., `/create-pr`) but defaults to manual for everything else. |
| 3 | Uses skills when the user types the slash command, but doesn't reach for relevant skills proactively. |
| 4 | Recognizes when a skill applies and uses it without prompting; uses MCP tools (Glean, Buildkite, Slack) when relevant. |
| 5 | Knows the full skill inventory, picks the most specific tool every time, suggests new skills when patterns repeat (sees a thing done 3 times → "this should be a skill"). |

**Red flags:**
- Asking Claude to "check the PR" when `/pr:review` exists.
- Asking Claude to "look at the failing build" when `buildkite:buildkite` exists.
- Manually grepping when `Explore` agent would be faster.
- Asking for a code review without invoking `joyce-code-review`.

**Boost signals:**
- Reaching for a skill the moment its trigger condition matches.
- Recognizing that a request crosses two skills and sequencing them.

---

## 3. Workflow discipline

What you're checking: does she follow the process moves that prevent rework — brainstorm, plan, TDD, verification?

| Score | Pattern |
|---|---|
| 1 | Jumps straight to "build it". No brainstorm, no plan, no verification. |
| 2 | Occasionally plans for big things but skips it most of the time. |
| 3 | Plans multi-step work; usually verifies before declaring done. |
| 4 | Brainstorms before creative work; writes plans for non-trivial features; verifies via tests/linters; uses TDD where it fits. |
| 5 | Reaches for the right process discipline by default — brainstorm → plan → TDD → verify — and recognizes when to skip (e.g., one-line fixes). |

**Red flags:**
- Building a feature without brainstorming when the requirements are ambiguous.
- "It looks right" as the verification step.
- Skipping `superpowers:brainstorming` for net-new design work.
- Declaring done without running tests.

**Boost signals:**
- Writing a short plan unprompted before a 3+ step task.
- "Let me verify" → actually verifying.
- Catching her own assumption before Claude builds on it.

---

## 4. Parallelism & delegation

What you're checking: when there's independent work, is it parallelized? Does she dispatch subagents for things that would bloat context?

| Score | Pattern |
|---|---|
| 1 | Everything serial. Never spawns subagents. Tool calls always one at a time. |
| 2 | Occasionally parallel tool calls for "easy" cases (two grep calls). |
| 3 | Parallel tool calls when obvious. Uses subagents for big research tasks. |
| 4 | Routinely batches independent calls. Uses `Explore` for broad searches. Dispatches subagents to keep main context clean. |
| 5 | Designs work to maximize parallelism — spawns multiple subagents in one turn for genuinely independent workstreams; knows when serial dependencies prevent parallelism. |

**Red flags:**
- Reading 5 files one at a time when they could be read in parallel.
- Spawning subagents serially when they don't depend on each other.
- Doing broad research in main context instead of in an Explore subagent.

**Boost signals:**
- "Spawn 3 parallel Explore agents to look at X, Y, Z."
- Batching reads in a single message.
- Choosing subagent isolation when the work would otherwise pollute context.

---

## 5. Context & memory hygiene

What you're checking: is context being kept lean? Are useful learnings persisted?

| Score | Pattern |
|---|---|
| 1 | Loads huge files into main context unnecessarily. Never uses memory. Never compacts. |
| 2 | Aware of context but doesn't actively manage. No memory entries. |
| 3 | Uses memory occasionally. Compacts when reminded. |
| 4 | Saves useful feedback/project memories. Uses subagents to absorb research. Keeps main context focused. |
| 5 | Treats context as a budget. Active memory hygiene — adds, updates, removes entries as facts change. Uses skills' progressive disclosure (refs over inline). |

**Red flags:**
- Restating the same preference in every session because it's not in memory.
- Reading a 2000-line file into main context to answer a question about one function.
- Letting old/stale memories accumulate.

**Boost signals:**
- "Save this as a feedback memory."
- Using `Explore` to absorb research without dragging it into main context.
- Updating a memory when a fact changes rather than adding a contradictory new one.

---

## 6. Verification & ownership

What you're checking: does she check AI output, or accept polished-looking artifacts on face value? This is the most consequential dimension — the "artifact paradox" from ai-fluency research means most users *decrease* verification when AI produces clean-looking code.

| Score | Pattern |
|---|---|
| 1 | Accepts AI output as truth. Merges generated PRs without reading diffs. |
| 2 | Skims output. Catches obvious errors but doesn't probe reasoning. |
| 3 | Reads diffs before committing. Runs tests. Pushes back on visibly wrong output. |
| 4 | Reviews carefully, questions reasoning when it doesn't add up, tests edge cases, fact-checks claims that matter. |
| 5 | Treats AI output as a draft requiring human validation. Has personal review checklists. Catches subtle bugs in clean-looking code. |

**Red flags (the artifact paradox in action):**
- A polished-looking implementation with no test run.
- Accepting an architectural decision because the code compiled.
- Not pushing back when Claude's reasoning skips a step.
- Approving a PR Claude wrote without running it locally.

**Boost signals:**
- "Show me where you got X" / "why X over Y?"
- Running tests, checking diffs, inspecting actual data before approving.
- Catching a subtle issue Claude missed.

---

## 7. Iteration loop quality

What you're checking: when something's going sideways, how fast does she course-correct?

| Score | Pattern |
|---|---|
| 1 | Lets wrong directions compound for many turns. Big rework cycles. |
| 2 | Notices wrong direction eventually but only after significant work. |
| 3 | Catches wrong direction within 2-3 turns. Course-corrects clearly. |
| 4 | Catches direction issues fast. Restarts cleanly when needed. Avoids sunk-cost. |
| 5 | Catches drift in the same turn. Re-scopes mid-task when premise shifts. Comfortable saying "stop, let's restart this." |

**Red flags:**
- "Almost done — just one more fix" repeated 5x for the same task.
- Patching on top of a wrong foundation rather than restarting.
- Not noticing that Claude misunderstood the goal until 4 turns in.

**Boost signals:**
- "Stop — that's the wrong direction" within 1-2 turns of seeing it.
- "Let's restart with a brainstorm" when the original premise was off.
- Recognizing sunk-cost and bailing.
