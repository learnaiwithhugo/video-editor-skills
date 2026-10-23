"""Shared helpers for the edit-my-video scripts. Nothing here touches the user's original footage."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parent.parent          # the skill folder
ENGINE = SK / "engine"
CONFIG = SK / "config.json"
PIN = "0.8.186"                                       # HyperFrames version the test edits rendered with
HF_ENV = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1", HYPERFRAMES_NO_TELEMETRY="1")
DEFAULT_STYLE = Path.home() / "edit-style"                # build-my-style suggests this folder too
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H, FPS = 1080, 1920, 30

# The Python helpers (faster-whisper, playwright, pillow) live in their own little folder, never in the Mac's
# own Python (Homebrew's Python refuses `pip install` there). setup.py --install makes it; every script
# imports this file first, so adding it to the path here makes the packages importable everywhere.
DATA = Path(os.environ.get("VIDEO_EDITOR_DATA") or Path.home() / ".claude-video-editor")
VENV = DATA / "edit-venv"


def use_venv():
    for sp in VENV.glob("lib/python%d.%d/site-packages" % sys.version_info[:2]):
        if str(sp) not in sys.path:
            sys.path.insert(0, str(sp))


use_venv()


def load_config():
    try:
        return json.loads(CONFIG.read_text())
    except (FileNotFoundError, ValueError):
        return {}


def save_config(**changes):
    cfg = load_config()
    cfg.update({k: v for k, v in changes.items() if v is not None})
    CONFIG.write_text(json.dumps(cfg, indent=1))
    return cfg


def built_style_dir():
    """The style folder build-my-style remembered (it sits next to this skill), if there is one."""
    try:
        return json.loads((SK.parent / "build-my-style" / "config.json").read_text()).get("styleDir")
    except (FileNotFoundError, ValueError):
        return None


def style_dir(arg=None):
    """The style folder: the one passed in, else the one saved at setup, else the one build-my-style made,
    else ~/edit-style."""
    p = Path(os.path.expanduser(arg)) if arg else Path(load_config().get("style_dir") or built_style_dir() or DEFAULT_STYLE)
    if not (p / "STYLE.md").exists():
        sys.exit(f"No STYLE.md in {p}. Point me at a style folder made by build-my-style.")
    return p.resolve()


def run(cmd, check=True, quiet=False, **kw):
    if not quiet:
        print("  $ " + " ".join(str(c) for c in cmd)[:220], flush=True)
    return subprocess.run([str(c) for c in cmd], check=check, **kw)


def ffprobe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBTP) via ffmpeg ebur128."""
    err = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[0-9.]+) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[0-9.]+) dBFS", tail)
    return (float(i.group(1)) if i else None, float(tp.group(1)) if tp else None)


def whisper_model(name="medium.en"):
    """faster-whisper, from the helpers folder setup.py --install made (see use_venv above)."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper isn't installed. Run: python3 scripts/setup.py --install")
    return WhisperModel(name, device="cpu", compute_type="int8")


def npx_hf(*args, cwd=None, check=True, capture=False):
    cmd = ["npx", "--yes", f"hyperframes@{PIN}", *args]
    print("  $ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, env=HF_ENV, check=check, capture_output=capture, text=True)


def jdump(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def jload(path):
    return json.loads(Path(path).read_text())


def copy_if_newer(src, dst):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or Path(src).stat().st_mtime > dst.stat().st_mtime:
        shutil.copy2(src, dst)
    return dst
