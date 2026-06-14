---
name: compare-render
description: >-
  Capture side-by-side screenshots of a frontend change across web + iOS + Android
  viewports and assemble them into one labeled contact sheet, so you can eyeball the
  visual diff on every platform at once. Use this whenever the user wants to SEE what
  a change looks like — "screenshot my change on iOS and android", "before/after of
  this branch", "what does this look like on mobile", "compare control vs variant",
  "show me the new layout on phone + desktop". Two modes: CONTROL-vs-VARIANT (the
  change is behind a runtime flag — flip the flag per shot, no rebuild) and
  BEFORE-vs-AFTER (ungated code — render the code at merge-base with origin/master,
  then the working tree). Reach for this even if the user only says "iOS and Android"
  — offer web too, it's free. Local-only, never committed.
---

# compare-render

Turn a frontend change into a single picture that shows it across **web, iOS, and
Android** at once. You drive Chrome's mobile-emulation viewports over CDP, shoot each
platform in two states, and `montage` the six PNGs into one labeled 3×2 contact sheet
(rows = web / iOS / Android, columns = the two states).

The user runs on a headless Linux box and **cannot see images inline** — so the
deliverable is always (a) one combined contact-sheet PNG and (b) the absolute paths
printed plainly, never "here's the screenshot" with nothing they can open.

## The one principle that matters most: show the truth

The value of this skill is a **faithful** diff — two columns that differ *only because
the real rendered code path differs*. The single worst outcome is a picture that looks
like a successful comparison but isn't: two columns that secretly render the same state,
or a "difference" you manufactured by hand.

So: **never fake a diff.** Don't inject CSS, don't edit the DOM in the browser, don't
hand-build a grid that the app didn't render. If the two states come out *identical*
when they shouldn't, that's not a problem to paper over — it's a signal telling you one
of these is wrong, and the honest move is to diagnose it and say so:

- You picked the **wrong mode** (the most common one — see below).
- The **flip didn't take** (wrong override value, or you forced a gate that doesn't
  control this surface).
- The **bundle is stale** (before-vs-after only — you screenshotted before the rebuild).
- The **account/user-state is wrong**, so the section never renders for *either* column
  (`capture.py` prints a loud `SECTION ABSENT` line for this — no flag flip can fix it).

A diff you can trust beats a pretty picture every time. If you genuinely can't produce a
real difference, report *why* and what's needed (e.g. "this account is a member; the
non-member section only renders for non-members") rather than synthesizing one.

## Two modes — pick the right one first

This is the decision that makes or breaks the run. Get it wrong and both columns show
the same thing.

| Mode | Use when | How the two states differ | Rebuild? |
|------|----------|----------------------------|----------|
| **control-vs-variant** | The change is behind a **runtime flag** — a feature variant / Roulette experiment / `useDebugToggle`. Both code paths already exist in the *current* bundle; a runtime switch picks one. | Flip the flag per shot (cookie / header / debug toggle) | **No.** Same bundle, two flag states. Fast. |
| **before-vs-after** | The change is **ungated code** — no runtime switch, the new look ships unconditionally. | "after" = current working tree; "before" = code at `git merge-base HEAD origin/master` | **Yes.** The bundle must rebuild for each code state. |

**The trap that cost a whole capture cycle:** if the change is flag-gated, *do not* use
before-vs-after. Reverting the code to merge-base does **not** move a runtime flag — the
flag stays at its default (usually control) in *both* the "before" and "after" builds, so
you get two identical control columns and conclude "no diff" when really you just used the
wrong tool. A flag-gated change is **always** control-vs-variant.

**How to tell if it's gated:** trace the changed component to what decides which branch
renders. If a boolean/variant from props, a hook, a GraphQL field, or a `useDebugToggle`
picks the layout → gated → control-vs-variant. If the new markup/styles render
unconditionally (no flag in the path) → ungated → before-vs-after. The `force-render`
skill does exactly this trace; lean on it for discovery (next section). When you still
can't tell, ask one short question — it's cheaper than a wasted capture.

