---
name: compare-render
description: >-
  Capture side-by-side screenshots of a frontend change across web + iOS + Android
  viewports and assemble them into one labeled contact sheet, so you can eyeball the
  visual diff on every platform at once. Use this whenever the user wants to SEE what
  a change looks like — "screenshot my change on iOS and android", "before/after of
  this branch", "what does this look like on mobile", "compare control vs variant",
  "show me the new layout on phone + desktop". Two modes: CONTROL-vs-VARIANT (the
  change is behind a runtime gate — flip the gate, no rebuild) and BEFORE-vs-AFTER
  (no gate — render the code at merge-base with origin/master, then the working tree).
  Composes with the force-render skill to discover and force the gate. Local-only,
  never committed. Reach for this even if the user only says "iOS and Android" — offer
  web too, it's free.
---

# compare-render

Turn a frontend change into a single picture that shows it across **web, iOS, and
Android** at once. You drive Chrome's mobile-emulation viewports over CDP (the same
capture path force-render uses), shoot each platform in two states, and `montage` the
six PNGs into one labeled 3×2 contact sheet (rows = web / iOS / Android, columns =
the two states).

The whole point is a **fast visual diff the user can scan in one glance**. The user
runs on a headless Linux box and **cannot see images inline in the terminal** — so the
deliverable is always (a) one combined contact-sheet PNG and (b) the absolute file
paths printed plainly, never "here's the screenshot" with nothing they can open.

## Two modes — pick the right one first

The single most important decision is *what the two columns are*. Get this wrong and
you capture the same thing twice.

| Mode | When | How the two states differ | Rebuild between shots? |
|------|------|----------------------------|------------------------|
| **control-vs-variant** | The change is gated by a feature flag / view variant / `useDebugToggle` — i.e. both states already exist in the *current* bundle and a runtime switch picks one | Flip the gate (cookie / override) | **No** — same bundle, two cookie states. Fast. |
| **before-vs-after** | The change is ungated — it's just different code with no runtime switch | "after" = current working tree; "before" = code at `git merge-base HEAD origin/master` | **Yes** — the bundle must be rebuilt for each code state |

**How to decide:** if the user says "control vs variant", names a flag/variant, or the
change is wrapped in a gate → control-vs-variant. If they say "before/after", "what it
looked like before", or the change has no flag → before-vs-after. When unsure, ask one
short question — guessing wastes a full capture cycle.

## Prerequisites (do these once, up front)

1. **Compose with force-render to find the gate (control-vs-variant only).** Don't
   reinvent gate-tracing. Invoke the `force-render` skill on the changed file — it
   walks the render tree, identifies the exact gate, and tells you the
   `ic_debug_toggles` key (or other override) that flips it. The key is *not*
   guessable from the filename: on the non-member-offers change the runtime key was
   `partnerships_non_member_offers_container_responsive_layout`, which no one would
   have typed from scratch. Let force-render hand you the key; pass it to `capture.py`.

2. **Bring the dev server up.** Invoke the `bento-up` skill (or confirm the relevant
   services are healthy) before driving the browser. A 500 page screenshots just as
   happily as a real one — the preflight is what stops you shipping a picture of an
   error. Remember the house rule: for an enabled-but-unhealthy service use
   `bento restart`, not `bento start`.

3. **Confirm the bundle is current.** Bento's dev server serves the **main checkout's**
   `customers/store/local-build/rspack/*.js`. After any code change (or checkout, in
   before-vs-after mode) rspack must finish rebuilding before you shoot, or you'll
   capture a stale bundle. Verify with a token unique to the change:
   ```bash
   grep -l "<distinctive-string-from-the-diff>" customers/store/local-build/rspack/*.js
   ```
   In before-vs-after mode this is your readiness signal: after reverting to base the
   token should **disappear**; after restoring it should **reappear**.

## Workflow A — control-vs-variant (no rebuild)

Both states live in the current bundle; you just toggle the gate cookie. One Chrome
session, six shots.

```bash
cd ~/snap/chromium/common/screenshots   # outputs MUST live under ~/snap/chromium/common (apparmor)

# variant ON — pass the gate key force-render gave you
python3 ~/.claude/skills/compare-render/scripts/capture.py \
  --url "http://www.instacart.com.test:8081/store/account/instacart-plus" \
  --out-prefix variant \
  --toggle partnerships_non_member_offers_container_responsive_layout

# control (gate cleared)
python3 ~/.claude/skills/compare-render/scripts/capture.py \
  --url "http://www.instacart.com.test:8081/store/account/instacart-plus" \
  --out-prefix control --no-toggle

# contact sheet: rows = web/iOS/android, cols = control | variant
python3 ~/.claude/skills/compare-render/scripts/contact_sheet.py \
  control variant --labels "control,variant" -o compare-nonmember.png
```

`capture.py` prints a one-line layout measurement per platform (`display`, card
count, card width). Use it to *confirm the gate actually flipped* — e.g. control
shows `display:flex` and variant shows `display:grid`. If both columns measure
identical, the gate didn't take (wrong key, stale bundle, or user-state mismatch —
see force-render's gotchas) and the screenshots are worthless. Catch that here, not
after you hand over the image.

