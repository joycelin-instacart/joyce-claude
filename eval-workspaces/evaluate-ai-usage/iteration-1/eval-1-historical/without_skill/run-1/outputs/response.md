# Your Claude Code usage — honest read

Quick note on scope: your most recent CC conversations in this project are from **April 20–29**, not literally "the last week." Today is May 18. So either you've moved your CC work elsewhere, or it's been ~3 weeks since you used CC on customers-backend. That's itself a data point — flagging it so you can correct me if the wrong dataset got loaded. I analyzed the 8 sessions I have.

---

## Scorecard

| Dimension | Grade | Notes |
|---|---|---|
| Prompt clarity | B | Clear intent, but minimal context up-front |
| Use of "tutor me" framing | A- | Strong, distinctive pattern — works well for you |
| Follow-through within a session | C+ | You ask great follow-ups, but often ones you could have answered yourself with one Bash command |
| Session hygiene (one task / one session) | D | Three separate sessions asking the *same question verbatim* |
| Leveraging existing context | C | You re-ask things instead of resuming |
| Verifying claims | B- | You don't really challenge Claude's answers; you take them and move on |
| Skill/tool ecosystem awareness | C | You let Claude pick skills; you're not driving the toolchain |

**Overall: B-.** You're getting value, but a meaningful chunk of your sessions are doing redundant or low-leverage work.

---

## Patterns I see across the 8 conversations

### 1. The same question, three times, three sessions
On April 21 within a ~7-hour window, you opened three separate conversations and asked, verbatim:

> "how do the PRs that modify view_domain/app/domain/express_view/layouts/express_benefit_value_props_response_backed/en_US.yml test their changes?"

(`2b512c2b`, `99ee744a`, `c056af57` — same first message, ~7 hours apart). Each one re-did the same `git log` / spec exploration from scratch. That's roughly 21 tool calls and 3 different answers to a question you'd already gotten answered. The third conversation also wasted 6 Bash calls because Claude initially `cd`'d into the wrong path before finding the file under `customers/customers-backend/`.

**Cost:** wall-clock time + you got three slightly different framings of the same answer, which probably eroded trust rather than building it.

### 2. The "tutor me" framing is genuinely good — and you use it well
Your CXP-208606, CXP-208674, and CXP-207887 sessions all opened with *"I'm working on [Jira link], could you be my tutor and teach me what I need to do?"* That's a strong prompt: it pins the scope to a ticket, signals you want explanation not just code, and gives Claude a Jira URL it can actually fetch. Keep doing this. It's distinctive and effective — most users don't do it.

### 3. The tutoring sessions degrade into "answer my dev-environment questions"
The CXP-208606 session is the clearest case. Great start, real teaching, then turns into:
- "How can I test the change?" (fair)
- "what link do I visit for manual verification?"
- "I need to run rails s to spin up http://localhost:3000 right?"
- "where (which directory) should i run dev up?"

These are environment questions Claude can't answer well without your machine context, and you can verify in seconds yourself (`cat Procfile`, ask in #eng-help, etc.). Claude spent ~12 tool calls fishing through Procfiles to half-answer them. You'd have been faster opening the file or pinging a teammate.

### 4. You don't push back when Claude is wrong or vague
In CXP-208606, Claude told you "I don't have enough context about your local dev setup to give you a definitive URL" — and then you just kept asking the same kind of question 3 more times instead of supplying the missing context (e.g., "we use `dev up` from the customers/ directory"). One sentence from you would have unblocked it.

In the bento debugging session (`36669e39`), Claude made a real mistake mid-investigation — claimed salsa and tally already used `corncob-node-checks` based on a grep that matched for other reasons, then self-corrected. Good that *Claude* caught it; you didn't visibly verify either way. If the model hadn't self-corrected, you'd have shipped an edit based on a false premise.

### 5. You don't pre-load context that you obviously have
Several sessions open with a question that names a deep file path but no working hypothesis, no "I tried X," no "here's what I think the answer is." Compare to the bento debugging session where you pasted the actual error output — that one immediately got concrete and useful because Claude had something real to work with.

### 6. Skill ecosystem: you have a lot loaded, you use almost none
You have ~150 skills available (superpowers, autopilot, ads-data, pr/*, etc.) and across 8 conversations Claude auto-invoked maybe 3–4 of them (`systematic-debugging`, `using-superpowers`, `test-driven-development`). You're not driving the toolchain — the `/superpowers:brainstorming` skill in particular would fit your "be my tutor" prompts naturally and isn't getting used. Either prune what you're not using, or start invoking deliberately.

---

## The 1–2 things that would actually move the needle

### #1: One task, one session — and resume instead of restarting
The repeated en_US.yml question is the single biggest waste in this dataset. Concretely:
- Before opening a new CC conversation, search your existing ones (`/resume` or grep your `~/.claude/projects/` jsonl files) for the same topic.
- If you legitimately want a fresh take, *say so* in the prompt ("I asked this before in another session, here's what I got — challenge it").
- For pure factual questions like "how do similar PRs test their changes," save the answer somewhere (a scratch note, a CLAUDE.md addition) so the next you doesn't ask Claude again.

This alone would cut your tool-call count meaningfully and stop generating contradictory answers.

### #2: Front-load context, and verify before moving on
Two sub-habits:
- **At the start of a tutoring session,** spend 2 sentences on what you already know and what you've tried. The bento session worked precisely because you pasted the error. The express_view questions stalled because they didn't.
- **When Claude answers something load-bearing,** make it prove it — "show me the line" or "what spec covers this?" In CXP-208606 you accepted "run dev up from customers/" without verifying it actually works in your env. That's the kind of thing that bites you 30 minutes later when the URL doesn't load and you don't know whether the answer was wrong or the env is broken.

---

## What you're doing well (don't lose these)
- Jira-link-first framing for ticketed work.
- Asking "could you be my tutor" — you're using CC as a learning tool, not just an autocomplete, and that compounds.
- You pasted real error output in the bento session. That's the right move.
- You ask follow-up questions instead of accepting one-shot answers. The instinct is right; the execution (asking things you could verify yourself) is the gap.

---

## Files referenced
- `/home/bento/.claude/projects/-home-bento-carrot/2b512c2b-0684-4785-8b32-4bc414456ef8.jsonl` — repeated en_US.yml question #1
- `/home/bento/.claude/projects/-home-bento-carrot/99ee744a-bd44-41a6-86bf-3e3937a7d144.jsonl` — repeated en_US.yml question #2
- `/home/bento/.claude/projects/-home-bento-carrot/c056af57-183a-47f8-ab62-afe82c66ccdd.jsonl` — repeated en_US.yml question #3
- `/home/bento/.claude/projects/-home-bento-carrot/6cbdf77e-a9a2-40bc-84bf-a76cddc7c290.jsonl` — CXP-208606 tutoring session (the long one)
- `/home/bento/.claude/projects/-home-bento-carrot/8457d7e8-99e0-4eca-af38-ea4121ee8b94.jsonl` — CXP-207887 tutoring session
- `/home/bento/.claude/projects/-home-bento-carrot/4837694d-7d2b-47cd-9873-3dae9e3cc499.jsonl` — CXP-208674 tutoring session
- `/home/bento/.claude/projects/-home-bento-carrot/36669e39-48f7-4f83-857d-d0dd84d0b370.jsonl` — bento debugging (best session in the set)
- `/home/bento/.claude/projects/-home-bento-carrot/c57aa90f-b767-494c-a140-aca55b67cbae.jsonl` — git pull question
