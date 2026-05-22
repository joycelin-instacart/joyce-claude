---
name: datadog-lifecycle-dashboard
description: Generate a Datadog dashboard JSON to monitor a user lifecycle (funnel, workflow, or adoption cohorts) for a customers-backend feature/project — OR evaluate an existing dashboard link and suggest improvements. Writes the resulting JSON to /tmp/datadog-dashboards/<feature>.json for the user to copy into Datadog. Trigger whenever the user says "make a datadog dashboard for X", "monitor the lifecycle of Y", "build me a launch dashboard for feature Z", "look at this datadog dashboard and tell me what's missing", "evaluate this dashboard <url>", or asks for observability for a feature about to roll out. Pair with the [[audit-lifecycle-logging]] skill — that one verifies the metrics exist in code; this one charts them.
---

# Datadog Lifecycle Dashboard

Two modes:

- **Generate mode** — produce a launch-quality Datadog dashboard JSON for a customers-backend feature, organized by lifecycle stage.
- **Evaluate mode** — when the user pastes a dashboard link, fetch its widgets and metric queries via the Datadog MCP, compare against the standard lifecycle template, and report gaps + write a revised JSON.

Both modes end by writing a `*.json` file to `/tmp/datadog-dashboards/`. Always print the file path and a one-liner curl/UI instruction so the user can immediately copy it into Datadog.

This skill is the chart-side companion to [[audit-lifecycle-logging]]. That skill confirms `ICMetrics.increment` / `Rails.logger` calls exist at every lifecycle step. This skill turns those metrics into a dashboard. If the user hasn't audited yet, suggest running that skill first — charting metrics that don't exist yet wastes everyone's time.

## When the lifecycle shape is unclear, ask

Three lifecycle shapes are supported. Detect from the user's message; if ambiguous, ask **one short question** before drafting.

| Shape | When to pick it | Dashboard organization |
|---|---|---|
| **Funnel** | A/B-tested feature with discrete user-visible steps (exposure → eligibility → impression → click → conversion) | Top-line conversion ratios + per-stage counts, grouped left→right by funnel order |
| **Workflow** | Feature with an internal flow (entry → external API call → state mutation → terminal). The NYT outbound dashboard ([[reference-good-dashboard]]) is workflow-shaped. | One group per stage (entry, integration calls, jobs, terminal states), error breakdowns inside each group |
| **Adoption cohorts** | New vs returning vs churned users of a feature over time | Cohort retention/churn timeseries + new-user counts, grouped by cohort age |

If the feature is brand-new and you can't tell, default to **workflow** — it's the shape most launch dashboards take and degrades gracefully into funnel or adoption later.

## Step 0 — Confirm the feature scope

Restate to the user in 3-5 lines: the feature name, the lifecycle shape, and the **metric prefixes** you'll chart. A wrong premise here produces a dashboard that looks plausible but charts the wrong metrics.

Pull metric prefixes by:

1. Asking the user for the entry point (orchestrator/consumer/resolver/service path), OR
2. Grepping the repo: `rg -n 'METRIC_PREFIX\s*=' <path>` and looking at the actual `ICMetrics.increment` calls in those files

Don't guess prefixes from class names. The `METRIC_PREFIX` constant is the source of truth, and it doesn't always match the class name 1:1.

## Step 1 — Decide widget layout

Read [`references/customers-backend-metric-patterns.md`](./references/customers-backend-metric-patterns.md) once at the start of generate mode. It maps `ICMetrics.increment(prefix.event, tag: value)` to the Datadog query that charts it, lists the standard tag breakdowns (`by {status}`, `by {error_type}`, `by {reason}`, `by {error_source}`), and explains the `custom.` prefix Datadog auto-prepends.

Then pick widget groups per the lifecycle shape (see table above). Within a group, the order is always:

