#!/usr/bin/env python3
"""Capture one render state across web/iOS/Android viewports via headless Chrome (CDP).

Drives snap-chromium over the DevTools Protocol (the path that works on the bento box,
where agent-browser hangs on snap apparmor). Loads the user's auth cookies, optionally
sets an ic_debug_toggles gate, then for each device profile emulates the viewport,
navigates, measures the offers section, and screenshots the full page.

Outputs MUST land under ~/snap/chromium/common/ — snap apparmor blocks writes elsewhere.

Usage:
  capture.py --url URL --out-prefix PREFIX [--toggle k1,k2 | --no-toggle]
             [--platforms web,ios,android] [--settle 8] [--port 9347]
             [--heading-re 'member exclusive|partner|offer|reward|perks']

Produces PREFIX-web.png, PREFIX-ios.png, PREFIX-android.png in --out-dir.
Prints a one-line layout measurement per platform so the caller can confirm the
state actually changed (e.g. display:flex vs display:grid) without seeing the image.
"""
import argparse, base64, json, subprocess, time, urllib.request
from urllib.parse import quote
from websocket import create_connection

DESKTOP_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
ANDROID_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36")

# name -> (width, height, deviceScaleFactor, mobile, userAgent). Heights are tall so
# captureBeyondViewport grabs the whole section.
PROFILES = {
    "web":     (1280, 1600, 1,     False, DESKTOP_UA),
    "ios":     (390,  1400, 3,     True,  IOS_UA),
    "android": (412,  1400, 2.625, True,  ANDROID_UA),
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--out-prefix", required=True)
    p.add_argument("--out-dir", default="/home/bento/snap/chromium/common/screenshots")
    p.add_argument("--cookie-file", default="/home/bento/snap/chromium/common/screenshots/ic-cookies.txt")
    p.add_argument("--domain", default="www.instacart.com.test")
    p.add_argument("--toggle", default="", help="comma-separated ic_debug_toggles keys to set true")
    p.add_argument("--no-toggle", action="store_true", help="explicitly clear ic_debug_toggles (control state)")
    p.add_argument("--platforms", default="web,ios,android")
    p.add_argument("--settle", type=float, default=8.0, help="seconds to wait after load for hydration")
    p.add_argument("--port", type=int, default=9347)
    p.add_argument("--heading-re", default="member exclusive|partner|offer|reward|perks")
    return p.parse_args()


def build_cookies(args):
    with open(args.cookie_file) as f:
        header = f.read().strip()
    cookies = []
    for part in header.split("; "):
        if "=" in part:
            n, v = part.split("=", 1)
            cookies.append({"name": n, "value": v, "domain": args.domain, "path": "/"})
    keys = [k.strip() for k in args.toggle.split(",") if k.strip()]
    if keys:
        val = quote(json.dumps({k: True for k in keys}))
        cookies.append({"name": "ic_debug_toggles", "value": val, "domain": args.domain, "path": "/"})
    elif args.no_toggle:
        # explicitly empty so a previously-set toggle can't leak into the control shot
        cookies.append({"name": "ic_debug_toggles", "value": "", "domain": args.domain, "path": "/"})
    return cookies


def main():
    args = parse_args()
    cookies = build_cookies(args)
    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    measure_js = """
      (()=>{
        const re = new RegExp(%s, 'i');
        const hs = Array.from(document.querySelectorAll('h2'));
        const h = hs.find(el => re.test(el.textContent||''));
        if(!h) return JSON.stringify({err:'no heading', h2s: hs.map(x=>(x.textContent||'').trim()).slice(0,8)});
        const cc = h.parentElement.children[1];
        if(!cc) return JSON.stringify({err:'no container', heading:(h.textContent||'').trim()});
        const cs = getComputedStyle(cc);
        const first = cc.children[0] ? cc.children[0].getBoundingClientRect() : {width:0,left:0,right:0};
        return JSON.stringify({heading:(h.textContent||'').trim(), display:cs.display,
          grid:cs.gridTemplateColumns, gap:cs.gap, flexDir:cs.flexDirection,
          cards:cc.children.length, cardW:Math.round(first.width), cardL:Math.round(first.left)});
      })()
    """ % json.dumps(args.heading_re)

    chrome = subprocess.Popen([
        "chromium", "--headless=new", "--disable-gpu", "--no-sandbox",
        f"--user-data-dir=/home/bento/snap/chromium/common/cdp-data-{args.port}",
        "--window-size=1400,1600", f"--remote-debugging-port={args.port}",
        "--remote-allow-origins=*", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        for _ in range(30):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{args.port}/json/version", timeout=1); break
            except Exception:
                time.sleep(0.5)
        targets = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{args.port}/json").read())
        page = [t for t in targets if t.get("type") == "page"][0]
        ws = create_connection(page["webSocketDebuggerUrl"])
        msg_id = [0]

        def send(method, params=None):
            msg_id[0] += 1
            ws.send(json.dumps({"id": msg_id[0], "method": method, "params": params or {}}))
            while True:
                r = json.loads(ws.recv())
                if r.get("id") == msg_id[0]:
                    return r

        def wait_load(timeout=30):
            ws.settimeout(0.2); end = time.time() + timeout
            try:
                while time.time() < end:
                    try:
                        m = json.loads(ws.recv())
                        if m.get("method") == "Page.loadEventFired":
                            return True
                    except Exception:
                        pass
            finally:
                ws.settimeout(None)
            return False

        send("Network.enable"); send("Page.enable")
        send("Network.clearBrowserCookies")
        send("Network.setCookies", {"cookies": cookies})

        for name in platforms:
            if name not in PROFILES:
                print(f"  !! unknown platform {name}, skipping"); continue
            w, h, dsf, mobile, ua = PROFILES[name]
            print(f"=== {args.out_prefix} {name} {w}px ===")
            send("Network.setUserAgentOverride", {"userAgent": ua})
            send("Emulation.setDeviceMetricsOverride",
                 {"width": w, "height": h, "deviceScaleFactor": dsf, "mobile": mobile})
            send("Page.navigate", {"url": "about:blank"}); wait_load(5)
            send("Page.navigate", {"url": args.url}); wait_load(30); time.sleep(args.settle)
            m = send("Runtime.evaluate", {"expression": measure_js})
            print("   layout:", m.get("result", {}).get("result", {}).get("value", "?"))
            # nudge the section into view in case lazy content needs it
            send("Runtime.evaluate", {"expression":
                "const h=Array.from(document.querySelectorAll('h2')).find(e=>new RegExp(%s,'i').test(e.textContent||''));if(h)h.scrollIntoView({block:'start'});"
                % json.dumps(args.heading_re)})
            time.sleep(1)
            shot = send("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
            if "result" in shot:
                out = f"{args.out_dir}/{args.out_prefix}-{name}.png"
                with open(out, "wb") as f:
                    f.write(base64.b64decode(shot["result"]["data"]))
                print(f"   saved {out}")
            else:
                print(f"   !! capture failed: {shot}")
        ws.close()
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=5)
        except Exception:
            chrome.kill()


if __name__ == "__main__":
    main()
