---
name: ddc-remediation-data
description: "Gathers the data an engineer needs to remediate a partnerships DDC (Declarative Data Check) failure: fetches the check config, locates the runbook (go/ links, Confluence, Glean, CXP-* ticket naming the failing check), and pulls runbook-requested data in parallel from Blazer, Snowflake, WittyCart, and Datadog. Flags @fernet.io test-user noise, calls out gaps when a runbook/step/data-source is missing, and surfaces Datadog traces as next steps. Does not propose code fixes. Use when: a DDC failure lands in #bot-hackers-partnerships, a Mastercard/BMO/Chase/partnership check fails, the user pastes a ddc.instacart.tools URL or a run UUID, or asks 'what do I need to fix this DDC' / 'gather data for this DDC' / 'help me remediate this check'."
---

# ddc-remediation-data

Gathers data needed to remediate a partnerships DDC failure. **Does not propose code fixes or perform mutations** — its job is to put every piece of data the runbook asks for on one screen, plus flag the things it can't get. The engineer makes the call.

## When this skill fires vs. sibling skills

This skill is the **remediation data prep** layer. It is not:

- `debug-ddc-failure` (icplus-core): root-causes IC+ checks from a Slack thread. Use that one for IC+ membership checks where you want a root-cause hypothesis, not a remediation prep packet.
- `ddc-investigate` (commerce-accountability): classifies Commerce Accountability `assert_*` checks (REGRESSION / CHRONIC / etc.). Use that for Commerce Platform checks.
- `oncall-triage` (partnership-experience): the alert picker for #bot-hackers-partnerships. Use that to *find* a hot alert; use this skill once you've picked one and decided "I'm going to remediate it."

If you're not sure whether the user wants root-causing, classification, or remediation data — ask before running. Don't fan out a bunch of subagents on the wrong frame.

## Inputs the user might give you

Accept any of:

1. **DDC details URL** — `https://ddc.instacart.tools/details/<run_uuid>`. Extract `<run_uuid>` from the path.
2. **Bare run UUID** — pass straight through.
3. **Slack thread URL** from #bot-hackers-partnerships — `https://instacart.slack.com/archives/C08R8NR00Q3/p<ts>`. Pull the thread via the Slack MCP, find the DDC link in the alert attachment's `title_link` or in message text, extract the UUID.
4. **Check URI** — `git+ddc://github.com/instacart/carrot/...check_X.yml`. Use `mcp__ddc-mcp__list_runs` to get the latest failed run UUID.

If the user gives you something else (an OpsGenie alert URL with no DDC link, a screenshot, a vague description), ask for one of the above. Don't guess a UUID.

## Workflow

### Step 1 — Fetch run details

Call `mcp__ddc-mcp__get_run_details` with the run UUID. This single call gives you everything you need to set up the rest of the workflow:

- `config.name` / `config.uri` / `config.owner.name` — the check identity
- `config.ddcMetadata.githubLinks.view` — link to the YAML in carrot
- `details.description` — the check's prose description (this is where runbook links usually live)
- `details.sqlQuery` — the full SQL query (use this to understand what the failure rows actually mean)
- `data.results` — the failure rows, each a JSON string. Parse them.
- `data.rowsWritten` — how many rows failed total (the `results` array may be truncated)
- `metadata.temporal.logsUrl` — the WittyCart logs URL pre-filtered to this run's workflow

If the run status is `success`, stop and tell the user the check isn't actually failing right now (and link to `mcp__ddc-mcp__list_runs` to find a recent failed run).

### Step 2 — Identify the runbook (+ active investigation ticket)

Two paths, in order:

**Path A: Remediation steps already provided.** If the user's prompt includes inline remediation steps (a runbook quote, a numbered list, a "do X then Y"), use those. Skip to Step 3.

**Path B: Find the runbook.** Fire these searches in parallel (single message, multiple tool calls), then merge — don't sequence them:

