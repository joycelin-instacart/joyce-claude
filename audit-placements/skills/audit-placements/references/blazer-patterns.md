# Blazer patterns for placement audits

All queries below run on data source **`main`** (NOT `customers_growth` — that's access-denied for most callers). Use `mcp__blazer__blazer_run_query` with `data_source: "main"`. Every query needs a `{blazer_now}` placeholder somewhere when time-bounded; Blazer will reject unbounded queries.

## Discover tables in a domain

```python
# In doubt about table names? List them first.
mcp__blazer__blazer_list_tables(data_source="main")
```

Filter the output for placement-shaped names: `*_placements`, `*_banners`, `*_cards`, `*_modals`, `partnership_*`, `express_*`.

## EPP — Express Placement Platform

Source-of-truth tables for what's configured on cart / checkout / account cards.

### List recent EPP placements

Actual `express_placements` schema (verified 2026-06): `(id, placement_type, layout_type, data, created_at, updated_at, updated_by)`. There is **no** `name` column and **no** `is_enabled` flag — the placement's targeting/enablement lives downstream in `express_targeting_placement_configs`. The `data` column is JSON with the row's contents.

```sql
SELECT
  id,
  placement_type,
  layout_type,
  updated_at,
  updated_by,
  data
FROM express_placements
WHERE updated_at > {blazer_now} - INTERVAL '2 years'
ORDER BY updated_at DESC
LIMIT 200;
```

Filter by domain keyword inside the JSON, e.g. `WHERE data ILIKE '%mastercard_smb%'`.

### Targeting configs for a specific placement

Inspect with `mcp__blazer__blazer_get_schema(data_source="main", table="express_targeting_placement_configs")` before guessing columns — schemas drift. Typical filter shape:

```sql
SELECT *
FROM express_targeting_placement_configs
WHERE express_placement_id = <placement_id>
  AND created_at > {blazer_now} - INTERVAL '1 year';
```

### Eligibility rules

Same pattern — schema first, then filter:

```sql
SELECT *
FROM express_placement_eligibilities
WHERE express_placement_id = <placement_id>
  AND created_at > {blazer_now} - INTERVAL '1 year';
```

## Partnership domain

Partnership cards (account page Mastercard tile, Chase tile, etc.) are gated by a 3-table chain: **offer** → **benefit** → **redemption**.

### List active partnership offers

Actual `partnership_offers` schema (verified 2026-06): `(id, name, display_name, path, start_date, end_date, country_ids, ...)` — there is **no** `partnership_type`, **no** `is_active`, and **no** `active_start_date`/`active_end_date`. "Active" = `end_date > now()` (or NULL).

```sql
SELECT
  id,
  name,
  display_name,
  path,
  start_date,
  end_date,
  country_ids
FROM partnership_offers
WHERE (end_date IS NULL OR end_date > {blazer_now})
  AND start_date < {blazer_now}
  AND created_at > {blazer_now} - INTERVAL '3 years'
ORDER BY name;
```

### Benefits attached to an offer

```sql
SELECT
  id,
  partnership_offer_id,
  name,
  benefit_type,
  benefit_payload
FROM partnership_benefits
WHERE partnership_offer_id = <offer_id>;
```

### Has a specific user already redeemed?

```sql
SELECT
  pr.id,
  pr.user_id,
  pr.partnership_benefit_id,
  pb.name AS benefit_name,
  pr.status,
  pr.redeemed_at,
  pr.start_date,
  pr.end_date
FROM partnership_redemptions pr
JOIN partnership_benefits pb ON pb.id = pr.partnership_benefit_id
WHERE pr.user_id = <user_id>
  AND pr.created_at > {blazer_now} - INTERVAL '2 years'
ORDER BY pr.redeemed_at DESC;
```

A row with `status='active'` and `redeemed_at` populated is the load-bearing artifact for "the user has an active redemption" predicates downstream. Check this BEFORE asking the user to grant anything for a partnership surface.

## Roulette FV cross-reference

Roulette doesn't live in Blazer; pull via the dedicated MCP and cross-reference by FV name in the codebase.

```python
mcp__roulette__search_features(name_contains="<placement_keyword>")
mcp__roulette__get_feature_by_name(name="<exact_fv_name>")
```

Pay attention to `variantWeights` — a FV at 100% variant behaves very differently from one at 1% holdout. The audit should distinguish these in the Status col.

## Gotchas

- **Verify columns before SELECTing them.** Schemas drift. Run `mcp__blazer__blazer_get_schema(data_source="main", table="<name>")` once, then write the SELECT. The example SQL above pins the verified shape as of 2026-06, but treat it as a starting point — a stale column name will fail the whole query and force a retry.
- **`information_schema` introspection trips Blazer's no-time-filter guard.** `SELECT * FROM information_schema.columns WHERE table_name = '…'` will be rejected. Use `blazer_get_schema` instead.
- **Data source name matters.** `main` works for almost everything placement-related. `customers_growth` is usually denied; if a query needs it, ask the user rather than guessing your way through error messages.
- **`{blazer_now}` is required.** Blazer rejects queries without a time bound on long-lived tables. Use `INTERVAL '<N> years'` if you really want a wide window.
- **Lowercase status values.** Real rows tend to use `status='active'` (lowercase), not `'ACTIVE'`. Verify with a `SELECT DISTINCT status FROM …` before filtering.
- **Test users are reusable.** Joyce keeps SMB / express / non-member test users; if you need a specific cohort state, ask for the user_id rather than picking a random row.