## Finding and flipping the gate (control-vs-variant)

There are two jobs here, and it's worth keeping them separate:

**1. Discover the gate** — *what* controls the layout. Don't guess from the filename; the
flag name is rarely typeable from scratch. Invoke the **force-render** skill on the
changed file: it traces up the render tree and down through GraphQL into the backend
resolver and tells you the exact gate — the feature-variant name, the GraphQL field, and
which value maps to which state. Use it for the *trace*, not the flip (see below).

**2. Flip the gate per shot** — *this skill owns this*, because the flip has to be a
clean per-column switch from the **same bundle** (you need control AND variant in one
run). The mechanism depends on the gate class force-render found:

| Gate class | How to flip it per shot | `capture.py` flag |
|------------|-------------------------|-------------------|
| **Server-side feature variant** (a Roulette FV resolved in the backend, surfaced as a GraphQL `viewSection` field the FE just reads) | Set the **`feature_overrides`** cookie (or `X-Feature-Overrides` header). Dev allows this unconditionally (`Rails.env.development?` short-circuits the override guard). | `--cookie 'feature_overrides=<fv>.<method>.<value>'` and/or `--header 'X-Feature-Overrides: <fv>.<method>.<value>'` |
| **Client debug toggle** (component reads `useDebugToggle` / `ic_debug_toggles`) | Set the `ic_debug_toggles` cookie | `--toggle <key>` / `--no-toggle` |

> **Why not let force-render flip it?** For a *server-side* feature variant, force-render's
> only override is to **edit source** (insert a `useDebugToggle`, or stub the resolver to
> return `true`). That's a stateful working-tree mutation — you can't toggle it off again
> for the control shot from the same bundle. The `feature_overrides` cookie *can* be set
> per-shot, which is exactly what a two-column comparison needs. So: force-render discovers,
> `capture.py` flips.

### `feature_overrides` format

`<feature_variant_name>.<method>.<value>` — `method` is `visible` or `variant`:
- `myfeature.visible.true` / `myfeature.visible.false` — force the FV's `visible?` result.
  This is the most direct lever when the backend reads `.visible?`.
- `myfeature.variant.<arm>` — force the assigned variant arm.

Stack multiple overrides with commas: `a.visible.true,b.variant.control`. The header
(`X-Feature-Overrides`) takes precedence over the cookie if you set both.

**Worked example** (the non-member offers responsive layout — gate
`partnerships_non_member_offers_container_responsive_layout`, GraphQL field
`nonMemberResponsiveLayoutVariant`):

```bash
cd ~/snap/chromium/common/screenshots   # outputs MUST live under ~/snap/chromium/common (apparmor)
FV=partnerships_non_member_offers_container_responsive_layout
ROUTE="http://www.instacart.com.test:8081/store/account/instacart-plus"

# variant — grid ON
python3 ~/.claude/skills/compare-render/scripts/capture.py \
  --url "$ROUTE" --out-prefix variant --cookie "feature_overrides=${FV}.visible.true"

# control — grid OFF (explicit, so a prior override can't leak into this shot)
python3 ~/.claude/skills/compare-render/scripts/capture.py \
  --url "$ROUTE" --out-prefix control --cookie "feature_overrides=${FV}.visible.false"

# contact sheet: rows = web/iOS/android, cols = control | variant
python3 ~/.claude/skills/compare-render/scripts/contact_sheet.py \
  control variant --labels "control,variant" -o compare-nonmember.png
```

`capture.py` prints a one-line layout measurement per platform (`display`, card count,
card width). **Use it to confirm the flip actually took** before you believe the
screenshots — e.g. control measures `display:flex / flexDir:column` and variant measures
`display:grid`. If both columns measure identical, the flip didn't take: re-read "show
the truth" above and diagnose, don't ship it.