## Workflow B — before-vs-after (rebuild between shots)

"after" is what's already being served (your working tree). "before" is the code at
the merge-base. Because the dev server only serves the main checkout, you render the
two states **sequentially in place**: shoot after, revert just the changed files to
base, let rspack rebuild, shoot before, then restore. This touches only the changed
files and is fully reversible.

**Use `origin/master`, never local `master`.** Local `master` drifts far behind (the
user rebases onto upstream), so `git merge-base HEAD master` points at ancient code
and the diff fills with unrelated files. `origin/master` is the real baseline.

```bash
git fetch origin master --quiet
BASE=$(git merge-base HEAD origin/master)

# the frontend files this branch changed (scope to FE extensions)
FILES=$(git diff "$BASE"...HEAD --name-only -- '*.ts' '*.tsx' '*.js' '*.jsx' '*.scss' '*.css')

# SAFETY: refuse if any of those files have uncommitted edits — reverting would lose them
if ! git diff --quiet -- $FILES; then
  echo "Uncommitted edits in changed FE files — commit or stash before before/after."; exit 1
fi

cd ~/snap/chromium/common/screenshots
# 1) AFTER = current working tree (already built)
python3 ~/.claude/skills/compare-render/scripts/capture.py --url "<route>" --out-prefix after --no-toggle

# 2) revert changed files to base, wait for rspack, then shoot BEFORE
git -C /home/bento/carrot checkout "$BASE" -- $FILES
#   wait until the change's token DISAPPEARS from the bundle (rebuild done):
#   until ! grep -ql "<distinctive-string>" customers/store/local-build/rspack/*.js; do sleep 2; done
python3 ~/.claude/skills/compare-render/scripts/capture.py --url "<route>" --out-prefix before --no-toggle

# 3) ALWAYS restore — even if a shot failed
git -C /home/bento/carrot checkout HEAD -- $FILES
#   wait until the token REAPPEARS before telling the user the tree is restored.

python3 ~/.claude/skills/compare-render/scripts/contact_sheet.py \
  before after --labels "before,after" -o compare-before-after.png
```

Restoring the working tree is non-negotiable — run the `checkout HEAD -- $FILES` even
on failure (treat it like a `finally`). Leaving the user's branch reverted is far
worse than a missing screenshot.

> Why not a git worktree? A worktree keeps the tree pristine, but bento's dev server
> serves the *main* checkout's bundle — it won't serve a worktree without a second dev
> server on another port (extra moving parts, brittle). In-place revert-and-restore of
> just the changed files is simpler, reuses the running server, and is safe as long as
> those files have no uncommitted edits (guarded above).

## Device profiles

`capture.py` ships these three (override with `--platforms`):

| Platform | Width | DSF | mobile | UA |
|----------|-------|-----|--------|-----|
| web | 1280 | 1 | false | desktop Chrome |
| ios | 390 | 3 | true | iPhone Safari 17 |
| android | 412 | 2.625 | true | Pixel 7 Chrome |

These are real iPhone/Pixel logical widths. They emulate the **mobile web / webview**
layout — which is what these changes ship to. They are *not* native iOS/Android UI;
genuine native capture would need a real device or simulator, which can't be driven
from this Linux box. For responsive-web and webview changes, viewport emulation is the
correct and sufficient tool. Say so plainly if the user assumes native screenshots.

## Deliverable — what you hand the user

Because the user can't see images inline, every run ends with:

1. **The contact sheet** — one PNG, 3 rows × 2 columns, each cell labeled
   (`web · control`, `web · variant`, …). This is the thing to look at.
2. **Absolute paths**, printed plainly — the contact sheet first, then the six
   individual PNGs in case they want a full-res cell.
3. **The layout measurements** from `capture.py`, as a quick text confirmation that
   the two states genuinely differ (e.g. flex→grid, 1 card→3 cards).

## Local-only — never commit

Everything here — forced gates, cookies, reverted files, screenshots — is for your
eyes during development. Screenshots live under `~/snap/chromium/common/`, outside the
repo. If force-render added a `|| useDebugToggle(...)` to a component, that's a
separate decision the user makes (keep as a durable dev affordance or `git checkout`
it) — surface it, don't silently leave or remove it.

## Gotchas (most are inherited from force-render — read its skill for the full list)

- **Stale bundle** is the #1 silent failure. Always grep the rspack output for the
  change token before believing a screenshot.
- **EPP / user-state matching** can blank the card regardless of the gate. If the
  section is empty in *both* states, the account isn't in the targeted state — that's
  a force-render problem to solve before compare-render can show anything.
- **`maki load` is destructive**; `maki load customers-express` populates
  `partnership_offers` but `maki sync instacart:express` does **not**. Get the data in
  before you shoot.
- **Outputs outside `~/snap/chromium/common/` are blocked** by snap apparmor — that's
  why the script writes there.
- **Hydration**: the script settles ~8s after load before measuring/shooting; bump
  `--settle` if the section renders late.
