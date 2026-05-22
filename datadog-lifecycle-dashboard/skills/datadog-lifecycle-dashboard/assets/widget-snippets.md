# Widget snippets

Copy-paste these into the `widgets` array of the dashboard JSON. Every snippet uses `<placeholder>` markers — replace before writing the final file.

## Group (wraps a lifecycle stage)

```json
{
  "definition": {
    "type": "group",
    "layout_type": "ordered",
    "title": "Stage N — <stage name>",
    "background_color": "vivid_blue",
    "widgets": []
  }
}
```

Color suggestions to make stages visually distinct:
- Entry / top-of-funnel: `vivid_blue`
- Middle stages: `vivid_purple` or `vivid_green`
- Terminal states (success/error): `vivid_green` for success, `vivid_orange` for warn, `vivid_pink` for error

## query_value (single big-number widget)

Use for headline volume metrics on the left edge of each group.

```json
{
  "definition": {
    "type": "query_value",
    "title": "<short title>",
    "requests": [
      {
        "q": "sum:custom.<prefix>.<event>{$env}.as_count()",
        "aggregator": "sum"
      }
    ],
    "precision": 0,
    "autoscale": true
  }
}
```

## timeseries (counter, broken down by tag)

Use for error breakdowns and any metric where you want to see which dimension is firing.

```json
{
  "definition": {
    "type": "timeseries",
    "title": "<short title>",
    "requests": [
      {
        "q": "sum:custom.<prefix>.error{$env} by {<tag>}.as_count()",
        "display_type": "bars",
        "style": {
          "palette": "warm",
          "line_type": "solid",
          "line_width": "normal"
        }
      }
    ],
    "show_legend": true,
    "legend_layout": "auto",
    "legend_columns": ["avg", "max", "value", "sum"]
  }
}
```

Common tag choices: `error_source`, `status`, `reason`, `error_type`, `result`.

## timeseries (latency — max gauge from ICMetrics.timing)

```json
{
  "definition": {
    "type": "timeseries",
    "title": "Latency — <op> (max only)",
    "requests": [
      {
        "q": "max:custom.<prefix>.<timed_op>{$env}",
        "display_type": "line"
      }
    ],
    "show_legend": false
  }
}
```

If `ICMetrics.distribution` is used instead of `ICMetrics.timing`, you can chart true percentiles:

```json
{
  "definition": {
    "type": "timeseries",
    "title": "Latency — <op> p50/p95/p99",
    "requests": [
      { "q": "p50:custom.<prefix>.<distribution_op>{$env}", "display_type": "line" },
      { "q": "p95:custom.<prefix>.<distribution_op>{$env}", "display_type": "line" },
      { "q": "p99:custom.<prefix>.<distribution_op>{$env}", "display_type": "line" }
    ],
    "show_legend": true
  }
}
```

## toplist (top N values of a tag)

Use when you want "which retailers/error_sources/variants contribute most" rather than a timeseries.

```json
{
  "definition": {
    "type": "toplist",
    "title": "Top error sources",
    "requests": [
      {
        "q": "top(sum:custom.<prefix>.error{$env} by {error_source}.as_count(), 10, 'sum', 'desc')"
      }
    ]
  }
}
```

## note (markdown banner)

Use sparingly at the top of a group to explain context the title can't carry.

```json
{
  "definition": {
    "type": "note",
    "content": "Latency widgets show MAX. Convert `ICMetrics.timing` → `ICMetrics.distribution` for p95.",
    "background_color": "yellow",
    "font_size": "14",
    "text_align": "left",
    "vertical_align": "top",
    "show_tick": false
  }
}
```

## Ratio widget (conversion between two funnel stages)

For funnel-mode dashboards, you often want the **ratio** of stage N+1 to stage N.

```json
{
  "definition": {
    "type": "query_value",
    "title": "<stageA> → <stageB> conversion",
    "requests": [
      {
        "formulas": [{ "formula": "query2 / query1", "number_format": { "unit": { "type": "canonical_unit", "unit_name": "percent" } } }],
        "queries": [
          { "name": "query1", "data_source": "metrics", "query": "sum:custom.<prefix>.<stageA>{$env}.as_count()" },
          { "name": "query2", "data_source": "metrics", "query": "sum:custom.<prefix>.<stageB>{$env}.as_count()" }
        ],
        "response_format": "scalar",
        "aggregator": "sum"
      }
    ],
    "precision": 2,
    "autoscale": false
  }
}
```
