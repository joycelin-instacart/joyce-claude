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

Show the user:

- The proposed row list as a **markdown table preview** (Surface + Cohort only — keep it scannable)
- The 6 default columns

Ask: "Looks right? Anything to add or remove?" — let them prune before screenshot work begins. This one confirmation costs one message and saves hours of capture effort on rows that won't make the cut.

If they say "go", lock the list. Treat later additions as appended rows, not a table rebuild.

**Headless mode (no interactive user):** If you're running in a non-interactive context (subagent, eval, CI — basically any context where you can't get a human reply mid-run), don't skip this step — *externalize* it. Write the proposed row list to `outputs/rows-proposal.md` as the FIRST artifact (before any screenshot work, before doc creation), then proceed with all proposed rows. The proposal becomes the artifact the reviewer reads after the fact and the pruning conversation moves to the iteration-N+1 loop. Without this file, the reviewer has no way to tell which rows were considered-and-rejected vs missed-entirely.

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

### 5d. When a real prod capture is blocked — MOCK FIRST, don't surrender to "Not captured"

If after all grants the surface still won't render in prod, the default move is **build an HTML mock**, not give up. Steps in order:

1. **Build an HTML mock of the WHOLE component, not just the copy.** Render the placement in a small HTML page using the production string literals (from YAML, view layout, or rendered template), screenshot via Chromium with `--screenshot=<path>`, embed in the doc with a clear `MOCK` label in the Screenshot cell caption. A labeled mock is dramatically more useful than a "Not captured — needs cookie" row because the reader is reading a *doc*, not your filesystem; they want to see the surface.

   **The component frame is load-bearing — render every visible piece a real user would see, not just the inner text.** For a modal: backdrop overlay, modal frame, header / title, body copy, primary CTA, secondary CTA, dismiss X. For a card: brand mark, title, body, AND any action buttons. For a cart banner: full banner with icon, copy, optional dismiss. A mock that shows only the title + subtitle text reads as "the agent didn't look at the surface" — it loses the comparison value PMs use mocks for ("is this CTA copy clear next to the dismiss option?"). When in doubt, render *more* chrome, not less.

   Use the copy-pasteable template at [`references/screenshot-mock-template.html`](./references/screenshot-mock-template.html) — fill in the title, body, CTAs, brand mark, and render it via:

   ```bash
   chromium --headless --disable-gpu --hide-scrollbars \
     --window-size=560,200 \
     --screenshot=/home/bento/snap/chromium/common/screenshots/<slug>-mock.png \
     "file:///path/to/mock.html"
   ```

   Skip the mock ONLY if the row has no renderable copy at all — pure backend resolvers, migration jobs, YAML configs with no body literal. In that case write the status text instead (step 3).

2. **State the SPECIFIC remaining gate** in the Status column — not "couldn't capture" but "Blocked — needs active row in partnership_redemptions for user X on benefit_id=110". Be exact enough that the user could unblock it next turn if they chose. This applies even when you DID render a mock — the mock shows what the surface looks like; the Status column tells the reader what's blocking the real capture.

3. If no copy exists to mock AND no real capture is possible, **describe** the surface in 1–2 lines in the Screenshot cell AND cite the codepath that would render it. This is the rarest case.

The row stays in the table either way — see Step 6 status labels.

## Step 6 — Populate rows (bottom-up)

**Inline images are LOAD-BEARING.** A captured PNG sitting in `outputs/` with no `insertImage` call into the doc is NOT done — the reader is in the doc, not your filesystem. Every row's Screenshot cell must end up containing one of:

- An inline image (gist URL → `insertImage` into the cell), real prod capture or MOCK
- A Status that names the exact missing gate (and ideally a MOCK image alongside per Step 5d)

The gist + insertImage round-trip is the load-bearing step in screenshot capture — not the `agent-browser screenshot` call. "Captured but didn't embed" reads as "missed the surface" to the doc reader.

Editing a Google Doc table shifts indices for everything below the edit. So:

1. Push each cropped screenshot to a public gist (`mcp__github__create_gist` with all PNGs in one batch — one gist per audit, not one per image) — `insertImage` requires a URL, not a local path. The MCP rejects `localImagePath` silently in sandboxed environments. Capture the raw gist URLs into a small `insert_plan.json` so you can re-run the inserts deterministically if the doc-edit pass partial-fails.
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
- **Don't ship rows silently.** Every row in the table either has an inline image (real or MOCK) or has a Status that names the missing gate.
- **Don't split into multiple tables.** Even if the user's prompt suggests Table 1 / Table 2 / Table 3 (e.g. one per copy variant, one per surface family), push back and consolidate. The single table IS the value prop — it's what lets a PM scan "what does cohort X see across all surfaces" in one pass. If grouping matters, use a sort order or a Cohort-prefix in the Surface column, not separate tables. Surface the structural reason in your reply ("merging into one table because that's what makes the doc PM-scannable; happy to re-split if you'd rather").
- **Don't claim drift without a byte-equal compare.** YAML can store `%{var}` placeholders while the DB stores the interpolated form — that's not drift. Before flagging "DB title disagrees with YAML source", actually interpolate the YAML template with the same inputs and compare the rendered output. A raw-string diff on uninterpolated YAML is noise.
- **Don't ask for grants one-at-a-time.** Trace all gates for all surfaces first, batch the ask. The user's turnaround cost is real.
- **Don't guess from FV names.** A flag called `force_eligible` describes one check, not the whole chain. Read the chain in code before deciding what a grant will unblock.
- **Don't bundle adjacent-domain placements.** If your grep drifts into another team's surfaces (e.g. you're auditing Mastercard SMB and find IC+ trial placements), flag them and ask before adding rows — scope creep makes the doc less useful, not more.
- **Don't write conventional doc filler.** "This document presents an audit of…" / "We hope this is helpful" — kill it. The reader skims; let the table speak.

## Bundled references

- [`references/blazer-patterns.md`](./references/blazer-patterns.md) — common SQL for placements / banners / partnership tables on data source `main`
- [`references/screenshot-capture.md`](./references/screenshot-capture.md) — prod cookie file layout, agent-browser navigation, CDP fallback for overlay-occluded clicks, dev `feature_overrides` cookie format, cropping commands
- [`references/gdoc-table-recipes.md`](./references/gdoc-table-recipes.md) — exact MCP call sequences: cell delete window `[cellStart, cellEnd-1)`, image-insert at `cellEnd-2`, bottom-up edit pattern, gist-URL requirement
