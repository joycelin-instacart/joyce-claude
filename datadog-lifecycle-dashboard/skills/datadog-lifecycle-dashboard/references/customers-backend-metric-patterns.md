# customers-backend metric patterns

How to map `ICMetrics` calls in the customers-backend repo to Datadog query strings. Read this once at the start of generate or evaluate mode — query syntax is fiddly and getting it wrong produces dashboards that look right but show "no data".

The canonical contract for emitting metrics is [`docs/observability-conventions.md`](../../../carrot/customers/customers-backend/docs/observability-conventions.md) in customers-backend. This file is the **charting** side — how those emitted metrics appear in Datadog.

## The `custom.` prefix

Every metric emitted via `ICMetrics.increment("foo.bar")` or `ICMetrics.timing("foo.bar")` shows up in Datadog as `custom.foo.bar`. The `custom.` is added by IC's stats infrastructure.

**This means**: in queries, always write `sum:custom.<metric_name>{...}`. In code, you write `"<metric_name>"` without the `custom.` prefix. Mixing these up is the most common mistake.

## METRIC_PREFIX templates

Per the observability conventions doc, each layer has a prefix template:

| Layer | Template | Example |
|---|---|---|
| Orchestrators | `<domain>_orchestrators.<orchestrator_name>` | `partnership_offer_orchestrators.nyt_redemption_notification` |
| Graph resolvers | `resolvers.<domain>.<resolver_name>` | `resolvers.partnerships.partnership_cards` |
| Graph mutations | `mutations.<domain>.<mutation_name>` | `mutations.partnerships.redeem_partner_offer` |
| Domain APIs | `<domain>.api.<api_name>` | `partnership_offer_domain.api.migrate_nyt_api_benefit` |
| Services | `<domain>.services.<category>.<service_name>` (omit category if top-level) | `partnership_offer_domain.nyt_partner_gateway` |
| Consumers | `<domain>.consumers.<consumer_name>` | `treatments.consumers.treatments_offer_creation` |

To find a feature's prefixes: `rg -n 'METRIC_PREFIX\s*=' <feature_directory>`. The prefix is the literal string in the constant — don't reconstruct it from the class name.

## Branch suffixes

Standard branch suffixes on `*.increment` calls (in rough order of how often they appear):

| Suffix | Means | Chart as |
|---|---|---|
| `.success` | Happy-path completion | Volume / query_value |
| `.error` | Caught exception or downstream failure | Timeseries by `error_source` or `error_type` |
| `.failed` | Business-logic failure (often distinct from `.error`) | Timeseries, often grouped with `.error` |
| `.not_found` | Lookup miss | Timeseries |
| `.attempted` | Top-of-funnel call count | Volume / query_value |
| `.skipped` | Guard-clause early return | Timeseries by tag (`reason`, etc.) |
| `.<edge_case>` | Domain-specific edge case (`already_active`, `missing_token`, `duplicate_blocked`) | Timeseries, one per edge case OR one with `by {edge_case_tag}` if tagged |

If the code emits `.error` AND `.failed` for the same operation, chart both — they usually represent different failure modes (exception vs business-rule denial).

## Tag breakdowns

`ICMetrics.increment` accepts extra keyword args that become Datadog tags. Common ones:

| Tag | Where it appears | Chart as |
|---|---|---|
| `error_source: "..."` | On `.error` metrics, names the downstream that failed | `by {error_source}` |
| `status: <int_or_string>` | HTTP/RPC response status | `by {status}` |
| `reason: "..."` | Business-rule failures | `by {reason}` |
| `error_type: <class_name>` | Exception class | `by {error_type}` |
| `result: "success" / "fail" / "mismatch"` | Used in axon/experiment patterns | `by {result}` |
| `variant: "..."` | Feature variant from Treatment Serving | `by {variant}` — only if the feature actually tags it |
| `retailer_id: <int>` | Per-retailer breakdown | `by {retailer_id}` — common in EPP / partnership features |
| `offer_name: "..."` | Promo/partnership offer slug | `by {offer_name}` — useful for filtering single-offer features |

