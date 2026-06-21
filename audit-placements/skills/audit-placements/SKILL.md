---
name: audit-placements
description: >-
  Comprehensive audit of placements / banners / surfaces / cards (storefront, cart, checkout, account page, modals) that produces a PM-and-Manager-readable Google Doc with one consolidated table.
  Use whenever the user wants an inventory, audit, gap analysis, or coverage map of user-facing surfaces — phrases like "audit all <X> placements", "what banners do we show <cohort>", "produce an inventory of <Y> surfaces", "where does the $N incentive render", "make a google doc listing every checkout placement for express members", "I need a slide-able audit doc for my PM", "what cards does a retained SMB user see".
  Scans Blazer (placements / banners / partnership_offers tables) and the customers-backend codebase in parallel, drafts the row list FOR USER CONFIRMATION before committing, then builds ONE consolidated table with these columns — Surface, Cohort, Codepath/IDs, Status, Condition, Screenshot.
  Captures screenshots from prod via agent-browser with prod cookies (localhost as fallback); for surfaces gated by user state, traces the FULL eligibility chain in code FIRST to identify the load-bearing gate, then BATCHES every grant request (roulette overrides, coupon/policy grants, IC+ status changes, DB inserts) into ONE round trip.
  Rows that can't be captured stay in the table with the SPECIFIC missing gate spelled out — never silently dropped.
  Distinct from audit-lifecycle-logging (that one is about backend observability / logs / metrics; this one is about user-visible surfaces and what they look like).
---

# Audit Placements

Produce a Google Doc audit that a Product Manager or Engineering Manager can read top-to-bottom and walk away knowing **what surfaces exist for a given experience, who sees them, where they're configured, and what each one actually looks like.**

The deliverable is always:

1. A Google Doc with a clear title (`<Domain> placements audit — <YYYY-MM-DD>`)
2. A brief **Executive summary** (1 short paragraph) — scope + headline findings, written in plain English
3. ONE consolidated **placements table** with these six columns:
   - **Surface** — short PM-readable label ("Cart drawer top banner")
   - **Cohort** — which user state sees it ("Retained SMB", "Non-member trial-eligible")
   - **Codepath / IDs** — file paths, resolver names, DB ids (engineer-only column)
   - **Status** — Active / Active — variant N% / Deprecated / Blocked — needs &lt;X&gt; / Not grant-controllable
   - **Condition** — plain-English steps to see the placement ("Add 13+ items to Safeway cart as a retained SMB member")
   - **Screenshot** — cropped image of the placement (or a labeled mock, or a description, in that order of preference)
4. A short **Methodology** note at the bottom — data sources, tools used, grants requested

The audience is mixed (PMs + Managers + engineers). Names go in plain English; jargon lives in the Codepath column. Screenshots are the load-bearing artifact — they're how the reader confirms "this is the thing".

## When to use

Run this skill when the user asks for:
- An inventory or audit of placements / banners / cards / surfaces in a domain
- A coverage map ("what do express members see on the cart page?")
- A pre-launch consolidation doc for PMs reviewing a feature's surfaces
- A post-launch retro of what's actually rendering vs what was designed
- A debugging doc that shows every surface for a specific cohort

Do NOT use this skill for:
- Routine code search ("where is this method defined?") — use grep
- Backend-only audits with no user-visible surfaces — use `audit-lifecycle-logging` instead
- A11y / styling / design review — those need a different tool
- Compare two states of one surface (control-vs-variant) — that's `compare-render`

## Step 1 — Scope the audit

The user gives a prompt like "audit all Mastercard SMB placements" or "what cart banners does an express member see?".

Before any tool calls, restate the scope back in 2–4 lines:

- The **domain** (e.g. Mastercard partnership, IC+ upsell, BOGO promo)
- The **surface families** in scope (cart drawer, checkout, account page, storefront banners, modals)
- The **cohort(s)** — every user state the user wants covered (non-member, IC+ trial, retained SMB, etc.)

A wrong premise here wastes the whole doc. Confirm in one short message before proceeding.

## Step 2 — Enumerate placements (parallel)

Run Blazer + codebase + Roulette discovery in parallel — they're independent and reading them all takes one turn.

**Blazer** — placements / banners / partnership tables are the source of truth for what's *configured*. Use `mcp__blazer__blazer_list_tables` with data source `main` to discover the relevant tables in your environment. Common ones:

- `express_placements` / `express_targeting_placement_configs` / `express_placement_eligibilities` — EPP-managed cards
- `partnership_offers` / `partnership_benefits` / `partnership_redemptions` — partnership domain
- domain-specific `*_banners` / `*_cards` / `*_modals` tables

See [`references/blazer-patterns.md`](./references/blazer-patterns.md) for ready-to-run SQL.

**Codebase** — for each placement family, locate the rendering code path:

