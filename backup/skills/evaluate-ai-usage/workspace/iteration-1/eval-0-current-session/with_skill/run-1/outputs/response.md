## AI Usage Review — current session (6 messages)

| Dimension | Score | Note |
|---|---|---|
| Prompt clarity & context | 2/5 | Msgs 1 & 2: "add validation" → "to the signup form" burned two turns before Claude had enough to act. A single prompt like *"add email format validation to `app/forms/signup_form.rb`, mirror the existing PasswordValidator pattern"* would have collapsed three turns into one. |
| Tool & skill selection | 2/5 | Msg 5: "make a PR for it" — Claude hand-rolled the description and ran git commands one at a time. `/pr:create` (or `/create-pr`) is built exactly for this and would have produced a better description with less ceremony. |
| Workflow discipline | 3/5 | Scope was small enough that skipping brainstorm/plan was fine. But "Done. Tests pass." in msg 3 went unverified by you — that's the discipline gap. |
| Parallelism & delegation | 3/5 | Nothing obvious to parallelize here — the work was genuinely sequential (read form → write validator → write tests → check user model). No points off. |
| Context & memory hygiene | 3/5 | Neutral. Nothing worth memorializing surfaced; nothing was bloated. |
| Verification & ownership | 2/5 | Msg 6: "thx" — you shipped without reading the diff, re-running the tests yourself, or asking *why* Claude chose that validator shape. Classic artifact paradox: clean-sounding "tests pass" became a substitute for looking. |
| Iteration loop quality | 3/5 | Msg 4 was a good scope-expansion instinct ("check the user model too"). No drift, no compounding wrong direction. |

**Overall: 2.6 / 5 — Directed**

### What you did well
- Msg 4 — proactively asking whether the user model needed the same change. That's the kind of "is this pattern repeated elsewhere?" instinct that catches drift. Keep it.

### Top 3 next moves (highest leverage)

1. **Front-load the prompt — file path + pattern to mirror + scope in one shot.** This is the highest-leverage change here because it shifts *throughput* (fewer turns), *learning* (you have to think through what you actually want before typing), and *verification* (a specific prompt makes it obvious when the output doesn't match). Example: msgs 1+2+3 collapse into *"Add email format validation to `app/forms/signup_form.rb`. Follow the PasswordValidator pattern. Add specs alongside the existing ones. Also check whether `User` needs the same — if it already has it, just confirm."* One message, no guessing, scope-bounded.

2. **Reach for `/pr:create` (or `/create-pr`) the instant you say "make a PR."** Throughput win — it's faster, it produces a structured description, and it handles the git ceremony. Manual PR creation in msg 5 was Claude doing skill-work by hand. The rule: if you said the word "PR", the skill should fire.

3. **Don't let "tests pass" be the verification step — you run them, or you read the diff.** This is the verification dimension and it's the highest-stakes one. In msg 3, Claude said tests pass and you moved on. In a 6-message session about a validator that's probably fine, but the *habit* of trusting the artifact is what causes real bugs to ship in larger sessions. At minimum: ask *"show me the diff"* or *"what edge cases did the specs cover?"* before "thx".

### One thing to internalize this week
Before you hit enter on a prompt under 10 words, ask yourself: *"could Claude act on this without guessing?"* — if no, add the file path and the precedent to mirror. That single habit fixes most of what's in this transcript.