1. **`go/` links in `details.description`.** Scan the description for `go/<slug>` patterns. These resolve via `https://go.instacart.tools/<slug>`. Fetch each with `WebFetch`. If the response is itself a Confluence page, follow through.
2. **Confluence search** via `mcp__atlassian__searchConfluenceUsingCql`. CQL like `title ~ "<check name>" AND type = page`, or `text ~ "<distinctive phrase from check description>" AND space = "<partnerships space if known>"`.
3. **Glean search** via `mcp__glean__search` with the check name as a short keyword query. Use `app: "confluence"` filter if it helps.
4. **Carrot repo, alongside the YAML.** Check for sibling `RUNBOOK.md` or `README.md` files using `Glob` near `customers/ddc_checks/checks/partnerships/`.
5. **Active investigation ticket as de-facto runbook.** In partnerships, the curated handoff doc usually covers campaigns/dashboards/segments but *not* per-check remediation — the operating runbook for a recurring failure often lives in the open investigation ticket. Search Jira and Glean for the check name and any related identifier:
   - `mcp__atlassian__searchJiraIssuesUsingJql` with JQL like `text ~ "<check_name>" AND project = CXP AND statusCategory != Done ORDER BY updated DESC`.
   - `mcp__glean__search` for the bare check name and for `[DDC: <check_name>]`.

   **Strong-match rule (required to cite as a runbook supplement).** Only promote a ticket into the canonical Runbook section if at least one of these holds:
   - The ticket title or description names the failing check by exact name (e.g., `check_partnership_redemptions_missing_coupons`).
   - The ticket references the failing **run UUID** or a specific recent failing-row identifier.
   - The ticket names the same `partnership_benefit_id`, `partnership_id`, or partnership-account identifier that's in the failure rows, *and* the failure signature in the ticket matches the current run's (same SQL clause, same error mode).

   When a strong match is found, treat the ticket description + most recent investigation comment as a runbook supplement. Cite it alongside any doc-based runbook in Step 5 — the comment thread usually contains the actual hypotheses and diagnostic queries the on-call engineer is working through (Datadog trace queries, time-window theories, suspected upstream services).

   **Weak match → optional context, not Runbook.** If the only link is product-area overlap (e.g., "this is also a Mastercard ticket") with no exact check-name / run-UUID / identifier match, do *not* put the ticket in the Runbook section. Instead, list it under a separate "Related open tickets (unverified)" bullet in Gaps so the engineer can decide whether to pull it in — partnerships often has multiple active CXP investigations in the same area, and importing the wrong hypothesis or Datadog query misleads triage.

**Merging results:** if both a handoff doc and an active ticket are found, present *both* — the doc gives general context, the ticket gives the actual investigation steps the on-call engineer is currently working through. Don't pick one over the other.

**If you find nothing**, flag this explicitly in the output (see "Gaps" in Step 5) and stop trying to invent steps. Don't make up remediation logic from the SQL query alone — that's a job for `debug-ddc-failure` or the engineer's brain, not this skill.

### Step 3 — Isolate the data the runbook asks for

Read the runbook carefully. Write down, as a literal list, every distinct piece of data the runbook tells the engineer to gather before acting. Examples:

- "Check the campaign's `treatment_offer_id` for partnership_benefit_id X" → one data item
- "Verify the user's coupon was issued this month" → one data item
- "Look at the WittyCart logs for the redemption workflow" → one data item

For each item, identify which source serves it (Blazer / Snowflake / WittyCart / Datadog / Rails console / Roulette / etc.). If a runbook step is ambiguous about *which* source or *which* query, that's a gap — list it as "unclear" rather than guessing.

**Snowflake-only tables are not locally verifiable.** If the check's SQL query (or a runbook step) references a table under `instadata.rds_data.*`, `instadata.eda.*`, or any other Snowflake-only namespace (you can confirm by trying `mcp__blazer__blazer_get_schema` and getting "table not found"), don't try to query it from Blazer. Note the dependency in the report as "trusts check evaluator's own join against `<table>` (Snowflake-only, not queryable from current tooling)" and move on. Common Snowflake-only tables in partnerships checks: `user_common_identities`, `instadata.eda.*` event streams.

**Datadog traces from runbook steps.** If the runbook (or active investigation ticket from Step 2) tells the engineer to "trace `<MutationName>` in Datadog" or "look at spans for `@user_id:<id>`", surface that as a recommended next step in the Gaps section — pre-fill the query with the specific user_ids from the failure rows so the engineer can click through. Don't try to execute the Datadog query yourself unless the user explicitly asks; it's expensive and the engineer is usually the right person to interpret the trace.

### Step 4 — Fan out parallel gathers

Two kinds of gather always happen.

**4a. User-ID admin/test check (always).** If any failure row has a `user_id` (or `USER_ID` — be tolerant of case), batch-look up emails via Blazer:

```sql
SELECT id, email FROM users WHERE id IN (<comma-separated user_ids>);
```

Use `mcp__blazer__blazer_run_query` against the main data source (`mcp__blazer__blazer_list_data_sources` if you need to discover the source name first; the default for partnerships work is the customers DB).

Flag any user whose email ends in `@fernet.io` as **TEST USER** in the output. These are admin/test accounts and a failure row that's entirely TEST USERs is usually noise that doesn't need real remediation. Don't drop them silently — present them, just tagged.

Don't flag a user as suspicious based on `user_id` digit count alone — IC has a wide range of legitimate ID shapes (8-digit legacy, 17-digit modern). The only authoritative signal is the email lookup.

**4b. Runbook data items.** How you fan out depends on how many items you have:

- **≤4 distinct data items, or items all in the same data source (e.g., all Blazer queries):** fire each query directly from this conversation in a single message — multiple `mcp__blazer__blazer_run_query` calls (and any other MCP queries) in one batch. This is faster than spawning subagents and avoids any subagent-tooling friction. Most partnerships checks fall in this bucket.

- **>4 distinct data items, OR items that need multi-step exploration per item (browse schemas, follow joins, read logs), OR items in sources where each query is itself noisy:** spawn one subagent per data item using the `Agent` tool with `subagent_type: general-purpose` to keep the noise out of the main context. Fan them out in parallel — single message with multiple `Agent` tool calls.