```bash
# customers-backend uses {domains,engines,layers} — there is NO top-level app/ tree for placement code.
# domains/ holds business logic (predicates like mastercard_smb_eligible?), engines/ holds GraphQL
# mutations and resolvers, layers/ holds view layouts and response-backed view builders.
rg -n --type ruby '<placement_keyword>' carrot/customers/customers-backend/{domains,engines,layers}
rg -n --type-add 'tsx:*.tsx' --type tsx '<placement_keyword>' carrot/customers/store/client
```

For each surface, identify:
- The resolver / view layout file
- The cohort / eligibility predicate that gates it (e.g. `mastercard_smb_eligible?`)
- The Roulette feature variant(s) controlling visibility

**Roulette** — `mcp__roulette__search_features` for placement-related FVs. Capture `variantWeights` so the audit can distinguish "rolled out to 100% variant" from "1% holdout".

Output of this step lives in your context as a working list of (surface, cohort, codepath, gate, status). **Don't write to the doc yet.**

## Step 3 — Confirm rows + columns with the user

ALWAYS pause here. Show the user:

- The proposed row list as a **markdown table preview** (Surface + Cohort only — keep it scannable)
- The 6 default columns

Ask: "Looks right? Anything to add or remove?" — let them prune before screenshot work begins. This one confirmation costs one message and saves hours of capture effort on rows that won't make the cut.

If they say "go", lock the list. Treat later additions as appended rows, not a table rebuild.

## Step 4 — Build the doc skeleton

Create the Google Doc with `mcp__google-docs__createDocument`. Title: `<Domain> placements audit — <YYYY-MM-DD>`.

Insert in order:

1. **Title** (Heading 1)
2. **Executive summary** (Heading 2) — placeholder paragraph; fill in Step 7
3. **Placements** (Heading 2) — table built via `mcp__google-docs__insertTableWithData`. Header row uses the 6 cols. Body rows: one per (surface × cohort), populated now with Surface name, Cohort, Codepath/IDs, and Condition text. Status: tentative. Screenshot: empty.
4. **Methodology** (Heading 2) — placeholder; fill in Step 7

**Fresh table vs amending an existing one — pick the cheaper write path:**

- For a freshly-built table where you already know every text cell up front (the common case for this skill), pass all rows to `insertTableWithData` as a single call. No cell-index math, no bottom-up edits — text is inlined at creation. Screenshots get inserted as images later via `insertImage`, but the text columns are done in one MCP call.
- For amending a table that already has rows (rare in this skill — usually only happens if you missed a row and the user wants it appended), use the bottom-up cell-edit pattern in Step 6 to preserve indices.

Then call `readDocument` once and cache cell start/end indices for every cell where you'll later insert a screenshot image. Re-reading after every edit is expensive and indices shift after each insert. See [`references/gdoc-table-recipes.md`](./references/gdoc-table-recipes.md).

## Step 5 — Capture screenshots (minimize round-trips!)

This is the step the session this skill was modeled on burned the most time on. Read these sub-steps in order.

### 5a. Trace the FULL gate chain in code BEFORE asking for grants

For each surface, walk the eligibility predicate end-to-end. A real example from the SMB session:

- `account_page_benefits.rb:205 mastercard_smb_eligible?` → calls `active_redemption?` → requires a row in `partnership_redemptions` with `status='active'`.
- The Roulette FV `express_partnership_mastercard_smb_eligibility=force_eligible` bypasses the *service-layer* check but NOT the resolver-layer `active_redemption?`.
- Asking the user to flip the FV without the DB row produces ZERO visible change.

**Lesson:** a name like `force_eligible` describes one check in the chain, not all of them. Read the chain; identify what's **load-bearing**; only ask for grants that actually move the surface from hidden to visible.

### 5b. Batch every grant request into ONE ask

Once you've traced gates for ALL surfaces, compile a single list:

```markdown
To unblock the screenshots, I need:
1. **Roulette overrides** on user <id>:
   - <FV name> → <variant/value>
   - <FV name> → <variant/value>
2. **Coupons / campaigns / policies** granted:
   - <policy name>
3. **IC+ status**: <add / remove / leave as-is>
4. **DB rows** (check Blazer FIRST to see if they already exist; only ask for what's missing):
   - INSERT INTO <table> (<cols>) VALUES (<values>) — for surface <X>
```

Then wait for the user. Do NOT trickle requests across multiple turns — each turn is a real cost to them.

### 5c. Capture with agent-browser (prod preferred, localhost fallback)

Default: prod (`https://www.instacart.com/`) with the user's prod cookies. Fall back to `http://www.instacart.com.test:8081/` only if prod can't reach the state.

```bash
agent-browser --profile ~/.audit-placements open https://www.instacart.com/store/<route>
agent-browser snapshot -i
agent-browser click @eN
agent-browser screenshot --full
```

