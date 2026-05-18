Three tactical moves, in order of leverage:

1. **Read the three files in parallel, not serial.** `orchestrator.rb`, `service.rb`, `api.rb` had no dependencies on each other — one message with three Read calls returns in roughly the time of one. Three sequential prompts is three round-trips of you waiting, reading, prompting again. This is the highest-frequency win because you'll do multi-file orientation constantly. Same applies to broad searches: reach for `Explore` (or parallel subagents) when the lookups are independent.

2. **`/pr:review` (or `joyce-code-review`) instead of manual diff review.** Manual eyeballing is the artifact-paradox trap — clean-looking diffs read as correct even when they're not. The skill applies a checklist you wouldn't apply by hand and catches the subtle stuff (untested branches, missed edge cases, layer violations from your AGENTS.md). Use it before the PR step, not after.

3. **`/pr:create` collapses the last two steps.** It runs review-style checks and opens the PR in one move, so "review the diff manually, then make a PR" becomes one invocation. Smaller thing than the first two but it's free throughput.

One thing to internalize: **before you send the next prompt, ask "is this serial because it has to be, or because I'm typing them one at a time?"** Done ten times, that single habit shifts your whole loop.

If "read N independent files in parallel" or "default to `/pr:review` before manual diff review" are patterns you want to lock in, say the word and I'll save them as feedback memories.
