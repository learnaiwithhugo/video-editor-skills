#!/usr/bin/env python3
"""Setup check for edit-my-video. Installs nothing unless asked (--install), and only after the user said yes.

Usage:
  python3 setup.py --check                       what's there, what's missing, the plain-English fix for each
  python3 setup.py --save --style "<style folder>" --edits "<folder for edits>"
                                                  remember where the style and the edits live (config.json)
  python3 setup.py --install                      the missing free pieces: faster-whisper + playwright + pillow
                                                  (into their own folder, never the Mac's Python),
                                                  HyperFrames (npx cache) and its headless browser
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
from common import CHROME, DEFAULT_STYLE, HF_ENV, PIN, VENV, built_style_dir, load_config, save_config  # noqa: E402

ok = True


def say(good, what, why, fix=""):
    global ok
    print(f"  {'OK     ' if good else 'MISSING'}  {what:28} {why}" + ("" if good else f"\n           -> {fix}"))
    ok = ok and good


def have_py(mod):
    import importlib
    importlib.invalidate_caches()
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


def check():
    print("Checking the free tools this editor needs:\n")
    say(platform.system() == "Darwin", "macOS", "this skill is built for a Mac", "Use a Mac.")
    say(bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), "ffmpeg", "cuts the clips and mixes the sound",
        "In Terminal: brew install ffmpeg   (no Homebrew? get it from https://brew.sh first)")
    nv = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip().lstrip("v") if shutil.which("node") else ""
    say(bool(nv) and int(nv.split(".")[0]) >= 22, f"Node.js 22+ ({nv or 'none'})", "runs HyperFrames",
        "Download the LTS from https://nodejs.org, or in Terminal: brew install node")
    say(sys.version_info >= (3, 10), f"Python 3.10+ ({platform.python_version()})", "runs the helper scripts", "brew install python")
    say(have_py("faster_whisper"), "faster-whisper", "hears every word (free, on your Mac)", "setup.py --install does it")
    say(have_py("playwright") and have_py("PIL"), "playwright + pillow", "takes screenshots of real pages and stills",
        "setup.py --install does it")
    say(Path(CHROME).exists(), "Google Chrome", "loads real websites fully for screenshots", "Install Chrome from google.com/chrome")
    v = ""
    if shutil.which("npx"):
        try:
            v = subprocess.run(["npx", "--no-install", f"hyperframes@{PIN}", "--version"], capture_output=True, text=True,
                               env=HF_ENV, timeout=90).stdout.strip()
        except subprocess.TimeoutExpired:
            pass
    say(v == PIN, f"HyperFrames {PIN}", "turns the edit into the video", "setup.py --install does it")
    free = shutil.disk_usage(Path.home()).free / 1e9
    say(free > 5, f"Disk space ({free:.0f} GB free)", "an edit needs ~2-5 GB while it works", "Free up some space first.")
    cfg = load_config()
    print(f"\n  style folder: {cfg.get('style_dir') or built_style_dir() or f'(not saved yet: default {DEFAULT_STYLE})'}")
    print(f"  edits go in:  {cfg.get('edits_dir') or '(not saved yet)'}")
    print("\nREADY" if ok else "\nNOT READY")
    return ok


def stop(msg):
    print("\n" + msg)
    sys.exit(1)


def install():
    if not (shutil.which("node") and shutil.which("npx")):
        stop("Node.js isn't installed yet, and the video renderer needs it. Install it first (the Node.js line in the check above), then run this again.")
    print("Installing the free pieces (one time, a few minutes):")
    if not (have_py("faster_whisper") and have_py("playwright") and have_py("PIL")):
        print("  ... Python helpers (faster-whisper, playwright, pillow) into their own folder: " + str(VENV))
        if not (VENV / "bin" / "python").exists() or not list(VENV.glob("lib/python%d.%d/site-packages" % sys.version_info[:2])):
            VENV.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, "-m", "venv", "--clear", str(VENV)], check=True)
        r = subprocess.run([str(VENV / "bin" / "python"), "-m", "pip", "install", "-q", "faster-whisper>=1.1", "av>=14,<19", "playwright", "pillow", "numpy"])  # av 19 breaks faster-whisper (metadata_errors)
        if r.returncode:
            stop("The Python helpers didn't install. Check the internet connection and run this again; if it keeps failing, tell me the error above.")
        common.use_venv()
        if not (have_py("faster_whisper") and have_py("playwright") and have_py("PIL")):
            stop("The Python helpers installed but I can't load them. Run this again.")
    print("  ... HyperFrames (downloads once into the npx cache)")
    r = subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "--version"], env=HF_ENV, capture_output=True)
    if r.returncode:
        stop("HyperFrames didn't download. Check the internet connection and run this again.")
    subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "browser", "ensure"], env=HF_ENV, capture_output=True)
    print("  ... speech model (first time ~500 MB)")
    try:
        from faster_whisper import WhisperModel
        WhisperModel("small.en", device="cpu", compute_type="int8")
    except Exception as e:  # noqa: BLE001
        stop(f"The speech model didn't download ({type(e).__name__}). Check the internet connection and run this again.")
    print("Done.")


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)   # show each install step as it happens
    a = sys.argv[1:]
    if "--install" in a:
        install()
    if "--save" in a:
        g = lambda k: os.path.abspath(os.path.expanduser(a[a.index(k) + 1])) if k in a else None  # noqa: E731
        cfg = save_config(style_dir=g("--style"), edits_dir=g("--edits"))
        print("saved:", cfg)
    if "--check" in a or not a:
        sys.exit(0 if check() else 1)
