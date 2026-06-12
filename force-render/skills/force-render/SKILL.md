---
name: force-render
description: Make Joyce's in-progress FE changes visible in her local browser by finding every gate between the changed code and the rendered page, forcing them open, recommending the maki commands needed for DB state, then driving agent-browser to verify. Use whenever Joyce says things like "let me see this in the browser", "force my variant on", "what do I need to render this", "make this visible locally", "show me my change", or after she finishes an FE change behind a Roulette / behind an EPP card / behind any partnership_offers / express_user_state_definitions gate. Default to this skill instead of manually stubbing FV hooks or guessing what to seed.
---

# Force Render

Goal: Joyce just changed something in the FE — a component behind a Roulette, an EPP card, a partnership-offer-gated section — and wants to see it render in her local browser. Without this skill, that usually means: figure out which Roulette gates the change, stub the hook, figure out which DB tables are empty after `maki sync`, run the right command, navigate, hard-refresh, hope. This skill does the trace for her and verifies the result.

## What this skill is and isn't

**Is:**
- A static-analysis pass from changed file → up the render tree → down through GraphQL fragments → into BE resolvers → out to the DB tables that gate the render.
- A local-only "stub the FE FV hook" affordance for the gates that aren't otherwise overridable.
- A recommendation of the `maki sync` / `maki load` command(s) needed to populate the empty tables.
- A drive-the-browser verification step that proves the changed element actually rendered.