Don't invent tags. If the code doesn't pass the kwarg, the dashboard's `by {tag}` query returns one bucket called `n/a` and looks broken.

## `.as_count()` — almost always required for counters

Datadog stores `ICMetrics.increment` calls as rates by default. To see raw counts, suffix the query with `.as_count()`:

```
sum:custom.partnership_offer_domain.create_nyt_activation_url.success{$env}.as_count()
```

Without `.as_count()`, the same query returns per-second rates, which on-call almost never wants for a launch dashboard. The exception: if you genuinely want a rate (e.g. "requests per second"), drop `.as_count()` and label the widget accordingly.

For `ICMetrics.timing` (gauges), do NOT use `.as_count()`. Use `max:` or `avg:` aggregators.

## `$env` is mandatory

Every query must filter by `{$env}` (or include it in a multi-tag filter like `{offer_name:nyt_cooking_outbound,$env}`). Without it, prod + staging metrics blend together and the dashboard misleads.

The template variable is declared once at the dashboard level (see `assets/lifecycle-dashboard-template.json`).

## Latency: timing vs distribution

```ruby
ICMetrics.timing("foo.bar.api_call") { call_partner }      # → gauge, single value per emit
ICMetrics.distribution("foo.bar.api_call") { call_partner } # → distribution, supports true percentiles
```

- `timing` → chart with `max:custom.<...>` for worst-case. p95 is **not available** from a gauge — the dashboard will look like it gives you percentiles but the math is wrong.
- `distribution` → chart with `p50:` / `p95:` / `p99:` aggregators.

If the code uses `timing` and the user wants p95, the right fix is in code (switch to `distribution`), not in the dashboard. Flag this in the dashboard description as a known limitation, as the NYT reference dashboard does.

## Worked example

Given this code:

```ruby
class Partnership::NytPartnerGateway
  METRIC_PREFIX = T.let("partnership_offer_domain.nyt_partner_gateway", String)

  def create_activation_url(user_id:)
    response = ICMetrics.timing("#{METRIC_PREFIX}.create_activation_url") { client.post(...) }
    ICMetrics.increment("#{METRIC_PREFIX}.create_activation_url.status", status: response.status)
    if response.ok?
      ICMetrics.increment("#{METRIC_PREFIX}.create_activation_url.success")
      response.body
    else
      Rails.logger.error(message: "nyt activation url failed", log_id: "a1b2c3d4e5f6", user_id: user_id)
      ICMetrics.increment("#{METRIC_PREFIX}.create_activation_url.error", error_source: "nyt_partner")
      nil
    end
  end
end
```

The dashboard widgets for this single operation are:

```
sum:custom.partnership_offer_domain.nyt_partner_gateway.create_activation_url.success{$env}.as_count()
sum:custom.partnership_offer_domain.nyt_partner_gateway.create_activation_url.error{$env} by {error_source}.as_count()
sum:custom.partnership_offer_domain.nyt_partner_gateway.create_activation_url.status{$env} by {status}.as_count()
max:custom.partnership_offer_domain.nyt_partner_gateway.create_activation_url{$env}
```

Note how the `timing` metric's name has no suffix — it's literally `create_activation_url`, while the `increment` metrics nest under `create_activation_url.success` / `.error` / `.status`. Read the code; don't assume a suffix exists.

## Gotchas

- **Forgetting `.as_count()`** — chart shows fractions per second, on-call gets confused.
- **Charting a metric that doesn't exist** — happens when you read the prefix from the class name instead of `METRIC_PREFIX`. Always grep the constant.
- **`by {tag}` on a metric that's not tagged** — produces an `n/a` series and looks broken. Verify the kwarg is actually passed at the call site.
- **Using `avg:` on an `increment` counter** — averages a per-bucket sum, which has no useful meaning. Use `sum:` for counters.
- **Latency p95 from `timing`** — not possible; needs `distribution`. Note in description.