If agent-browser can't reach the state (cart drawer behind an overlay-intercepted click, dynamic modal, etc.) use the CDP fallback. See [`references/screenshot-capture.md`](./references/screenshot-capture.md) for the prod-cookie file layout, dev `feature_overrides` cookie format, CDP fallback recipe, and cropping commands.

Save each cropped PNG to `/home/bento/snap/chromium/common/screenshots/<audit-slug>-<row-id>.png` (apparmor requires this directory).

### 5d. When a screenshot is genuinely blocked

If after all grants the surface still won't render:

1. **State the SPECIFIC remaining gate** — not "couldn't capture" but "needs an active row in partnership_redemptions for user X on benefit_id=110". Be exact enough that the user could unblock it next turn if they chose.
2. **Try a mock** — render the placement copy in a small HTML page with production strings, screenshot, label it `MOCK`. Better than nothing.
3. If even a mock isn't possible, **describe** the surface in 1–2 lines.

Either way the row stays in the table — see Step 6 status labels.

## Step 6 — Populate rows (bottom-up)

Editing a Google Doc table shifts indices for everything below the edit. So:

1. Push each cropped screenshot to a public gist (`mcp__github__create_gist`) — `insertImage` needs a URL, not a local path.
2. Edit table cells **from the LAST row up to the FIRST**. This preserves the indices you cached in Step 4.
3. For each cell, use the recipes in [`references/gdoc-table-recipes.md`](./references/gdoc-table-recipes.md):
   - Clear content: `deleteRange(cellStart, cellEnd-1)` — that window is the safe deletable range
   - Insert text: `insertText(cellStart, "...")`
   - Insert image: `insertImage(cellEnd-2, imageUrl=<gist raw url>)` — `cellEnd-2` keeps the image inside the target cell

**Status cell** — use one of these literal labels so the doc is scannable at a glance:

- **Active** — currently rendering for the named cohort, screenshot captured
- **Active — variant N%** — rolled out partially (specify the holdout in the Codepath col)
- **Deprecated** — code path removed or behind a deprecation flag (cite the commit if you have it)
- **Blocked — needs &lt;specific gate&gt;** — capture is blocked by a grant we didn't get; name the gate
- **Not grant-controllable — &lt;reason&gt;** — system-level (DxGy infra, locale routing) that user grants can't change

The audit's credibility lives in the Status column being honest. Don't paper over blockers.

## Step 7 — Executive summary + Methodology

Once all rows are populated, fill the placeholders.

**Executive summary** (~3–5 sentences, plain English, zero Roulette/Blazer jargon):

- What was audited (domain + cohorts + surface families)
- N of M surfaces are Active and rendering
- N of M are Deprecated / Blocked / Not grant-controllable
- The single most important takeaway for the PM

**Methodology** (bulleted, can be more technical):

- Blazer tables consulted (and the data source — usually `main`)
- Codebase paths scanned
- Roulette FVs checked
- Grants requested from the user (and which were applied vs declined)
- Capture tool used (agent-browser / CDP fallback) and where the PNGs live

## Step 8 — Deliver

Reply to the user with:

1. The Google Doc URL
2. A 3-bullet recap: rows captured · rows still blocked (with remaining gate) · open questions
3. If any blockers remain that the user *could* still unblock, list them — let the user decide whether the doc is "done enough" to share

## What this skill should NOT do

- **Don't fabricate screenshots.** If a surface won't render, say so and offer a mock. Never paste a similar surface and call it close enough.
- **Don't ship rows silently.** Every row in the table either has a screenshot or has a Status that names the missing gate.
- **Don't ask for grants one-at-a-time.** Trace all gates for all surfaces first, batch the ask. The user's turnaround cost is real.
- **Don't guess from FV names.** A flag called `force_eligible` describes one check, not the whole chain. Read the chain in code before deciding what a grant will unblock.
- **Don't bundle adjacent-domain placements.** If your grep drifts into another team's surfaces (e.g. you're auditing Mastercard SMB and find IC+ trial placements), flag them and ask before adding rows — scope creep makes the doc less useful, not more.
- **Don't write conventional doc filler.** "This document presents an audit of…" / "We hope this is helpful" — kill it. The reader skims; let the table speak.

## Bundled references

- [`references/blazer-patterns.md`](./references/blazer-patterns.md) — common SQL for placements / banners / partnership tables on data source `main`
- [`references/screenshot-capture.md`](./references/screenshot-capture.md) — prod cookie file layout, agent-browser navigation, CDP fallback for overlay-occluded clicks, dev `feature_overrides` cookie format, cropping commands
- [`references/gdoc-table-recipes.md`](./references/gdoc-table-recipes.md) — exact MCP call sequences: cell delete window `[cellStart, cellEnd-1)`, image-insert at `cellEnd-2`, bottom-up edit pattern, gist-URL requirement
