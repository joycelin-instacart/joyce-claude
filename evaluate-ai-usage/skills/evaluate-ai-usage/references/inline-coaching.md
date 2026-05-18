# Inline Coaching Patterns

Inline coaching = a one-sentence nudge dropped at a natural breakpoint when you notice an improvable pattern mid-session. The point is to plant the seed without derailing the current work.

This file enumerates the patterns worth flagging and the patterns *not* worth flagging. When in doubt: don't nudge. A wasted nudge erodes trust in future nudges.

---

## When to nudge

Nudge when:
1. You observe a pattern that maps to a clear rubric dimension scoring ≤ 3 (see [rubric.md](rubric.md)).
2. There's a concrete alternative she could have used (a skill, a parallelism, a verification step).
3. The pattern is *repeatable* — she'll face this situation again.
4. You're at a natural pause (end of a task chunk, before starting a new one).

Don't nudge when:
- She's mid-debug or mid-decision.
- She just got something working — let the win stand for a beat.
- The "better way" is marginal. Save nudges for ones that meaningfully shift the loop.
- You've already nudged this session. One per session max unless she invites more.
- It's a stylistic preference rather than a productivity issue.

---

## Patterns worth flagging

### Skipped a relevant skill

Symptom: she asked you to do something a skill is designed for.
Examples to flag:
- Manually wrote a PR description instead of using `/pr:create` or `/pr:describe`.
- Asked you to "review the diff" without invoking `joyce-code-review`.
- Asked you to check failing CI without using `buildkite:buildkite`.
- Asked you to find scattered code without spawning `Explore`.

Nudge form: *"btw — `[skill name]` is built for this kind of task. Worth defaulting to it next time."*

### Serial work that could be parallel

Symptom: she asked you to look at 3 things one after another, or you ran them serially when there were no dependencies.

Nudge form: *"small one — those three lookups could have run in parallel; saves a beat on bigger searches."*

### Vague prompt that wasted a turn

Symptom: she gave a prompt vague enough that you had to ask back, or you guessed wrong and had to redo.

Nudge form: *"heads up — when you say 'fix it', I'm guessing which surface you mean. A file:line ref makes the loop tighter."*

### Skipped brainstorm for ambiguous design work

Symptom: she jumped to "build it" for something where the right approach wasn't obvious, and you (or she) ended up reworking the design.

Nudge form: *"this one would have benefitted from a brainstorm pass first — would have caught [the issue] before we wrote the code."*

### Artifact paradox — accepting polished output without verification

Symptom: you produced a clean-looking diff/implementation and she's about to ship it without running tests, reading the diff carefully, or pushing back.

Nudge form: *"before you ship — worth a `bin/rspec [file]` run; clean-looking code isn't the same as correct code."*

This one is the highest-stakes nudge. Don't skip it.

### Lets a wrong direction compound

Symptom: 2-3 turns in, the work has drifted from the original intent and she hasn't called it out.

Nudge form: *"check — we've drifted from [original goal]. Worth restarting clean rather than patching from here?"*

### Repeating a preference instead of memorializing

Symptom: she's restated the same preference she's stated before ("no, I don't want X" / "I always want Y").

Nudge form: *"this is the 2nd time you've said this — want me to save it as a feedback memory so it sticks next session?"*

---

## How to phrase a nudge

Format (in order):
1. **Soft opener** ("btw —", "heads up —", "small one —", "before you ship —"). Signals this isn't blocking.
2. **Specific observation** with the concrete moment, not an abstract principle.
3. **The why** in productivity terms (faster, more learning, less rework).
4. **Optional pointer** to the skill/command/pattern that would have helped.

Anti-patterns to avoid:
- Apologetic preamble ("sorry to interrupt the flow but…") — it's coaching, not a confession.
- Stacking 3 nudges in one sentence ("you could also…and also…and also…").
- Abstract principles without a concrete moment ("you should be more disciplined about verification").
- Lecturing tone — this is a peer giving a tip, not a teacher grading.
- Re-stating the rubric ("you scored 3 on workflow discipline because…") — just give the practical move.

---

## After the nudge

- Don't expect a response. The nudge is fire-and-forget; she may acknowledge or may not.
- If she pushes back ("not relevant here because X"), update your understanding for the rest of the session — that's calibration, not an argument to relitigate.
- Don't re-nudge the same thing later in the session. Once said, said.
- If she finds the nudge useful and the pattern is repeatable, offer to save it as a feedback memory (see `Patterns worth flagging > Repeating a preference`).