When you spawn subagents, each prompt should:

- Name the exact data item being gathered ("the active treatment_offer_id for partnership_benefit_id 108")
- Name the exact source and query/command to run
- Specify the output format you want back (e.g., "return a markdown table with these columns, no prose")
- Have a clear "if you can't get this, say so explicitly with the reason" clause
- End with: **"Return your findings as the final text of your response. Do not use the Write tool to save a file — the environment blocks subagent file writes."** Without this clause, subagents often default to writing a report file, which fails silently and you'll get back a confused agent.

If a data item's source isn't accessible from your current environment (no Snowflake MCP, no WittyCart MCP), don't silently fail. Have the subagent return "source unavailable: <reason>" — or, if you're querying inline, just note the unavailability — and treat it as a gap in Step 5.

### Step 5 — Synthesize the report

Output an inline markdown report with these sections, in this order. Keep it tight — the engineer wants to triage in under a minute.

```markdown
## DDC Remediation Data: <check name>

**Check:** [<check name>](<github view link>)
**Owner:** <config.owner.name>
**Run:** [<run uuid prefix>](https://ddc.instacart.tools/details/<run uuid>) — failed at <endedAt>
**Rows failing:** <data.rowsWritten> (showing <N> here)
**Logs:** [WittyCart](<metadata.temporal.logsUrl>)

## Runbook

<one of:>
- Source: <go/ link or Confluence URL>
- Summary: <2-4 bullet list of the steps the runbook prescribes>
<AND, only when a strong match is found per Step 2 rule (exact check name, run UUID, or partnership identifier + matching failure signature):>
- **Active investigation:** <CXP-ticket-link> — <one-line summary of the current investigation hypothesis or status>
<OR if no runbook found:>
- **GAP**: No runbook found. Searched: go/ links in description, Confluence CQL, Glean, open Jira tickets for `[DDC: <check_name>]`. Suggest filing one; in the meantime the check's SQL query is at <github link> for context.

## User accounts

<table: user_id | email | flag>
<Each row tagged TEST USER if email ends in @fernet.io, otherwise blank>
<Summary line: "X of Y rows are TEST USERs — likely noise" or "All rows are real users.">

## Data gathered

### <Data item 1 name>
<the gathered data — table, code block, or short prose>

### <Data item 2 name>
<...>

## Gaps & engineer next steps

<bulleted list of:>
- Runbook step "<quote>" was unclear about <what>
- Source <X> was unavailable: <why>
- Data item <Y> returned no rows — runbook implies this is unexpected
- **Engineer next step:** trace `<MutationName> @user_id:<id>` in Datadog (runbook step N) — prefilled query: <link or query string>
- **Related open tickets (unverified):** <CXP-ticket-link> — same product area but no exact check-name / run-UUID / identifier match; engineer to confirm whether hypothesis applies before importing.
<If no gaps and no next steps: "None — runbook fully covered, no further investigation suggested.">
```

Order of sections matters: **User accounts before Data gathered**, because if everything is TEST USERs the engineer might not need to read further.

## Important guardrails

- **Don't propose fixes.** This skill stops at presenting data. If the engineer asks "so what should I do?", point them to `debug-ddc-failure` or the runbook author, or offer to think through it as a separate non-skill conversation. Mixing remediation execution into this skill is what we explicitly decided against.
- **Don't invent runbook steps.** If you can't find a runbook, say so. Don't write your own from the SQL — that's where wrong remediations come from.
- **Don't drop TEST USERs.** Always show them, tagged. An engineer might still need to know they're there.
- **Don't batch up failure rows past what's useful.** If `data.results` shows 16 sample rows, show all 16 in the user-accounts table. If `rowsWritten` is in the thousands, note the discrepancy and pick a representative sample (say, 20 random) for the user-accounts lookup; mention the sampling.
- **Don't sequence parallel work.** The runbook searches in Step 2 (go/links + Confluence + Glean + Jira), and the gathers in Step 4 (user-email lookup + each data item), have no dependency on each other within their step. Fire them in the same turn. Sequencing them is the single biggest source of wasted wall-clock in this skill.
- **Prefer inline tool calls over subagents for small fan-outs.** If you have ≤4 data items and they're all single-query lookups, run them inline. Subagents add ~5-15 seconds of overhead per invocation and have stricter tool constraints (the file-write block being the most common bite); they're worth it only when each item needs multi-step exploration or when you want to keep noisy output out of the main context.

## Reference files

| File | When to read |
|---|---|
| `references/sources.md` | Quick lookup of which data source serves which kind of data (Blazer schemas, Snowflake table names common to partnerships checks, WittyCart query patterns). Read before Step 4 if you're not sure where a runbook item lives. |
| `references/runbook-discovery.md` | Detailed patterns for resolving `go/` links, Confluence space hints for partnerships, and how to recognize a "runbook" page vs. a generic doc. Read in Step 2 if your first search came up empty. |
