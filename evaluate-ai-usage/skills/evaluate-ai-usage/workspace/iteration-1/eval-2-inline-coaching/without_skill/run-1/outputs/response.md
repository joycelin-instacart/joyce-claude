A few tactical tweaks for next time:

1. **Batch the file reads into one turn.** "Read orchestrator.rb, service.rb, and api.rb" in a single prompt — Claude will parallelize the reads and you save round-trips. Three sequential asks is three sequential context loads.

2. **State the goal before the reads.** Instead of "look at X, then Y, then Z" then later revealing what you want, lead with the task: "I'm adding [feature] that touches these three files. Read them, then propose an approach." That way Claude reads with intent and you get a plan instead of three summaries.

3. **Ask for the plan before the code.** A quick "what's your approach?" checkpoint before implementation catches misunderstandings cheaply. Especially valuable across three files where the wrong seam choice is expensive to unwind.

4. **Write tests alongside, not after.** TDD-ish flow ("write the test for the new behavior in service.rb, then make it pass") tends to produce tighter code and catches the "works but tests the wrong thing" failure mode. Writing tests after the fact biases toward tests that confirm whatever you built.

5. **The manual diff review is good — keep it, but sharpen it.** "Review the diff" is vague. Try "review the diff for: unused code, missing error paths, anything that violates the patterns in [neighboring file]." Specific checklists beat open-ended review.

6. **PR creation is fine as a final step** — no change needed there, assuming you reviewed the PR body before it went up.

The biggest lift is #1 and #3. The sequential reads pattern is the most common token/time waste I see, and skipping the plan checkpoint is where rework comes from.
