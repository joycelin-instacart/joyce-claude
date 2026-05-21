---
name: daily-update
description: 'Use when Joyce wants to draft her daily standup post for #team-partnership-experience-internal. Triggers on phrases like "draft daily update", "draft my standup", "write my standup", "/daily-update", "what should I post for standup", or any morning ask for a Yesterday/Today/Blocker post. Gathers candidates from Jira (CXP), recent carrot commits/PRs, Slack activity, Monday priority post, and local Claude/Glean usage; presents candidates per section for Joyce to check off; assembles the draft in her voice; shows it for confirmation; then posts it as a threaded reply under the day''s Slackbot standup prompt in #team-partnership-experience-internal (falling back to a Slackbot DM if no prompt is found).'
---

# daily-update

Draft Joyce's daily standup post in her exact voice, sourcing candidates from real activity signals so she just has to check off what's relevant.

## When to invoke

Joyce types something like "draft daily update", "/daily-update", "draft my standup", "morning standup", or it's a weekday morning and she's asking what to post. The trigger is the *post she needs to write today*, not historical analysis.

## Joyce's voice — match exactly

Her format from past posts (do not deviate):

```
Y:
• <concise item>, with optional <link|description> inline
• <project name>
    ◦ <sub-bullet for specifics, e.g., specific PRs>

T:
• <concise item>
• <project name with link>
```

