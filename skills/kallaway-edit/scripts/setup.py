#!/usr/bin/env python3
"""First-time setup, the tool check, and the project folders. Safe to run again any time (it only
fixes what is missing and never touches the user's files).

Usage (VIDEO_EDITOR_DATA = the editor's data folder; the skill passes ${CLAUDE_PLUGIN_DATA}):
  VIDEO_EDITOR_DATA="<data>" python3 -I "<skill>/scripts/setup.py" --check [--for new-edit-style]
      Report only: what is installed and what is missing, with the fix for each. Installs nothing.
      yt-dlp (downloads reels from links) is optional for editing; --for new-edit-style makes it required.
  VIDEO_EDITOR_DATA="<data>" python3 -I "<skill>/scripts/setup.py" --project "<folder>" [--clips-from "<folder>"] [--music on|off]
      Create the project folders (raw/ references/ exports/ work/ archive/, only the missing ones)
      and save where the user's videos live in config.json. Installs nothing.
  VIDEO_EDITOR_DATA="<data>" python3 -I "<skill>/scripts/setup.py"
      The full install (~5 minutes the first time).

Checks: macOS, ffmpeg + ffprobe, Node 22+, Python 3.10+, disk space, HyperFrames.
Installs into the editor's DATA folder only (see state.py), never into the skill folder, so a plugin
update never wipes the user's setup, and nothing global:
  venv/             Python packages: faster-whisper (free local transcription), numpy, pillow
  config.json       the user's folders and choices (no secrets, ever)
  sfx/              the recorded sound effects, copied from HyperFrames' media-use skill (or its
                    GitHub repo). Pixabay licence: fine inside your videos, never re-shared as files.
Warms up: the HyperFrames CLI through npx (pinned), its headless Chrome, the Whisper model.
It never runs `npx hyperframes init` or `npx hyperframes skills` (those copy skills into
~/.claude/skills); every HyperFrames call is made with HYPERFRAMES_SKIP_SKILLS=1.
"""
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import state  # noqa: E402  where the user's settings, venv and sound effects live (never in SK)

sys.stdout.reconfigure(line_buffering=True)  # progress lines arrive in order, even when logged to a file
SK = state.SK
CONFIG = state.CONFIG
PIN = state.PIN
ENV = dict(state.HF_ENV, VIDEO_EDITOR_DATA=str(state.DATA))  # children resolve the same DATA folder
FOLDERS = {
    "raw": "your clips go here (copies; your originals are never touched)",
    "references": "videos whose editing style you like",
    "exports": "finished reels land here",
    "work": "the editor's working files, one folder per reel",
    "archive": "older versions, kept instead of deleted",
}
COMMAND = (f"/video-editor:{SK.name}" if (SK.parent.parent / ".claude-plugin" / "plugin.json").exists()
           else f"/{SK.name}")  # how the user runs this skill (plugin skills carry the plugin's name)
ok = True


def say(good, msg, fix=""):
    global ok
    print(("  OK   " if good else "  MISSING  ") + msg + ("" if good else f"\n         -> {fix}"))
    ok = ok and good


