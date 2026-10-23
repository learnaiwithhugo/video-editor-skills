#!/usr/bin/env python3
"""Get real pictures: storyboard stills, fully-loaded web pages, real app icons, footage frames.

Usage:
  python3 shoot.py html  <still.html> <out.jpg> [<still2.html> <out2.jpg> ...]
        screenshot 1080x1920 storyboard stills (waits for fonts + images), saved as JPG (fast page)
  python3 shoot.py web   <url> <out.png> [--mobile] [--height 1800] [--wait 2500]
        a real page after it has FULLY loaded (network idle, lazy images scrolled in, no grey placeholder bars)
        --mobile = iPhone width rendered at 1080 px wide (best for the top half of a split screen)
  python3 shoot.py icon  "<App name or /Applications/X.app>" <out.png>
        the real macOS app icon, via sips (1024 px PNG with transparency)
  python3 shoot.py frame <video> <seconds> <out.jpg>
        one frame of footage (storyboard backgrounds)
"""
import plistlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHROME  # noqa: E402


def browser(p):
    try:
        return p.chromium.launch(executable_path=CHROME, args=["--hide-scrollbars"]) if Path(CHROME).exists() \
            else p.chromium.launch(args=["--hide-scrollbars"])
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Couldn't start Chrome for screenshots ({e}). Install Google Chrome, or run setup.py --install.")


def html(pairs):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    errs = []
    with sync_playwright() as p:
        b = browser(p)
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        for src, out in pairs:
            pg.goto("file://" + str(Path(src).resolve()))
            pg.evaluate("document.fonts.ready")
            pg.wait_for_function("[...document.images].every(i => i.complete)", timeout=15000)
            pg.wait_for_timeout(250)
            tmp = Path(out).with_suffix(".tmp.png")
            pg.screenshot(path=str(tmp))
            Image.open(tmp).convert("RGB").save(out, "JPEG", quality=84, optimize=True, progressive=True)
            tmp.unlink()
            print("  ", out)
        b.close()
    if errs:
        print("console errors:", *errs, sep="\n  ")


def web(url, out, mobile, height, wait):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = browser(p)
        if mobile:
            ctx = b.new_context(viewport={"width": 412, "height": height}, device_scale_factor=1080 / 412, is_mobile=True, has_touch=True,
                                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
        else:
            ctx = b.new_context(viewport={"width": 1280, "height": height}, device_scale_factor=2)
        pg = ctx.new_page()
        pg.goto(url, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(wait)
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        pg.wait_for_timeout(1200)
        pg.evaluate("window.scrollTo(0, 0)")
        pg.wait_for_function("[...document.images].filter(i => i.getBoundingClientRect().top < innerHeight).every(i => i.complete)",
                             timeout=20000)
        pg.wait_for_timeout(800)
        pg.screenshot(path=out)
        print(f"  {out}  ({pg.url})")
        b.close()


def icon(app, out):
    a = Path(app) if app.endswith(".app") else Path("/Applications") / f"{app}.app"
    if not a.exists():
        hits = list(Path("/Applications").glob(f"*{app}*.app"))
        if not hits:
            sys.exit(f"No app called {app} in /Applications. Use the tool's official logo from its website instead.")
        a = hits[0]
    info = plistlib.loads((a / "Contents" / "Info.plist").read_bytes())
    name = info.get("CFBundleIconFile") or "AppIcon"
    icns = a / "Contents" / "Resources" / (name if name.endswith(".icns") else name + ".icns")
    if not icns.exists():
        icns = next((a / "Contents" / "Resources").glob("*.icns"), None)
    if not icns:
        sys.exit(f"{a.name} has no .icns icon file; use its official logo instead.")
    subprocess.run(["sips", "-s", "format", "png", "-Z", "1024", str(icns), "--out", out], check=True, capture_output=True)
    print(f"  {out}  (from {icns})")


def frame(video, t, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", "-q:v", "3", out], check=True)
    print("  ", out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "html":
        html(list(zip(a[1::2], a[2::2])))
    elif a[0] == "web":
        h = int(a[a.index("--height") + 1]) if "--height" in a else 1800
        w = int(a[a.index("--wait") + 1]) if "--wait" in a else 2500
        web(a[1], a[2], "--mobile" in a, h, w)
    elif a[0] == "icon":
        icon(a[1], a[2])
    elif a[0] == "frame":
        frame(a[1], a[2], a[3])
    else:
        sys.exit(__doc__)
