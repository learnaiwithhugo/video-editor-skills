#!/usr/bin/env python3
"""The setup wizard's helper: tool check, the style folder, and (only when the person says yes) the one
install this skill does itself. Standard library only. Safe to run again any time.

Usage:
  python3 -I setup.py --check
      Report what's installed and what's missing, each with a one-line fix. Installs nothing.
  python3 -I setup.py --init "<style folder>"
      Make (or refresh) the style folder: STYLE.md later, locked/ sfx/ page/ reviews/ references/.
      Copies the page engine in. Existing choices (round.json, custom.js, assets, locks) are never overwritten.
  python3 -I setup.py --install-hyperframes
      Downloads the pinned HyperFrames video renderer and its headless Chrome through npx (~150 MB).
      Only run this after the person agreed. Nothing goes into ~/.claude/skills.

Remembers the style folder in config.json next to this skill, so later sessions can find it.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
ENGINE = SK / "engine"
CONFIG = SK / "config.json"
PIN = "0.8.186"   # same HyperFrames version edit-my-video uses
ENV = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1", HYPERFRAMES_NO_TELEMETRY="1")
ok = True
# Engine files that get refreshed on --init. Everything else in page/ belongs to the person.
ENGINE_FILES = ["library.js", "app.js", "boot.js", "style.css", "index.html", "shine.html", "zoom.html", "shadow.html", "sfx.html"]


def say(good, msg, fix=""):
    global ok
    print(("  OK       " if good else "  MISSING  ") + msg + ("" if good else f"\n           fix: {fix}"))
    ok = ok and good


def out(cmd, timeout=60, env=None):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def find_chrome():
    for p in [os.environ.get("CHROME", ""), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]:
        if p and Path(p).exists():
            return p
    cache = Path.home() / ".cache" / "puppeteer"
    for exe in sorted(cache.glob("chrome-headless-shell/*/*/chrome-headless-shell"), reverse=True):
        return str(exe)
    for exe in sorted(cache.glob("chrome/*/*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"), reverse=True):
        return str(exe)
    return ""


def config(**changes):
    cfg = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    if changes:
        cfg.update(changes)
        CONFIG.write_text(json.dumps(cfg, indent=1))
    return cfg


def check():
    print("Checking your Mac for the free tools Style Studio needs:\n")
    say(platform.system() == "Darwin", "macOS", "This skill is built for a Mac.")
    say(bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe")), "ffmpeg (cuts clips, makes previews)",
        "install Homebrew from https://brew.sh, then in Terminal: brew install ffmpeg")
    nv = out(["node", "--version"]).lstrip("v")
    say(bool(nv) and int(nv.split(".")[0]) >= 22, f"Node.js 22 or newer (found {nv or 'none'}): screenshots and the video renderer",
        "download the LTS installer from https://nodejs.org, or in Terminal: brew install node")
    say(sys.version_info >= (3, 9), f"Python 3.9+ (found {platform.python_version()}): runs the page", "in Terminal: brew install python")
    say(bool(shutil.which("yt-dlp")), "yt-dlp (downloads your reference videos, logged out)", "in Terminal: brew install yt-dlp")
    chrome = find_chrome()
    say(bool(chrome), "A Chrome browser (takes real website screenshots)",
        "install Google Chrome from https://www.google.com/chrome, or say yes when I offer to install HyperFrames")
    hv = out(["npx", "--no-install", f"hyperframes@{PIN}", "--version"], timeout=60, env=ENV) if shutil.which("npx") else ""
    say(hv == PIN, f"HyperFrames {PIN} (renders your edits later, not needed to build the style)",
        "I can install it for you (one command, about 2 minutes). Just say yes.")
    free = shutil.disk_usage(Path.home()).free / 1e9
    say(free > 3, f"Free disk space ({free:.0f} GB)", "free up a few GB first.")
    cfg = config()
    if cfg.get("styleDir"):
        print(f"\n  Your style folder: {cfg['styleDir']}")
    print("\nREADY" if ok else "\nNOT READY")
    return 0 if ok else 1


def init(style):
    style = Path(os.path.expanduser(style)).resolve()
    made = not style.exists()
    for sub in ["locked/old", "sfx/old", "reviews", "references/analysis", "page/assets/icons", "page/rounds"]:
        (style / sub).mkdir(parents=True, exist_ok=True)
    for f in ENGINE_FILES:   # refresh the engine, keep the person's own files
        shutil.copy2(ENGINE / "page" / f, style / "page" / f)
    if not (style / "page" / "custom.js").exists():
        shutil.copy2(ENGINE / "page" / "custom.js", style / "page" / "custom.js")
    shutil.copy2(ENGINE / "serve.py", style / "serve.py")
    if not (style / "sfx" / "sfx.json").exists():
        (style / "sfx" / "sfx.json").write_text("[]\n")
    config(styleDir=str(style))
    print(f"{'Made' if made else 'Refreshed'} your style folder: {style}")
    for sub, what in [("STYLE.md", "your style guide (written as we go)"), ("locked/", "settings you lock"),
                      ("sfx/", "your sound effects"), ("page/", "the style page"), ("reviews/", "your Keep / Maybe / Drop marks"),
                      ("references/", "videos you love and what we learned from them")]:
        print(f"  {sub:13} {what}")


def install_hyperframes():
    if not shutil.which("npx"):
        raise SystemExit("Node.js is missing. Install it first (https://nodejs.org).")
    print(f"Installing HyperFrames {PIN} (the free video renderer) ...", flush=True)
    v = out(["npx", "-y", f"hyperframes@{PIN}", "--version"], timeout=600, env=ENV)
    print("  OK" if v == PIN else "  failed: check the internet connection and try again")
    print("Making sure it has its headless Chrome (first time ~150 MB) ...", flush=True)
    subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "browser", "ensure"], env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Done.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--check" in a:
        sys.exit(check())
    elif "--init" in a:
        init(a[a.index("--init") + 1])
    elif "--install-hyperframes" in a:
        install_hyperframes()
    else:
        print(__doc__)
