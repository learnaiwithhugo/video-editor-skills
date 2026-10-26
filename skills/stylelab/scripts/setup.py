#!/usr/bin/env python3
"""The setup wizard's helper: tool check, the style folder, and (only when the person says yes) the one
install this skill does itself. Standard library only. Safe to run again any time.

Usage:
  python3 -I setup.py --check
      Report what's installed and what's missing, each with a one-line fix. Installs nothing.
  python3 -I setup.py --init "<style folder>"
      Make (or refresh) the style folder: STYLE.md later, locked/ sfx/ page/ reviews/ references/.
      Copies the page engine in (every file in engine/page/, so new page files arrive too). Existing choices
      (round.json, custom.js, assets, locks) are never overwritten. The page is published as a Claude artifact
      from this folder, so it should sit inside the folder Claude Code was opened in (suggested: ./my-style);
      otherwise a plain warning says so.
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
PIN = "0.8.185"   # same HyperFrames version the editing skills use
ENV = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1", HYPERFRAMES_NO_TELEMETRY="1")
ok = True
# Everything in engine/page/ is refreshed on --init, EXCEPT custom.js (the person's own animations, copied only when
# missing). Everything else in the style folder's page/ (round.json, assets/, ...) belongs to the person.
KEEP_MINE = {"custom.js"}


def say(good, msg, fix="", optional=False):
    """One row of the table. An optional tool that's missing is shown but never makes the result NOT READY."""
    global ok
    print(("  OK       " if good else "  LATER    " if optional else "  MISSING  ") + msg + ("" if good else f"\n           fix: {fix}"))
    ok = ok and (good or optional)


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
    print("Checking your Mac for the free tools StyleLab needs:\n")
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
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from make_assets import cutout_tools   # the same test the cut-out step itself runs
    can_cut, why = cutout_tools()
    say(can_cut, "Head cut-out tools (lets words sit behind your head; the style works without it)", why, optional=True)
    hv = out(["npx", "--no-install", f"hyperframes@{PIN}", "--version"], timeout=60, env=ENV) if shutil.which("npx") else ""
    say(hv == PIN, f"HyperFrames {PIN} (renders your edits later, not needed to build the style)",
        "I can install it for you (one command, about 2 minutes). Just say yes.", optional=True)
    free = shutil.disk_usage(Path.home()).free / 1e9
    say(free > 3, f"Free disk space ({free:.0f} GB)", "free up a few GB first.")
    cfg = config()
    if cfg.get("styleDir"):
        print(f"\n  Your style folder: {cfg['styleDir']}")
    print("\nREADY" if ok else "\nNOT READY")
    return 0 if ok else 1


def outside_cwd_warning(style):
    """The Artifact tool only publishes files from the folder Claude Code was opened in."""
    cwd = Path.cwd().resolve()
    try:
        Path(style).resolve().relative_to(cwd)
        return ""
    except ValueError:
        return (f"HEADS UP: {style} is not inside the folder Claude Code was opened in ({cwd}). The style page is published "
                f"as a Claude artifact from this folder, and the Artifact tool can only publish files from the folder Claude Code "
                f"was opened in. Use a folder inside it (suggested: ./my-style), or open Claude Code in {Path(style).parent}.")


def copy_engine_page(dest):
    """Refresh every engine page file (not custom.js, the person's own) and report which ones were copied."""
    copied = []
    for src in sorted((ENGINE / "page").iterdir()):
        if src.name.startswith(".") or src.name in KEEP_MINE:
            continue
        if src.is_dir():
            shutil.copytree(src, dest / src.name, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dest / src.name)
        copied.append(src.name)
    return copied


def init(style):
    style = Path(os.path.expanduser(style)).resolve()
    made = not style.exists()
    for sub in ["locked/old", "sfx/old", "reviews", "references/analysis", "page/assets/icons", "page/assets/photos", "page/rounds",
                "images/liked", "images/disliked", "notes"]:
        (style / sub).mkdir(parents=True, exist_ok=True)
    copy_engine_page(style / "page")   # refresh the engine, keep the person's own files
    if not (style / "page" / "custom.js").exists():
        shutil.copy2(ENGINE / "page" / "custom.js", style / "page" / "custom.js")
    shutil.copy2(ENGINE / "serve.py", style / "serve.py")
    # serve.py records Like / Nope clicks with the same function the scripts use: keep a copy beside it.
    shutil.copy2(Path(__file__).resolve().parent / "images.py", style / "images_lib.py")
    if not (style / "sfx" / "sfx.json").exists():
        (style / "sfx" / "sfx.json").write_text("[]\n")
    words = style / "notes" / "their-words.md"
    if not words.exists():   # everything they say they like or hate, word for word, dated (STYLE.md only gets what's decided)
        words.write_text("# In your own words\n\nEverything you've said you like or don't like, word for word.\n")
    config(styleDir=str(style))
    print(f"{'Made' if made else 'Refreshed'} your style folder: {style}")
    for sub, what in [("STYLE.md", "your style guide (written as we go)"), ("locked/", "settings you lock"),
                      ("sfx/", "your sound effects"), ("page/", "the style page (published as your Claude artifact)"),
                      ("reviews/", "your Keep / Maybe / Drop marks"),
                      ("references/", "videos you love and what we learned from them"),
                      ("images/", "photos you like and don't (your image taste)"), ("notes/", "what you've told me, word for word")]:
        print(f"  {sub:13} {what}")
    warn = outside_cwd_warning(style)
    if warn:
        print("\n" + warn)


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
