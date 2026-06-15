# Finding the runbook

Partnerships DDC checks usually link their runbook from the check's `description` field. Sometimes they don't. This file is the playbook for the "sometimes they don't" case.

## Pattern 1 — `go/<slug>-runbook` in the description

The most common pattern. Example from `check_partnership_redemptions_missing_coupons`:

> "...See go/bmo-ddc-runbook and go/mastercard-ddc-runbook"

Resolve via `WebFetch` against `https://go.instacart.tools/<slug>`. The `go/` shortlinker redirects to the canonical URL — usually a Confluence page, sometimes a Google Doc, occasionally a GitHub link.

If `WebFetch` returns auth-protected content, the redirect target tells you which MCP to use next:
- Redirect to `*.atlassian.net` or `instacart.atlassian.net` → use the Atlassian MCP (`mcp__atlassian__getConfluencePage`) with the page ID from the URL.
- Redirect to `docs.google.com` → use `mcp__google-docs__readDocument` if available.
- Redirect to `github.com` → use `mcp__github__get_file_contents`.

## Pattern 2 — Confluence search

When the description has no `go/` link, search Confluence with CQL. Useful queries:

```text
title ~ "<check name without prefix>" AND type = page
text ~ "<distinctive phrase from the check description>" AND type = page
title ~ "runbook" AND text ~ "<partnership name>" AND type = page
```

Partnerships team's Confluence space is `EGP` (Express, Growth, Partnerships) — try scoping with `space = EGP` if you get too many false positives.

Use `mcp__atlassian__searchConfluenceUsingCql`. If you don't know the `cloudId`, call `mcp__atlassian__getAccessibleAtlassianResources` first.

## Pattern 3 — Glean

Last resort. Use a short keyword query (no boolean logic):

```text
mcp__glean__search query="<partnership name> ddc runbook" num_results=5
```

Filter to `app: "confluence"` if the results are noisy. Don't use full sentences — Glean's keyword matcher does worse with them.

## Pattern 4 — Sibling RUNBOOK.md in the carrot repo

Some teams keep runbooks alongside their checks. Look for:

```text
customers/ddc_checks/checks/partnerships/RUNBOOK.md
customers/ddc_checks/checks/partnerships/<check-name>/README.md
```

Use `Glob` from the carrot repo root. This is rare for partnerships but worth a quick check.

## Pattern 5 — Active investigation ticket (the de-facto runbook)

For recurring failures, the curated handoff doc usually covers campaigns/dashboards/segments but *not* per-check remediation. The actual operating runbook for the failure du jour often lives in the open investigation ticket.

Search Jira and Glean in parallel:

```text
mcp__atlassian__searchJiraIssuesUsingJql jql="text ~ \"<check_name>\" AND project = CXP AND statusCategory != Done ORDER BY updated DESC"
mcp__glean__search query="<check_name>"
mcp__glean__search query="[DDC: <check_name>]"
```

What to look for in the ticket:
- The description usually frames the failure pattern ("Chase ENROLLED users without subscription — recurring DDC failure").
- The **most recent investigation comment** is usually the most useful thing — it contains the hypotheses the on-call engineer is currently working through, often with specific Datadog trace queries, SQL probes, or service names.
- The activity log can show what's been tried already (saves you from re-running the same diagnostic).

**Strong-match rule (required to promote into Runbook).** Partnerships often has multiple active CXP investigations in the same product area, and importing the wrong hypothesis or Datadog query misleads triage. Only cite a ticket under the Runbook section when at least one of these holds:
- The ticket title or description names the failing check by **exact name** (e.g., `check_partnership_redemptions_missing_coupons`).
- The ticket references the failing **run UUID** or a specific failing-row identifier (redemption_id, treatment_offer_id, etc.) from today's run.
- The ticket names the same `partnership_benefit_id`, `partnership_id`, or partnership-account identifier as the failure rows, **and** the failure signature in the ticket matches the current run (same SQL clause / error mode), not just the same product area.

How to present a strong match:
- Cite the ticket alongside the doc-based runbook in the Step 5 report under `**Active investigation:**`.
- Quote the relevant investigation step(s) verbatim — don't paraphrase, because the engineer needs the exact query string to act on.
- If the ticket suggests a Datadog query (e.g., "trace `RedeemPartnershipOfferMutation @user_id:<id>`"), include it in the Gaps & engineer next steps section pre-filled with the actual user_ids from today's failure rows.

**Weak match → "Related open tickets (unverified)" in Gaps, not Runbook.** If the only link is product-area overlap (e.g., "this is also a Mastercard ticket") with no exact check-name / run-UUID / identifier match, list it as a separate optional-context bullet in Gaps so the engineer can decide whether to pull it in.

Example partnership investigation tickets that have served as de-facto runbooks: `CXP-187151` (Chase ±5-second join-window investigation), `CXP-209857` (post-enrollment orchestration nil-crash).

## What counts as "a runbook"

A page is a runbook if it tells the engineer what to do when this check fails — specifically, what data to look at and what action to take. A page that just describes the check ("this is the Mastercard credit redemption check, it validates X") is *documentation*, not a runbook.

If the only thing you find is documentation, list it as context but flag in the Gaps section that you didn't find an actual runbook.

## When you find multiple runbooks

The Mastercard/BMO check has two runbook links because it covers two partnerships. Fetch both, but in your output, present them as one combined "Runbook" section with sub-bullets per partnership. Don't make the engineer flip between two pages mentally.

## When you find none

Don't invent steps from the SQL query. Surface this explicitly:

```markdown
## Runbook
- **GAP**: No runbook found. Searched:
  - go/ links in description: none present
  - Confluence CQL: `title ~ "<check name>" AND type = page` → 0 results
  - Glean: "<check name> runbook" → no matches
  - Carrot repo sibling files: none

  The check's SQL is at <github view link>. Recommend filing a runbook
  (the check description points at owner: <owner name>).
```

That's a real finding — the absence of a runbook is itself the most useful thing this skill can tell the engineer in that case.
