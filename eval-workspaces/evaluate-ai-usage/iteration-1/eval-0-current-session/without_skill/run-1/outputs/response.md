# Review of your Claude Code session

Here's what stood out, ordered roughly by impact.

## 1. Front-load context instead of drip-feeding it

Your first three messages were "add validation" → "to the signup form" → "yes". That's three round trips to get to the point where Claude could start working. Each round trip costs you wall-clock time and burns tokens on clarification instead of execution.

A single opening prompt like this would have skipped straight to the implementation:

> Add email format validation to `SignupForm`. Follow the same pattern as the existing `PasswordValidator`. Write tests.

Rule of thumb: before you hit enter, ask yourself "could Claude actually start working from this, or will it have to ask me something?" If the answer is "it'll have to ask," add the missing piece now.

This is the single highest-leverage change you can make. Vague prompts feel faster because they're shorter to type, but they're almost always slower end-to-end.

## 2. Bundle related questions into one prompt

Message 4 ("also check if the user model needs the same") is a good instinct — you're thinking about consistency across related code. But it should have been part of message 1, not a follow-up.

Better opener:

> Add email format validation to `SignupForm` matching the existing `PasswordValidator` pattern. Also check whether `User` needs the same validation and add it there if missing. Write tests for any changes.

This lets Claude plan the whole unit of work, batch the file reads, and give you a single coherent answer instead of two sequential ones.

## 3. Use slash commands for routine workflows

Message 5 was "make a PR for it" and Claude hand-rolled the whole thing — wrote a description from scratch, ran git commands one at a time, called `gh` manually. Your environment has skills built for exactly this:

- `/create-pr` — commits current changes and opens a PR in one step
- `/commit-and-push` — review, commit with a conventional message, push
- `pr:create`, `pr:describe` — PR creation helpers

Any of those would have been faster, more consistent with your team's conventions, and would have generated a better PR description than a one-shot. If you find yourself describing a routine workflow in prose, check whether there's a skill for it first.

## 4. Consider whether the work itself needed scoping

You asked Claude to add validation and it did exactly that, but neither of you stopped to ask: what kind of email validation? Format only (regex)? MX record check? Disposable-email blocking? Uniqueness (probably already handled at the DB level, but worth confirming)? Should invalid input surface as a form error, an exception, or a soft warning?

For a small change matching an existing pattern this is probably fine — "do what `PasswordValidator` does" is a reasonable scope. But notice that you didn't define "done" up front, you let the implementation define it. That's a habit worth watching, because it scales badly: the bigger the task, the more important it is to agree on the shape of the solution before code gets written. For larger features, lean on `superpowers:brainstorming` to pin down requirements before implementation.

## 5. Small wins to keep doing

- Message 4 ("check if the user model needs the same") shows good systems thinking — you're considering blast radius beyond the immediate ask. Keep that.
- You verified completion rather than assuming (tests passed, then moved on). Good.
- You said thanks at the end. Doesn't matter to Claude, but it's a nice habit.

## What to practice next

Pick one prompt this week and force yourself to write the "full" version before sending it. Include: the file or area, the desired behavior, the pattern to follow, related surfaces to check, and what "done" looks like (tests, PR, etc.). Time how long it takes vs. your usual back-and-forth. I'd bet the upfront version finishes faster overall and produces a cleaner result.

Then: next time you reach for `gh` or `git` manually, stop and check your skills list first.