def version(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        return ""


load_config = state.load_config
save_config = state.save_config


def check_tools():
    say(platform.system() == "Darwin", "macOS", "This skill is built for a Mac.")
    say(bool(shutil.which("ffmpeg")) and bool(shutil.which("ffprobe")), "ffmpeg (cuts and sound)",
        "Install Homebrew from https://brew.sh, then run: brew install ffmpeg")
    nv = version(["node", "--version"]).lstrip("v")
    say(bool(nv) and int(nv.split(".")[0]) >= 22, f"Node.js 22 or newer (found {nv or 'none'})",
        "Install it from https://nodejs.org (the LTS button), or: brew install node")
    say(sys.version_info >= (3, 10), f"Python 3.10+ (found {platform.python_version()})",
        "brew install python")
    free = shutil.disk_usage(state.DATA).free / 1e9
    say(free > 8, f"Free disk space ({free:.0f} GB; a run needs ~5 GB while it works)",
        "Free up some space before editing.")


def check_ytdlp(required):
    """yt-dlp downloads reels from links: required to build a new style, optional for editing."""
    global ok
    has = bool(shutil.which("yt-dlp"))
    fix = "brew install yt-dlp"
    if required:
        say(has, "yt-dlp (downloads the reference reels from their links)", fix)
    elif has:
        say(True, "yt-dlp (optional: downloads reels from links)")
    else:
        print(f"  OPTIONAL  yt-dlp (downloads reels from links; not needed to edit your own clips)\n         -> {fix}")


def check_only(for_skill=None):
    """Report what is there without installing anything. Exit 0 when ready to edit."""
    print("Checking your Mac for the free tools this editor needs:\n")
    check_tools()
    check_ytdlp(required=(for_skill == "new-edit-style"))
    py = state.PY
    has_whisper = py.exists() and subprocess.run([str(py), "-I", "-c", "import faster_whisper"],
                                                 capture_output=True).returncode == 0
    say(has_whisper, "Transcription engine (faster-whisper)", "The full setup installs it (no action from you).")
    v = ""
    if shutil.which("npx"):
        v = subprocess.run(["npx", "--no-install", f"hyperframes@{PIN}", "--version"], capture_output=True,
                           text=True, env=ENV, timeout=60).stdout.strip()
    say(v == PIN, f"HyperFrames {PIN} (renders the video)", "The full setup downloads it (no action from you).")
    sfx = state.SFX
    say(sfx.is_dir() and any(sfx.glob("*.mp3")), "Sound effects", "The full setup fetches them (no action from you).")
    cfg = load_config()
    root = cfg.get("projectRoot")
    say(bool(root) and Path(root).is_dir(), f"Project folder ({root or 'not chosen yet'})",
        "The setup wizard asks where your videos should live.")
    print(f"\nThe editor's own files (settings, Python, sound effects) live in: {state.DATA}")
    print("\nREADY" if ok else "\nNOT READY")
    sys.exit(0 if ok else 1)


def init_project(root, clips_from, music):
    root = Path(os.path.expanduser(root)).resolve()
    root.mkdir(parents=True, exist_ok=True)
    print(f"Project folder: {root}\n")
    for name, what in FOLDERS.items():
        made = not (root / name).exists()
        (root / name).mkdir(exist_ok=True)
        print(f"  {'made ' if made else 'kept '} {name + '/':12} {what}")
    cfg = save_config(projectRoot=str(root), music=music)
    if clips_from:  # no --clips-from means "I'll drop clips into raw/ myself"
        cfg = save_config(clipsFrom=str(Path(os.path.expanduser(clips_from)).resolve()))
    elif cfg.pop("clipsFrom", None):
        CONFIG.write_text(json.dumps(cfg, indent=1))
    print(f"\nSaved: videos live in {cfg['projectRoot']}"
          + (f", new footage usually lands in {cfg['clipsFrom']}" if cfg.get("clipsFrom") else "")
          + f", background music {cfg.get('music', 'on')}.")


def install():
    print("Checking your Mac for the free tools this editor needs:\n")
    check_tools()
    check_ytdlp(required=False)
    if not ok:
        print("\nFix the items above, then run this again.")
        sys.exit(1)

    py = state.PY
    print(f"\nThe editor keeps its own files in {state.DATA} (updates never touch it).")
    if not py.exists() or subprocess.run([str(py), "-c", "pass"], capture_output=True).returncode:
        # missing, or broken because the Mac's Python it was made from changed: (re)make it
        print("\nSetting up the editor's own Python folder (one time, ~1 minute) ...")
        subprocess.run([sys.executable, "-m", "venv", "--clear", str(state.VENV)], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "-q", "faster-whisper>=1.1", "numpy", "pillow"],
                   check=True)
    say(True, "Transcription engine (faster-whisper) in the editor's own Python folder")

    save_config(hyperframes=PIN)
    v = subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "--version"], capture_output=True, text=True,
                       env=ENV).stdout.strip()
    say(v == PIN, f"HyperFrames {PIN} (renders the video)", "Check your internet connection and rerun.")
    print("  ...  making sure HyperFrames has its headless Chrome (first time downloads ~150 MB)")
    subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "browser", "ensure"], env=ENV,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # the recorded sound effects come from HyperFrames' media-use kit, never bundled here
    subprocess.run([str(py), "-I", str(SK / "scripts" / "sounds.py")], check=True, env=ENV)
    say(True, "Sound effects (recorded, Pixabay licence, fetched from HyperFrames media-use)")

    print("  ...  downloading the speech model (first time only, ~1.5 GB) ...")
    subprocess.run([str(py), "-I", "-c",
                    "from faster_whisper import WhisperModel; WhisperModel('medium.en', device='cpu', "
                    "compute_type='int8')"], check=True, env=ENV)
    say(True, "Speech model medium.en")
    save_config(setupComplete=bool(load_config().get("projectRoot")),
                setupDate=datetime.date.today().isoformat())
    print(f"\nAll set. Drop your raw clips in raw/ and run {COMMAND}.")


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_only(arg("--for"))
    elif "--project" in sys.argv:
        init_project(arg("--project"), arg("--clips-from"), arg("--music"))
    else:
        install()
