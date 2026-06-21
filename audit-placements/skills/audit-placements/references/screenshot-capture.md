# Screenshot capture for placement audits

The audit's value lives in the screenshots. Aim for prod-rendered, cropped to the placement, captured under the right cohort state.

## Where things live

| Thing | Path |
|---|---|
| Prod cookies (per-cohort) | `/home/bento/snap/chromium/common/screenshots/ic-cookies-prod-<cohort>.txt` |
| Audit PNGs | `/home/bento/snap/chromium/common/screenshots/<audit-slug>-<row-id>.png` |
| Chromium user-data dirs | `/home/bento/snap/chromium/common/cdp-data-<port>/` |

The `~/snap/chromium/common/` prefix is mandatory — apparmor blocks Chromium from writing anywhere else. Don't fight it.

Cookies live OUTSIDE the git tree and **must never be committed**. Settings.json deny list already covers `**/secrets/**`, `**/credentials/**`, but the cookies live under `~/snap/` so they're not auto-protected — be careful.

## Default path: agent-browser

For most surfaces (storefronts, account pages, IC+ pages, checkout flows that don't require a populated cart):

```bash
# Authenticated profile, persists across runs
agent-browser --profile ~/.audit-placements open https://www.instacart.com/store/<route>
agent-browser snapshot -i
agent-browser click @eN
agent-browser wait --load networkidle
agent-browser screenshot --full
```

If the user data dir needs to start authenticated, seed it once with cookies before the first run:

```bash
# One-shot: import cookies into a fresh profile dir
agent-browser --profile ~/.audit-placements open https://www.instacart.com
# (then log in once interactively, or push cookies via CDP — see below)
```

## When agent-browser isn't enough: CDP fallback

The `feedback_cdp_click_overlay_occlusion` memory captures this: cart drawers, modals, and other overlay-heavy surfaces sometimes intercept `dispatchMouseEvent` at the wrong z-layer, so an agent-browser click silently does nothing. Use JS `.click()` via CDP `Runtime.evaluate` instead.

Template script (adapt per audit):

```python
import json, subprocess, sys, time, urllib.request, base64
from websocket import create_connection

OUT_PREFIX = "/home/bento/snap/chromium/common/screenshots/<audit-slug>"
COOKIE_FILE = "/home/bento/snap/chromium/common/screenshots/ic-cookies-prod-<cohort>.txt"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9557

with open(COOKIE_FILE) as f:
    cookie_header = f.read().strip()
cookies = []
for part in cookie_header.split("; "):
    if "=" in part:
        n, v = part.split("=", 1)
        c = {"name": n, "value": v, "domain": "www.instacart.com", "path": "/", "secure": True}
        if n.startswith("__Host-"):
            c.pop("domain", None)
            c["url"] = "https://www.instacart.com/"
        cookies.append(c)

chrome = subprocess.Popen([
    "chromium", "--headless=new", "--disable-gpu", "--no-sandbox",
    f"--user-data-dir=/home/bento/snap/chromium/common/cdp-data-{PORT}",
    "--window-size=1400,1800",
    f"--remote-debugging-port={PORT}", "--remote-allow-origins=*", "about:blank",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=1); break
        except Exception: time.sleep(0.5)
    page = [t for t in json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json").read()) if t.get("type") == "page"][0]
    ws = create_connection(page["webSocketDebuggerUrl"])
    msg_id = [0]
    def send(method, params=None):
        msg_id[0] += 1
        ws.send(json.dumps({"id": msg_id[0], "method": method, "params": params or {}}))
        while True:
            r = json.loads(ws.recv())
            if r.get("id") == msg_id[0]: return r
    def evaljs(expr):
        r = send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("result", {}).get("value")
    def snap(name):
        shot = send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        with open(f"{OUT_PREFIX}-{name}.png", "wb") as f:
            f.write(base64.b64decode(shot["result"]["data"]))

    send("Page.enable"); send("Network.enable"); send("Runtime.enable")
    send("Network.setCookies", {"cookies": cookies})
    send("Emulation.setDeviceMetricsOverride", {
        "width": 1280, "height": 1800, "deviceScaleFactor": 1, "mobile": False,
    })

    # Navigate, click overlay-occluded element via JS, screenshot
    send("Page.navigate", {"url": "https://www.instacart.com/store/<route>"})
    time.sleep(20)
    evaljs("document.querySelector('[data-testid=\"floating-cart-button\"]').click()")
    time.sleep(6)
    snap("cart-drawer")

    ws.close()
finally:
    chrome.terminate(); chrome.wait(timeout=5)
```

Drop this in `/home/bento/.claude/jobs/<job-id>/tmp/<audit-slug>-capture.py`. Don't pollute the skill directory.

## Localhost fallback

Use only when prod cookies can't reach the state (rare). Localhost = `http://www.instacart.com.test:8081/`.

Localhost gives you the **`feature_overrides` cookie** for FV flips without going through Roulette console:

```
feature_overrides=<fv_name>.visible.true,<fv_name>.variant.<value>
```

Stack multiple overrides with commas. The header `X-Feature-Overrides: …` takes precedence over the cookie. Dev allows these unconditionally because `Rails.env.development?` short-circuits the override guard.

Localhost ALSO requires data — `maki sync` populates some tables but skips others (notably `partnership_offers` — use `maki load customers-express` for that). If a localhost capture renders blank, the data is probably missing.

## Cropping

Default capture is 1280×1800. Crop down to just the placement:

```bash
# ImageMagick — region is +X+Y WxH from top-left
convert /home/bento/snap/chromium/common/screenshots/<full>.png \
        -crop 800x400+200+1200 +repage \
        /home/bento/snap/chromium/common/screenshots/<row-id>.png
```

Eyeball the full screenshot first to get coordinates, or use a probe script that returns `getBoundingClientRect()` of the target element and crop programmatically.

## When prod is the wrong target

Some surfaces only exist behind a closed-experiment FV or only render in QA environments. Document these in the audit's Methodology section with the specific reason — don't try to spoof them in prod and don't silently default to localhost.

## What NOT to do

- **Don't ship uncropped screenshots.** A 1280×1800 page-level shot in a Google Doc table is unreadable. Always crop.
- **Don't fake a state by editing the DOM.** If the surface won't render, mock it in a labeled HTML page or describe it; never inject markup into the live page and call that a screenshot of the placement.
- **Don't reuse a similar-looking screenshot from another cohort.** Each row's screenshot must be from a session with that row's actual cohort state.
- **Don't bento restart the store/proxy mid-capture.** It triggers an interactive Okta device re-auth that hangs headless. If a dev server is wedged, surface it to the user instead of trying to fix it inline.