1. **Volume** — total `*.success` count (`sum:custom.<prefix>.success{$env}.as_count()`)
2. **Errors** — broken down by tag (`sum:custom.<prefix>.error{$env} by {error_source}.as_count()`) **only if the code actually emits that tag**. Confirm by reading the `ICMetrics.increment` call: `ICMetrics.increment("...error", tags: { error_source: ... })`. If the emit has no `tags:` kwarg, skip the breakdown — a flat error count is more honest than a `by {invented_tag}` widget that produces no data forever.
3. **Edge cases** — count of each non-success non-error branch the code emits (e.g. `not_found`, `missing_token`, `already_active`)
4. **Latency** — if the step uses `ICMetrics.timing`, add `max:custom.<prefix>.<op>{$env}` with a note that this is worst-case, not p95

This order matters: it's how on-call reads a dashboard during an incident — "is traffic flowing → are errors elevated → which edge case fired → how slow is the partner".

**Never `by {kube_cluster_name}` / `by {service}` / `by {pod_name}`** unless the user explicitly asks for an infra view. Datadog auto-tags those, so the breakdown will technically render — but it splits a feature metric across nodes that are irrelevant to product behavior, and adds visual noise during incidents.

## Step 2 — Build the JSON

Start from [`assets/lifecycle-dashboard-template.json`](./assets/lifecycle-dashboard-template.json). It is a minimal, valid Datadog dashboard envelope with one example group. Copy it, then fill in groups + widgets per Step 1. Common widget recipes are in [`assets/widget-snippets.md`](./assets/widget-snippets.md) — `timeseries`, `query_value`, `group`, and toplist.

Required dashboard properties:

- `title` — `<Feature> — Lifecycle & Health` (matches the NYT reference dashboard style)
- `description` — include: one-line purpose, link to the feature's runbook if known (or `TODO: runbook`), monitor IDs the dashboard pairs with (or `TODO: add monitors`), and any known limitations (e.g. "latency is max only — convert `ICMetrics.timing` → `ICMetrics.distribution` for true percentiles")
- `template_variables` — always include `env` with default `production`. Add `retailer_id` only if the feature's metrics are tagged with it.
- `layout_type` — `"ordered"`
- `widgets` — groups containing widgets; use `"type": "group"` with `"layout_type": "ordered"` to box each lifecycle stage

Every metric query MUST:

- Be prefixed with `custom.` (Datadog adds this automatically to `ICMetrics`-emitted metrics — your queries must include it explicitly)
- Filter by `{$env}` at minimum
- Suffix `.as_count()` for `increment` metrics (not for `timing`/gauges)

If you skip `.as_count()` on counter metrics, the chart shows per-second rates instead of raw counts and will confuse on-call. This is the single most common mistake — double-check before writing the file.

## Step 3 — Write the file

Write the assembled JSON to `/tmp/datadog-dashboards/<feature_slug>.json` (mkdir -p the directory first). Use a lowercase kebab-case feature slug (e.g. `nyt-outbound`, `epp-partnership-card`).

Then print to the user:

```
Wrote: /tmp/datadog-dashboards/<feature_slug>.json
To import: in Datadog, New Dashboard → ⚙️ → Import dashboard JSON → paste contents.
```

Don't try to `curl` the Datadog API yourself — the user copies the JSON into the UI. (If they explicitly ask for an API import, they can use the `dashboards/9np-v48-q5g`-style POST themselves.)

## Evaluate mode

Trigger this mode when the user provides a dashboard URL (e.g. `https://instacart.datadoghq.com/dashboard/abc-def-ghi`) and asks for improvements / a review. Extract the dashboard ID from the URL (the slug between `/dashboard/` and the next `/` or end-of-string).

### Fetch the dashboard

Use the Datadog MCP:

```
mcp__datadog__search_datadog_dashboards
  query: "id:<dashboard_id>"
  include_description: true
  include_template_variables: true
  max_queries_per_dashboard: 200
  max_tokens: 30000
```

If the MCP isn't authed or returns nothing, ask the user to paste the exported JSON (Datadog UI → ⚙️ → Export dashboard JSON). Don't try to scrape the URL.

### Compare against the standard template

For each lifecycle stage you'd expect (based on the feature's metric prefixes — grep the repo as in Step 0), check:

| Check | What to look for |
|---|---|
| **Volume widget present** | `sum:custom.<prefix>.success{...}.as_count()` exists for every prefix in the feature's code |
| **Error breakdown present** | At least one widget has `by {error_source}` or `by {status}` / `by {reason}` / `by {error_type}` on the error metric |
| **Edge-case branches charted** | For each non-success non-error `ICMetrics.increment` branch in the code, there's a widget |
| **Latency widget present** | Each `ICMetrics.timing` call has a `max:custom.<...>` widget |
| **`$env` template var** | Dashboard has an `env` template variable and queries use `{$env}` |
| **`.as_count()` on counters** | Every `sum:` counter query suffixes `.as_count()` |
| **Description has runbook + monitor IDs** | Description links to a runbook (or `TODO:`) and lists monitor IDs (or `TODO:`) |
| **Naming consistency** | Widget titles use the same casing/format throughout (no mix of "Activation Errors" + "activation error count") |

### Report findings + write the revised JSON

Produce the report **inline in your chat response** — do not write it to a `.md` file. Many environments block subagent writes for `report*.md` / `summary*.md` / `findings*.md` / `analysis*.md`, and the report is more useful in-thread anyway (the user can read it without opening a file). The only on-disk artifact in evaluate mode is the revised JSON.

Use this exact template (it mirrors [[audit-lifecycle-logging]] so the two skills feel like a pair):

```markdown
# Dashboard review — <dashboard title> (`<dashboard_id>`)

**Feature:** <feature name>
**Lifecycle shape detected:** <funnel / workflow / adoption>
**Code reference:** <orchestrator/service path the dashboard is monitoring>

## Summary

| Stage | Volume | Errors broken down | Edge cases | Latency | Verdict |
|---|---|---|---|---|---|
| <stage 1> | ✓ / ✗ | ✓ / ✗ | <N missing> | ✓ / ✗ / n/a | ok / needs work |

## Findings

### [high] <short label>
- Where: widget "<title>" / missing widget
- Why it matters: <one sentence>
- Suggested fix: <query string or widget snippet>

### [med] ...

## Layout & readability

- <ordering issues, naming inconsistencies, widget sizing>

## Alert / SLO coverage gaps

- For each critical-path metric (top of funnel volume, terminal-state errors), note whether a monitor exists. Use `mcp__datadog__search_datadog_monitors` if needed to verify.
- Don't fabricate monitor IDs — if you can't confirm, say "no monitor found for <metric>, recommend adding".

## Revised JSON

Wrote: /tmp/datadog-dashboards/<feature_slug>-revised.json
```

Severity hierarchy (highest → lowest): missing error breakdown on a critical path > missing latency on an external API call > missing edge-case widget > naming/layout inconsistency > description missing runbook link.

Always write the revised JSON file even if findings are minor — Joyce asked for it as an explicit deliverable. Apply your suggested fixes to the dashboard JSON and save to `<feature_slug>-revised.json` next to the original.

## Things this skill should NOT do

- **Don't audit logging / metrics coverage in code** — that's [[audit-lifecycle-logging]]. If the user wants to know whether the metrics they want to chart even exist, redirect them.
- **Don't create monitors or alerts** — flag missing ones in the report, but don't generate monitor JSON. Monitors have their own SLO/owner/escalation policy that's outside this skill's scope.
- **Don't pick metric prefixes from class names** — read `METRIC_PREFIX` constants. The constant is the contract; the class name might drift.
- **Don't hand-write Datadog query syntax from memory.** Read [`references/customers-backend-metric-patterns.md`](./references/customers-backend-metric-patterns.md) at the start of each invocation — query syntax is fiddly and the doc has the exact patterns that work.
- **Don't add widgets for metrics you can't trace back to the code.** If the user asks for "everything observable", grep for the prefixes first; charting hypothetical metrics produces dashboards that show "no data" forever.

## Bundled reference

- [`assets/lifecycle-dashboard-template.json`](./assets/lifecycle-dashboard-template.json) — minimal valid dashboard envelope with one example group
- [`assets/widget-snippets.md`](./assets/widget-snippets.md) — copy-pasteable widget definitions (timeseries, query_value, group, toplist)
- [`references/customers-backend-metric-patterns.md`](./references/customers-backend-metric-patterns.md) — ICMetrics → Datadog query mapping, tag conventions, and gotchas
