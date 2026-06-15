# Data sources for partnerships DDC remediation

A quick lookup of which source serves which kind of data. Read this in Step 4 of the SKILL when you're not sure where a runbook item lives.

## Blazer (primary for user lookups)

`mcp__blazer__blazer_run_query` against the customers database. Use this for any quick lookup that hits a customers-backend Postgres table.

Most useful tables for partnerships work:

| Table | What's in it |
|---|---|
| `users` | `id`, `email`, `created_at`. Used for the @fernet.io admin check. |
| `partnership_benefits` | Partnership benefit definitions. Join key with `partnership_redemptions`. |
| `partnership_redemptions` | One row per redemption. Has `user_id`, `partnership_benefit_id`, `status`, `redeemed_at`. |
| `coupon_codes` | Coupon issuance. Joined by `discount_policy_id` in the BMO/coupon-mode checks. |
| `retailer_campaigns` / `campaign_properties` / `campaign_treatments` | DXGY campaign config. Used in the Mastercard checks. |

Discovery patterns:

```text
mcp__blazer__blazer_list_data_sources           # find the right database
mcp__blazer__blazer_list_tables data_source=... pattern=partnership
mcp__blazer__blazer_run_query data_source=... statement="SELECT ..."
```

## Snowflake (when Blazer can't reach it)

Many DDC checks read from Snowflake views the application DB doesn't have. The check's own SQL (from `details.sqlQuery`) tells you the exact table names — copy them.

Common Snowflake locations seen in partnerships checks:

- `rds.customers.*` — mirror of customers Postgres (slightly stale)
- `instadata.rds_data.gamification_user_dxgy_assignments` — DXGY treatment assignments
- `instadata.rds_data.users` — user mirror

There is no Snowflake MCP installed by default in this environment. If a runbook step needs Snowflake and you don't have a tool, mark it as a gap and either:

- Suggest the engineer run the query manually, or
- Point at the failure-data S3 file (in `metadata.s3ResultUrl`) which already contains the rows the check matched.

## WittyCart / Quickwit (logs)

The DDC run already returns a pre-filtered logs URL in `metadata.temporal.logsUrl`. Prefer linking that over running a new search — it's narrower (scoped to this run's Temporal workflow ID) and more useful.

If you need broader log context (e.g., "all log lines for user_id X in the last 4 hours") and there's no WittyCart MCP available, mark it as a gap. Don't fall back to "I'll suggest a query" unless the runbook explicitly tells the engineer to look at logs themselves.

## Datadog (when WittyCart isn't enough)

If a runbook step asks for metrics, traces, or aggregated log counts (not raw log lines), use the Datadog MCP:

- `mcp__datadog__search_datadog_logs` — log search with @user_id, @usr.id, service filters
- `mcp__datadog__aggregate_events` — counts/rates over time
- `mcp__datadog__search_datadog_spans` — APM trace search

Common partnership-related services:

- `embedded_instacart`
- `partnership_offer`
- `express_domain`
- `customers-backend`

## Roulette (feature flag state)

If a runbook step says "check whether feature X is enabled for the user," use `mcp__roulette__check_evaluation` or `mcp__roulette__check_feature_assigned`. Partnerships feature names usually start with `partnerships_`.

## Rails console (manual fallback)

Some partnerships state lives only in Ruby objects that aren't trivially queryable (memoized services, ActiveRecord scopes with non-trivial logic). When the runbook says "use the Rails console," don't try to translate it into SQL — just surface the exact commands the engineer should run.

The sibling `debug-user` skill maintains a list at `growth/partnership-experience/skills/debug-user/references/console-commands.md` — link there rather than duplicating it.