**Critical**: insert a **blank line** before `T:` and before `B:` if present. Without it, Slack renders the section header as a hanging-indented continuation of the previous bullet list, which looks wrong even though the raw text appears correct. Her own client may render her bullets as a proper list block (where this isn't needed), but messages sent via the API as plain text with literal `•` chars require the blank-line separator.

Style notes derived from her posts:
- **Abbreviations**: `Y:` and `T:` (not "Yesterday" / "Today"). Use `B:` only when she actually has a blocker — she usually omits it.
- **Bullets**: `•` for top-level, `◦` indented with 4 spaces for sub-bullets.
- **Links**: Slack format `<url|text>` inline within the bullet. PR titles, Jira IDs, Google doc titles, expy dashboards all get linked.
- **Tone**: short, declarative noun phrases ("NYT prod testing", "Costco FD policy cutover"). Occasional light personality (":dancingpenguin:", parenthetical "please try it out!"). No corporate-speak. No "completed", "finalized" filler.
- **No bold, no headers**, no preamble like "Here is my update:".
- **Project naming**: she uses short proper-noun project names (NYT, Peacock, Costco FD, GH+ FD) — keep them.

## The workflow

### 1. Determine the date window

"Yesterday" = **previous working day** (skip weekends). Today is the current date.

```bash
date +%Y-%m-%d  # today
```

If today is Monday, yesterday = previous Friday. Otherwise yesterday = literal previous day. Compute both in `YYYY-MM-DD` and as Slack epoch timestamps (start-of-day + end-of-day in `America/New_York`, Joyce's TZ) for source queries.

### 2. Gather candidates in parallel

Spawn the source-gathering steps in parallel — they're independent and most are slow (Slack API, Glean, git log). Run them as parallel tool calls in one message.

#### 2a. Yesterday candidates

Pull from these sources:

**Jira (CXP project)** — tickets where Joyce was the assignee that transitioned to Done/Resolved yesterday. Use Glean:
```
mcp__glean__search with query like:
  "project:CXP assignee:joyce.lin status:Done updated:<yesterday>"
```
If Glean returns nothing useful, fall back to: `mcp__glean__search` with `joyce.lin CXP <yesterday-date>` and filter for Jira datasource.

**Carrot commits/PRs** — Joyce's authored or merged commits in the carrot monorepo:
```bash
cd /home/bento/carrot && git log --author="Joyce Lin" --since="<yesterday>" --until="<today>" --oneline
```
Plus PRs she merged yesterday via `gh pr list --author "@me" --state merged --search "merged:<yesterday>"` (run from /home/bento/carrot).

**Slack activity** — her own posts yesterday in #team-partnership-experience-internal and adjacent project channels, which surface the things she was actively pushing on:
```
mcp__slack__slack_search_public_and_private:
  query: "from:<@U0AK8RMGWFR>"
  after: <yesterday-00:00 epoch>
  before: <yesterday-23:59 epoch>
  limit: 20
```

**Claude Code transcripts** — the prompts she was typing yesterday, which signal what she was actively investigating:
```bash
ls ~/.claude/projects/-home-bento-carrot-customers-customers-backend/*.jsonl
# Find jsonl files modified yesterday, extract user prompts
```
Cluster topically — don't list every prompt, group by intent (e.g., "investigating Peacock benefit suppression" rather than every individual question).

**Glean (recent activity)** — supplement with Glean's recent-activity feed for Joyce yesterday:
```
mcp__glean__search:
  query: "joyce.lin yesterday"
  with appropriate filters
```

#### 2b. Today candidates

**In-progress CXP tickets** — open tickets assigned to Joyce that aren't Done:
```
mcp__glean__search:
  query: "project:CXP assignee:joyce.lin status:'In Progress' OR status:'To Do'"
```

**Monday's priority post** — find the most recent Monday post in #team-partnership-experience-internal where Joyce (or her manager Rob/Richard) laid out the week's priorities. Search the channel for messages from the prior Monday containing words like "priority", "this week", "focus":
```
mcp__slack__slack_read_channel:
  channel_id: C0880QWQ5K3
  oldest: <prior-monday-00:00 epoch>
  latest: <prior-monday-23:59 epoch>
```
Then look for posts from Joyce or "this week"/"priorities" content. If no clear priority post exists, skip this source and note it.

**Yesterday's "T:" carryover** — read her own most recent standup post in the channel and extract any "T:" items she may not have finished:
```
mcp__slack__slack_search_public_and_private:
  query: "from:<@U0AK8RMGWFR> in:#team-partnership-experience-internal"
  limit: 5
  sort: timestamp, sort_dir: desc
```
The most recent post starting with `Y:` is her last standup. Items she listed under `T:` are strong candidates for today.

**Open Slack threads** — threads where she's been @-mentioned and hasn't responded, or threads she started that are awaiting her follow-up.

**Recent Claude/Glean topics** — same sources as yesterday but filter for in-flight work (things she was mid-investigation on).

#### 2c. Blocker candidates

**Her own Slack signals** — search yesterday's messages from her for "blocked", "waiting on", "stuck on", "pending":
```
mcp__slack__slack_search_public_and_private:
  query: "from:<@U0AK8RMGWFR> (blocked OR waiting OR pending OR stuck)"
  after: <last-3-days-epoch>
```

**Jira Blocked status** — any CXP tickets in Blocked status assigned to her.

If nothing surfaces, **default to no Blocker section** — she usually omits it.

### 3. De-dupe and normalize

The same item often surfaces from multiple sources (e.g., a PR shows up in git log AND in her Slack messages). De-dupe by topic. Prefer the version with a useful link (PR URL, Jira link, doc link, Datadog dashboard). Rewrite each candidate in her short noun-phrase style — do not paste raw commit messages or Jira ticket titles verbatim.

For each candidate, capture:
- Short label (1 line, her voice)
- Source (so she knows where you got it)
- Optional link in Slack format `<url|text>`

### 4. Present candidates for selection

Use `AskUserQuestion` with `multiSelect: true` so Joyce can tick checkboxes instead of typing back numbers. AskUserQuestion caps each question at 4 options, so split each section into multiple questions when it has more than 4 candidates. Send all the questions in a single AskUserQuestion call so they appear together. (If the total number of questions across all sections would exceed AskUserQuestion's per-call cap of 4, split across two AskUserQuestion calls — Y first, then T+B.)

**Per-section layout:**
- Y candidates 1–4 → question with `header: "Yesterday"`
- Y candidates 5–8 → question with `header: "Yesterday (cont.)"` — only if she has >4 candidates
- T candidates 1–4 → question with `header: "Today"`
- T candidates 5–8 → question with `header: "Today (cont.)"` — only if needed
- B section: only ask if ≥1 blocker candidate surfaced. Otherwise omit the question entirely — matches her habit of dropping B: when there's nothing.

**Each option:**
- `label`: the candidate phrased in Joyce's voice — short noun phrase, the way it would read in the final bullet (e.g., `"NYT outbound flyout new design"`).
- `description`: source tag + the link/context she needs to judge it (e.g., `"[git+PR 792206] CXP-211002 — merged + cleanup commits under terms variant"`). This shows under the option in the UI and never makes it into the post.

**'Other' free-text is auto-added** by AskUserQuestion. That's how she adds anything missed — no separate prompt needed. Treat any non-empty 'Other' response as an additional selected item for that section, and rewrite it into her short noun-phrase style if she gave it verbosely.

**Edge case — fewer than 2 real candidates for a section:** AskUserQuestion requires a minimum of 2 options per question. If only 1 candidate surfaced for Y or T, add a literal `"None of these / I'll add via Other"` as the second option so she can still type an addition via 'Other'. If 0 candidates surfaced for Y or T, skip the structured question and ask her in plain text what to put there — having zero signals is itself worth flagging.

**Example call shape** (Y has 6 candidates, T has 3, B omitted):
```
AskUserQuestion(questions: [
  {
    question: "Yesterday (Y:) — pick what to include",
    header: "Yesterday",
    multiSelect: true,
    options: [
      { label: "NYT outbound flyout new design", description: "[git+PR 792206] CXP-211002 — merged + follow-up cleanup commits" },
      { label: "Peacock IC+ benefit suppression testing", description: "[CXP-210557, PR 791828] landed Thu, tested Fri" },
      { label: "Mandatory Snowflake Continu training", description: "[slack] mentioned in Friday's Y:" },
      { label: "Peacock World Cup workstreams discussion w/ Rob", description: "[slack-thread] CRM suppression + payment-gating direction" }
    ]
  },
  {
    question: "Yesterday (cont.) — anything else?",
    header: "Yesterday (cont.)",
    multiSelect: true,
    options: [
      { label: "NYT modal images uploaded", description: "[weekend PRs 792812, 792815]" },
      { label: "Peacock payment-method-required gate started", description: "[weekend PR 792845, CXP-211150]" }
    ]
  },
  {
    question: "Today (T:) — pick what to include",
    header: "Today",
    multiSelect: true,
    options: [
      { label: "Land Peacock payment-method-required gate", description: "[CXP-211150, PR 792845]" },
      { label: "Get NYT modal image PRs merged", description: "[PRs 792812, 792815]" },
      { label: "NYT EPP storefront banner placements", description: "[PR 791195]" }
    ]
  }
])
```

Wait for her checkbox response before assembling the draft. Selected option labels + any 'Other' text become the items for that section in step 5.

### 5. Assemble the draft in her voice

Build the post using the selected items. Strict formatting:

```
Y:
• <item 1>
• <item 2 with <link|description>>
    ◦ <sub-bullet if multi-part>
T:
• <item 1>
• <item 2>
B:    ← only include this section if she selected blockers
• <blocker>
```

**Order bullets within each section by priority — most important first.** Do not preserve the AskUserQuestion option order (that's discovery order from git/Slack/Jira, not importance order). Rough heuristics:
- `Y:` — shipped/landed work first, then in-progress/iteration, then small one-offs
- `T:` — must-do today first, then follow-ups, then nice-to-haves
- `B:` — most blocking first

If the priority isn't obvious from the candidates, ask her to confirm ordering when showing the draft ("ordered by priority — want to reshuffle?"). She'll often reorder herself if it's wrong.

Show the assembled draft in chat first so she can see it. **Do not send anything yet** — wait for an explicit go-ahead in step 6.

### 6. Confirm, then post as a threaded reply to today's Slackbot standup prompt

Posting goes to a public channel, so the draft must be confirmed before it sends.

**6a. Get confirmation.** After showing the draft, ask in plain text: "Post this as a reply in the standup thread?" Wait for an affirmative response ("yes", "send it", "looks good", "ship it", etc.). If Joyce asks for edits, revise the draft inline and ask again. Do **not** proceed to 6b without a clear go-ahead.

**6b. Find today's Slackbot standup prompt.** Read recent messages from #team-partnership-experience-internal posted today (Joyce's TZ, `America/New_York`):

```
mcp__slack__slack_read_channel:
  channel_id: C0880QWQ5K3
  oldest: <today-00:00 epoch in America/New_York>
  latest: <now epoch>
```

From the returned messages, pick the most recent top-level post (no `thread_ts`, or `thread_ts == ts`) that came from Slackbot — typically `user == "USLACKBOT"` or `subtype == "bot_message"` with Slackbot as the author — whose text looks like a standup prompt (mentions "standup", "update", "Y:/T:", or similar). The `ts` of that message is the thread root.

**6c. Post the reply.**

```
mcp__slack__slack_send_message:
  channel_id: C0880QWQ5K3
  thread_ts: <the standup post ts>
  message: <the assembled draft, formatted exactly as in step 5>
```

After posting, confirm in chat with a one-liner: "Posted in the standup thread."

**6d. Fallback — no Slackbot standup prompt found today.** If 6b returns no qualifying Slackbot post (weekend, holiday, bot didn't fire yet, etc.), do **not** post a top-level message in the channel. Send the draft to Joyce's Slackbot DM so she can post manually:

```
mcp__slack__slack_send_message:
  channel_id: USLACKBOT
  message: <the assembled draft>
```

If `USLACKBOT` fails, fall back to her self-DM (`channel_id: U0AK8RMGWFR`). Then confirm in chat: "No standup prompt found in #team-partnership-experience-internal today — sent the draft to your Slackbot DM instead so you can post when ready."

## Things to avoid

- **Don't post without explicit confirmation.** Show the assembled draft in chat (step 5), ask, and wait for a clear go-ahead before sending anything. Posting to a public channel is one-way — no undo.
- **Don't post the draft as a top-level message in #team-partnership-experience-internal.** Always reply in-thread under that day's Slackbot standup prompt. If no Slackbot prompt is found for today, fall back to her Slackbot DM — never post to the channel root.
- **Don't invent items.** Every candidate must trace to a real source (Jira, commit, Slack message, Claude transcript). If a source is empty, say so — don't pad.
- **Don't include B: when there's nothing.** Match her actual habit of omitting it.
- **Don't expand bullets with prose.** "Verified FD still works in Grubhub" not "Yesterday, I performed verification testing on the Free Delivery feature in the Grubhub integration to confirm continued functionality."
- **Don't strip links.** PR/Jira/doc/dashboard links in Slack `<url|text>` format are load-bearing — they're how Rob/Richard skim the update.
- **Don't reformat to "Yesterday/Today/Blocker".** She uses `Y:` `T:` `B:`. Match it.

## Hardcoded identifiers (Joyce-specific)

- Joyce's Slack user ID: `U0AK8RMGWFR`
- Channel #team-partnership-experience-internal: `C0880QWQ5K3`
- Slackbot DM channel: `USLACKBOT`
- Jira project: `CXP`
- Carrot working directory: `/home/bento/carrot` (subproject usually `customers/customers-backend`)
- Local Claude transcripts: `~/.claude/projects/-home-bento-carrot-customers-customers-backend/*.jsonl`
- Joyce's timezone: `America/New_York`
