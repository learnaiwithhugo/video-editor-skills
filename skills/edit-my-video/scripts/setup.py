#!/usr/bin/env python3
"""Setup check for edit-my-video. Installs nothing unless asked (--install), and only after the user said yes.

Usage:
  python3 setup.py --check                       what's there, what's missing, the plain-English fix for each
  python3 setup.py --save --style "<style folder>" --edits "<folder for edits>"
                                                  remember where the style and the edits live (config.json)
  python3 setup.py --install                      the missing free pieces: faster-whisper + playwright (pip, user
                                                  install), HyperFrames (npx cache) and its headless browser
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHROME, DEFAULT_STYLE, HF_ENV, PIN, built_style_dir, load_config, save_config  # noqa: E402

ok = True


def say(good, what, why, fix=""):
    global ok
    print(f"  {'OK     ' if good else 'MISSING'}  {what:28} {why}" + ("" if good else f"\n           -> {fix}"))
    ok = ok and good


def have_py(mod):
    return subprocess.run([sys.executable, "-c", f"import {mod}"], capture_output=True).returncode == 0


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
        v = subprocess.run(["npx", "--no-install", f"hyperframes@{PIN}", "--version"], capture_output=True, text=True,
                           env=HF_ENV, timeout=90).stdout.strip()
    say(v == PIN, f"HyperFrames {PIN}", "turns the edit into the video", "setup.py --install does it")
    free = shutil.disk_usage(Path.home()).free / 1e9
    say(free > 5, f"Disk space ({free:.0f} GB free)", "an edit needs ~2-5 GB while it works", "Free up some space first.")
    cfg = load_config()
    print(f"\n  style folder: {cfg.get('style_dir') or built_style_dir() or f'(not saved yet: default {DEFAULT_STYLE})'}")
    print(f"  edits go in:  {cfg.get('edits_dir') or '(not saved yet)'}")
    print("\nREADY" if ok else "\nNOT READY")
    return ok


def install():
    print("Installing the free pieces (one time, a few minutes):")
    if not have_py("faster_whisper") or not have_py("playwright") or not have_py("PIL"):
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "-q", "faster-whisper>=1.1", "playwright", "pillow", "numpy"], check=True)
    print("  ... HyperFrames (downloads once into the npx cache)")
    subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "--version"], env=HF_ENV, check=True, capture_output=True)
    subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "browser", "ensure"], env=HF_ENV, capture_output=True)
    print("  ... speech model (first time ~500 MB)")
    subprocess.run([sys.executable, "-c", "from faster_whisper import WhisperModel; WhisperModel('small.en', device='cpu', compute_type='int8')"],
                   check=True)
    print("Done.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--install" in a:
        install()
    if "--save" in a:
        g = lambda k: os.path.abspath(os.path.expanduser(a[a.index(k) + 1])) if k in a else None  # noqa: E731
        cfg = save_config(style_dir=g("--style"), edits_dir=g("--edits"))
        print("saved:", cfg)
    if "--check" in a or not a:
        sys.exit(0 if check() else 1)