## Prerequisites

1. **Dev server up.** Confirm the relevant bento services are healthy before driving the
   browser — a 500 page screenshots just as happily as a real one. House rule: for an
   enabled-but-unhealthy service use `bento restart`, not `bento start`.

2. **Right account / user-state.** Many sections only render for a specific user state
   (the non-member offers section, for instance, renders *only for non-members* —
   `!isMember` gates it). No flag flip can render a section the account isn't eligible
   for. If `capture.py` prints `SECTION ABSENT` for *both* states, the account is wrong,
   not the flag — fix that first (different account cookies, or a user-state override) and
   say so to the user.

3. **Data present.** `maki load` is destructive but populates tables; e.g.
   `maki load customers-express` populates `partnership_offers` while
   `maki sync instacart:express` does not. Get the data in before you shoot.

## Workflow A — control-vs-variant (no rebuild)

Both code paths live in the current bundle; you only toggle the flag. One Chrome session
per state, six shots total. This is the worked example above. Steps:

1. Discover the gate with force-render (flag name + GraphQL field + value mapping).
2. `capture.py` with the variant override → `variant-{web,ios,android}.png`.
3. `capture.py` with the control override → `control-{web,ios,android}.png`.
4. Verify the per-platform measurements differ (flip took).
5. `contact_sheet.py control variant` → the deliverable.

## Workflow B — before-vs-after (rebuild between shots)

**Only for ungated code changes.** "after" is your working tree (already served);
"before" is the code at the merge-base. The dev server serves the *main* checkout, so you
render the two states sequentially in place: shoot after, revert just the changed files to
base, wait for the rebuild, shoot before, then restore.

**Use `origin/master`, never local `master`** — local `master` drifts far behind (the
user rebases onto upstream), so `git merge-base HEAD master` points at ancient code and
the diff fills with unrelated files. `origin/master` is the real baseline. `git fetch
origin master` may fail on auth here — that's fine, the local `origin/master` ref is
present; use it (or the known BASE sha) directly.

```bash
BASE=$(git merge-base HEAD origin/master)

# the frontend files this branch changed (render-affecting only — skip specs/fixtures)
FILES=$(git diff "$BASE"...HEAD --name-only -- '*.ts' '*.tsx' '*.js' '*.jsx' '*.scss' '*.css' \
        | grep -vE '(__tests__|__fixtures__|\.spec\.|\.test\.)')

# SAFETY: refuse if any of those files have uncommitted edits — reverting would lose them
if ! git diff --quiet -- $FILES; then
  echo "Uncommitted edits in changed FE files — commit or stash first."; exit 1
fi

cd ~/snap/chromium/common/screenshots
# 1) AFTER = current working tree (already built)
python3 ~/.claude/skills/compare-render/scripts/capture.py --url "<route>" --out-prefix after

# 2) revert changed files to base, WAIT FOR THE REBUILD, then shoot BEFORE
git -C /home/bento/carrot checkout "$BASE" -- $FILES
#    (see "Confirming the rebuild" below — do not shoot until the served bundle is fresh)
python3 ~/.claude/skills/compare-render/scripts/capture.py --url "<route>" --out-prefix before

# 3) ALWAYS restore — even if a shot failed (treat as finally)
git -C /home/bento/carrot checkout HEAD -- $FILES
#    wait for the rebuild again before telling the user the tree is restored.

python3 ~/.claude/skills/compare-render/scripts/contact_sheet.py \
  before after --labels "before,after" -o compare-before-after.png
```

Restoring the working tree is non-negotiable — run the `checkout HEAD -- $FILES` even on
failure. Leaving the user's branch reverted is far worse than a missing screenshot.

### Confirming the rebuild (before-vs-after only)

rspack must finish rebuilding before you shoot, or you capture a stale bundle. The dev
server serves the live bundle from the **main checkout's build dir**:

- Entrypoint: `customers/store/build/client/store.webpack_bundle.js`
  (served at `http://127.0.0.1:8083/javascripts/store/store.webpack_bundle.js`).
- Manifest: `customers/store/build/manifest/rspack-assets.json` (copied from `build/client`
  after each compile).

Confirm a rebuild by watching the **mtime advance** past your `git checkout`:

```bash
BUNDLE=/home/bento/carrot/customers/store/build/client/store.webpack_bundle.js
before_mtime=$(stat -c %Y "$BUNDLE")
git -C /home/bento/carrot checkout "$BASE" -- $FILES
until [ "$(stat -c %Y "$BUNDLE")" -gt "$before_mtime" ]; do sleep 2; done   # rebuild done
```

**Do NOT** grep `customers/store/local-build/rspack/*.js` — that path is stale (days old)
and is **not** on the serving path. It was the readiness check in an earlier version of
this skill and silently passed against old code. The `build/client` + `build/manifest`
paths above are the real ones.

> Why not a git worktree? A worktree keeps the tree pristine, but the dev server serves
> the *main* checkout's bundle — it won't serve a worktree without a second dev server on
> another port (extra moving parts, brittle). In-place revert-and-restore of just the
> changed files reuses the running server and is safe as long as those files have no
> uncommitted edits (guarded above).

## Device profiles

`capture.py` ships these three (override with `--platforms`):

| Platform | Width | DSF | mobile | UA |
|----------|-------|-----|--------|-----|
| web | 1280 | 1 | false | desktop Chrome |
| ios | 390 | 3 | true | iPhone Safari 17 |
| android | 412 | 2.625 | true | Pixel 7 Chrome |

These are real iPhone/Pixel logical widths emulating the **mobile web / webview** layout —
which is what these responsive changes ship to. They are *not* native iOS/Android UI;
genuine native capture would need a real device or simulator, which can't be driven from
this Linux box. For responsive-web and webview changes, viewport emulation is the correct
and sufficient tool. Say so plainly if the user assumes native screenshots.

## Deliverable — what you hand the user

Because the user can't see images inline, every run ends with:

1. **The contact sheet** — one PNG, 3 rows × 2 columns, each cell labeled
   (`web · control`, `web · variant`, …). This is the thing to look at.
2. **Absolute paths**, printed plainly — the contact sheet first, then the six individual
   PNGs in case they want a full-res cell.
3. **The layout measurements** from `capture.py`, as a text confirmation that the two
   states genuinely differ via the real render (flex→grid, column count, card width) —
   and that the difference came from the flag flip / rebuilt bundle, not from anything you
   did by hand.

## Local-only — never commit

Everything here — forced flags, cookies, reverted files, screenshots — is for your eyes
during development. Screenshots live under `~/snap/chromium/common/`, outside the repo.
Never `git add` / `commit` / `push`. If a before-vs-after run touched tracked files, the
run isn't done until the tree is restored (only the pre-existing untracked `local-build/`
dirs should remain in `git status`).

## Gotchas

- **Wrong mode** is the #1 silent failure — a flag-gated change run as before-vs-after
  shows control in both columns. Re-read "Two modes" if your columns match.
- **Stale bundle** (before-vs-after) is #2 — always confirm the `build/client` mtime
  advanced before shooting. The old `local-build/rspack` grep is a trap.
- **`SECTION ABSENT`** in both columns = user-state mismatch (e.g. a member account on a
  non-member-only section). No flag flip fixes this; fix the account.
- **EPP / user-state matching** can blank a card regardless of the flag — that's a
  force-render/data problem to solve before compare-render can show anything.
- **Outputs outside `~/snap/chromium/common/` are blocked** by snap apparmor — that's why
  the scripts write there.
- **Hydration**: `capture.py` settles ~8s after load before measuring/shooting; bump
  `--settle` if the section renders late.