**Isn't:**
- A `maki` runner — Joyce decides whether to run the recommended command (the `maki load` variant resets her local DB, so it's her call).
- A Roulette admin override — we only touch the FE FV hook file locally; the prod Roulette is unchanged.
- A way to ship code. **Every edit this skill applies (stubs, `useDebugToggle` insertions, cookie pokes, anything else) is a local dev affordance — never `git add`, `git commit`, or `git push` from inside this skill.** Treat every code edit as "DO NOT COMMIT" by default. Joyce uses this skill to see her own in-progress change render; if a toggle or stub turns out to be ship-worthy, she'll lift it into a real product PR herself in a separate pass.

## Workflow

Run the steps in order. Don't skip the trace — knowing *all* the gates upfront prevents the "stubbed one, still empty, stubbed another" loop Joyce hates.

### 1. Identify the changed surface(s)

Read git status + diff to find changed FE files. Focus on `.tsx`/`.ts` in `customers/store`, `customers/help`, `customers/landing`, and any `.rb` view layout files in `customers/customers-backend/domains/view_domain`. Note both committed-on-branch and uncommitted changes — Joyce often runs this mid-implementation.

For each changed FE component file, that's a starting node for the trace.

### 2. Walk UP the render tree to find gates

For each changed component, find every importer (`grep -rn "from '../<component-name>'" customers/store/client`). Walk up until reaching a page-level component (filename like `*Page.tsx`, in `pages/`, or rendered by a router). At each level, look for:

- **FV hook calls** — anything matching `use*Variant(`, `useFeature*(`, `createClientSideFeatureVariantHook`. Capture the variable name, the file it's imported from, and the Roulette feature name from the hook definition.
- **Conditional renders** — `if (!offerCards?.length || visibilityVariant === 'false') return null` style early-returns and ternary-based show/hide. These often reference the FV hook result OR a field from the GraphQL viewSection.
- **Required props** — props the component needs to render at all (e.g., `partnershipOffers` non-null).

Record the gate chain: `[changed file] ← [parent component, gate X] ← [grandparent, gate Y] ← [page]`.

### 3. Trace DOWN through GraphQL into BE

For each GraphQL fragment imported by a component in the chain (look for `gql\`fragment Xxx on Yyy { ... }\``):

- Find the matching BE GraphQL type definition (`grep -rn "Yyy" customers/customers-backend/engines/graph/app/graphql/types/`).
- Read the resolver method that returns it. In view-section-style layouts (`*_response_backed/*.rb`), the methods named `<variant>_variant`, `visibility_variant`, etc. are gates.
- Inside resolver methods, look for:
  - `Roulette.features["..."].enabled?` — server-side gate. Note the feature name.
  - `FeatureVariants::Xxx.new(...).visible?` — same, wrapped in an FV class.
  - Calls to eligibility services (e.g., `EligibilityService.find_eligible_placement_configs`, partnership status checks).
  - DB lookups via domain APIs (`PartnershipOfferDomain::Api::GetOffer`, etc.).
- For each eligibility/DB call, trace down to identify which **tables** must have data for the gate to evaluate true.

### 4. Map gates to overrides

For each gate found in steps 2 and 3, classify in this order of preference (cheapest first):

All overrides below are **local dev affordances** — apply them in the working tree, verify in the browser, then revert before any commit. The "preferred" column is about which override leaves the smallest cleanup footprint, NOT about which is fit to ship.

| Gate kind | Preferred override | Why preferred |
|---|---|---|
| Component already composes a flag with `useDebugToggle('<key>')` (pattern: `isEnabled = flag \|\| useDebugToggle(...)`) | Just **set the `ic_debug_toggles` cookie** in the browser. **No file edit at all** — zero cleanup. | `useDebugToggle` is platform-owned (`client/platform/shared/debug/`) and reads from the cookie at runtime. Pre-existing toggle = no diff to revert. |
| FE FV hook (`createClientSideFeatureVariantHook`) — **NO** `useDebugToggle` in the component | Two options, both local-only: (a) Temporarily add `\|\| useDebugToggle('<key>')` to the component and use the cookie. (b) Stub the `featureVariants.ts` file to return `{ visible: true as const, loading: false }`. Either way, add the DO-NOT-COMMIT header described below and revert via `git checkout` before committing. Pick whichever Joyce finds easier to revert (the stub is usually more surgical). |
| BE viewSection variant resolved server-side | Two options, both local-only: (a) Temporarily add `useDebugToggle('<key>')` to the FE component that reads the field — `nonMemberGridEnabled = !isMember && (responsiveLayoutVariant === 'true' \|\| useDebugToggle(...))`. (b) Stub the BE resolver method to return `BooleanVariant::True`. Either way, DO NOT COMMIT — revert before pushing. |
| DB-backed eligibility | Map to the maki sync/load recommendation in step 5 — no FE override can fake DB data. |
| Conditional render on `offerCards.length > 0` and the like | Trace down — there's a query behind it; the query needs DB seed. |

**The `useDebugToggle` cookie format** (paste into DevTools console; works for any key, registered or not):
```js
document.cookie = `ic_debug_toggles=${encodeURIComponent(JSON.stringify({your_key: true}))}; path=/; max-age=2592000; samesite=lax`
location.reload()
```
Clear with: `document.cookie = 'ic_debug_toggles=; path=/; max-age=0'; location.reload()`. Or just visit `Cmd+Ctrl+Shift+D` for the debug panel (only registered keys appear there; cookie works for unregistered).

### 5. Recommend maki commands for missing DB state

For each table identified in step 3 that's likely to be empty after the typical `maki sync instacart:<group>`:

- If the table is in a `.pgsync.yml` group, recommend `maki sync instacart:<group>` or `maki sync instacart:<table>` if it's listed individually.
- If the table is NOT in `.pgsync.yml` but IS in `infra/maki/conf/customers/datasets/<name>.yml` as a `maki_pgsync` line, recommend `maki load <snapshot-variant>` (e.g., `maki load customers-express`).
- If the table is in neither, recommend a manual `INSERT` snippet or flag that it needs a one-off seed.

Output as: `> Run: maki sync instacart:express` (or whichever) with a one-line explanation of which table it populates and why it's needed. **Do not run it** — Joyce wants to decide (especially for `maki load` which resets the local DB).

### 6. Apply overrides (local-only — never commit)

For each gate flagged in step 4. **Every edit below is a temporary working-tree change. Don't stage, don't commit, don't push.** Tell Joyce up front what you're editing and offer the `git checkout` command to revert it in the same message.

**If the override is the `ic_debug_toggles` cookie alone** (component already composes with `useDebugToggle`): drive the browser to set the cookie via `Runtime.evaluate` (CDP) or agent-browser `eval`. No file edit, no cleanup needed.

**If the override is a temporary `useDebugToggle('<key>')` insertion** into a component that doesn't currently compose with one: apply the edit, then immediately surface the revert command (`git checkout <path>`) in your reply. Add a top-of-file DO-NOT-COMMIT comment so Joyce sees it if she happens to scroll past:

```ts
// !! LOCAL DEV OVERRIDE — DO NOT COMMIT !! Added by force-render to flip <variant> ON locally.
// Revert: git checkout <file-path>
```

If Joyce later decides the toggle is genuinely worth shipping, that's a separate decision she makes outside this skill — open a fresh ask, don't roll it into the force-render flow.

**If the override is a file stub** (FE FV hook returning `{ visible: true as const, loading: false }`, or a BE resolver returning `BooleanVariant::True`): rewrite the file and add this header at the top:

```ts
// ============================================================================
// !! LOCAL DEV OVERRIDE — DO NOT COMMIT !!
// Forces <variant-name> ON for local visual verification.
// Restore before pushing:
//   git checkout <file-path>
// ============================================================================
```

Use `as const` for the FE stub so the literal type stays `true` (matches what `createClientSideFeatureVariantHook`'s real output looks like to TS).

### 7. Wait for rspack/HMR

After stubbing, the dev server needs to rebuild. Touch the file once (`touch <file>`) and wait ~6 seconds before reloading the browser — rspack rebuilds aren't always picked up by HMR for variant-hook changes.

### 8. Pre-flight: ensure bento is healthy

Before driving any browser, invoke the **`bento-up`** skill via the `Skill` tool. Reason: a half-healthy bento (especially `customers/store/web` or `customers/customers-backend/web` in `timeout` state) will silently swallow page loads and waste a 240s CDP timeout. `bento-up` enumerates unhealthy services and restarts them; takes ~30-90s when `customers-backend/web` is involved.

Do this even if the last `bento status` you ran looked fine — health drifts between turns, and a stale `timeout` row is the most common reason the browser verification step hangs with no output.

If `bento-up` reports everything is healthy, proceed to step 9 immediately — no harm done. If it restarted anything, wait for it to confirm green before driving the browser.

### 9. Drive a browser to verify

**Try `agent-browser` first.** If `agent-browser open` hangs silently (no output for 60s), you're hitting the snap-chromium apparmor issue on the bento dev box. Stop trying — see fallback below.

Happy path:
1. Open the URL the page renders at (ask Joyce if it's not obvious from the route file; default to the page Joyce was last working on).
2. Wait for `networkidle` + a 5-8s settle for hydration.
3. Find a stable selector that identifies the changed element (a heading text from the new section, a data-testid, etc.).
4. Confirm it's in the DOM. Measure layout (grid template, computed style) and report numbers — Joyce often wants those.
5. Screenshot with `--full --path /tmp/force-render-<short-name>.png`.

**Fallback when agent-browser hangs (snap chromium):** drive chromium directly via CDP using the script template at `/home/bento/snap/chromium/common/screenshots/shoot2.py`. Adapt the URL and viewport widths. Save outputs INSIDE `~/snap/chromium/common/screenshots/` (snap apparmor blocks writes outside `~/snap/chromium/common/`). See [[reference-chromium-snap-cdp-workaround]] for the full pattern. You'll need a fresh Cookie header in `ic-cookies.txt` if Joyce's last auth state is stale — ask her to paste a recent "Copy as cURL" from her real browser DevTools.

If the changed element doesn't render even with all gates forced: re-trace. Either a gate was missed, or there's a deeper DB requirement (e.g., the user_state's conditions need a specific cohort the test user isn't in). Don't loop blindly — surface what was found and ask Joyce.

**One more pitfall worth checking before you re-trace:** the FE bundle may be stale. `bento restart customers/store/web` and then verify the new field name shows up in the bundle: `grep -l "<your-new-field>" customers/store/local-build/rspack/*.js`. If grep returns nothing, the bundle didn't pick up your rebased FE — restart is the fix.

### 10. Report + clean-up instructions

End with:
- Path to the screenshot.
- The exact `git checkout` command to revert **every** file you touched in step 6 — stubs AND `useDebugToggle` insertions AND anything else. List them as a single block Joyce can paste.
- The cookie-clear snippet if you set any debug cookies.
- The maki command Joyce should run (if she hasn't already and the DB state is still incomplete).
- Any gates that couldn't be forced (BE-only Roulettes without a Joyce-controllable override, etc.).

Don't auto-revert and don't auto-commit — Joyce often iterates and wants to keep seeing the variant for follow-up tweaks. Leave the working tree dirty with the cleanup commands handy so she can revert on her own schedule.

Do NOT offer "commit + push" as a next-step option at the end of the run. The skill stops at "rendered + cleanup snippets surfaced". If Joyce decides the toggle/stub is worth shipping (rare), she'll open a separate ask for that.

## Gotchas (worth knowing upfront)

- **Stub file must keep imports.** Leave the original imports in place at the top of the stubbed `featureVariants.ts`; add a `void` reference if needed to avoid unused-import lint errors. Joyce's lint config will flag dead imports.
- **`useXxxxVariant({ skip: isMember })` API.** The real hook accepts an opts object. Your stub should accept `(_opts?: { skip?: boolean })` to match — TS errors otherwise.
- **rspack rebuild can be silent for ~5s.** Don't reload the browser immediately after editing; wait, or touch the file to force a recompile signal.
- **`maki load` is destructive.** It resets the entire local DB to a snapshot. Joyce explicitly wants to opt in. Recommend, don't run.
- **The page-level `visibilityVariant === 'false'` check.** For non-IC+ partnership-offers, the page resolver returns False on non-marketplace store configs. If Joyce is on a partner SFX URL the whole section is hidden regardless of how many FE FVs you stub. Trace it.
- **The store-app account page is locked to ≥1024px viewport.** Don't be surprised if narrowing the browser doesn't drop columns — the page itself horizontally scrolls instead of reflowing.
- **EPP user-state matching is the silent killer.** A non-IC+ user sees zero offer cards if none of the 28-ish `express_offer_card` user_states have conditions that evaluate true for them. Empty `partnership_offers` table means almost every partnership-gated state evaluates false. `maki load customers-express` (snapshot) populates it; `maki sync instacart:express` does NOT (it only syncs express_* tables).

## When in doubt

If the trace gets murky (e.g., the gate involves a TaaS segment, a feature_dependency Joyce doesn't recognize, or a code path that goes through services not in customers-backend), surface what you found and ask Joyce. She'd rather steer than have you guess.
