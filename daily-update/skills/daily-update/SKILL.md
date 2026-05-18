---
name: daily-update
description: Use when Joyce wants to draft her daily standup post for #team-partnership-experience-internal. Triggers on phrases like "draft daily update", "draft my standup", "write my standup", "/daily-update", "what should I post for standup", or any morning ask for a Yesterday/Today/Blocker post. Gathers candidates from Jira (CXP), recent carrot commits/PRs, Slack activity, Monday priority post, and local Claude/Glean usage; presents candidates per section for Joyce to check off; assembles the draft in her voice; DMs it via Slackbot for final review before she posts.
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

Show all three sections at once as numbered lists. Use plain markdown — AskUserQuestion caps at 4 options and a section often has more.

```markdown
## Candidates — check off what to include

### Yesterday (Y:)
1. [jira CXP-210557] Peacock benefit suppression — landed code, testing in progress
2. [git] Costco FD VGP cutover — merged PR #790123
3. [slack] NYT prod testing
4. [claude] Investigating Peacock IC+ exclusion logic
...

### Today (T:)
1. [carryover] EI FD discount policy cutover
2. [jira CXP-210600] NYT new flyout update
3. [priority-post] Peacock World Cup readiness
...

### Blocker (B:) — usually omit
1. [slack] Waiting on Matt for Yoda backtest results
(or: "none surfaced — recommend omitting B: section")

---
Reply with which to include, e.g.:
  Y: 1,2,3   T: 1,2   B: skip
```

Wait for her response.

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

Show the assembled draft in chat first so she can see it.

### 6. Send the draft to Slackbot DM

Use `mcp__slack__slack_send_message` to post to Slackbot:

```
channel_id: USLACKBOT
text: <the assembled draft, formatted exactly as above>
```

If sending to `USLACKBOT` fails for any reason, fall back to her own user-ID DM (`channel_id: U0AK8RMGWFR`) — Slack will route it to her self-DM.

After sending, confirm in chat with a one-liner: "Draft sent to your Slackbot DM. Tweak there and post when ready."

## Things to avoid

- **Don't post directly to #team-partnership-experience-internal.** Drafts go to Joyce's Slackbot DM only — she reviews and posts manually.
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
