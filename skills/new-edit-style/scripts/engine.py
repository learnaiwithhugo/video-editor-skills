"""Where the shared editing engine lives, and small helpers every script here uses.

The engine is the first style skill that was built and proven (kallaway-edit): its setup wizard,
transcription, take picking, cutting, cut-out, music, sound effects, build, render and QA scripts.
New style skills are cloned from it, so they inherit a working engine instead of starting from zero.

The user's own things (settings, the editor's Python, sound effects, the font cache) never live in a
skill folder: they live in the engine's DATA folder (see the engine's scripts/state.py), which plugin
updates never touch.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

_ME = Path(__file__).resolve()
HERE = next((p for p in _ME.parents if (p / "SKILL.md").exists()), _ME.parent.parent)  # this skill's folder
SKILLS = HERE.parent                                   # the skills folder it sits in (plugin or project)


def engine_dir(name=None) -> Path:
    """The engine skill: the one named (a name or a path), else this skill if it is one, else kallaway-edit
    next to it (in the plugin: ${CLAUDE_PLUGIN_ROOT}/skills/kallaway-edit), else any sibling *-edit skill."""
    is_engine = lambda p: (p / "scripts" / "build.py").exists() and (p / "scripts" / "setup.py").exists()  # noqa: E731
    name = name or os.environ.get("VIDEO_EDITOR_ENGINE")
    if name:
        cands = [Path(name).expanduser()] if ("/" in name) else [SKILLS / name]
    else:
        cands = [HERE, SKILLS / "kallaway-edit"]
        cands += sorted(p for p in SKILLS.iterdir() if p.is_dir() and p.name.endswith("-edit"))
    for p in cands:
        if is_engine(p):
            return p
    raise SystemExit("No editing engine found next to this skill. The kallaway-edit skill carries it: "
                     "reinstall both skills from github.com/learnaiwithhugo/video-editor-skills, then run this again.")


def state(eng: Path = None):
    """The engine's state module: DATA folder, config, the editor's Python, sound effects, font cache."""
    scripts = str((eng or engine_dir()) / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import state as st
    return st


def engine_python(eng: Path) -> Path:
    py = state(eng).PY
    if not py.exists():
        raise SystemExit(f'The editor is not set up yet. Run its setup wizard (/video-editor:kallaway-edit setup), '
                         f'or: python3 -I "{eng}/scripts/setup.py"')
    return py


def project_root(eng: Path) -> Path:
    cfg = state(eng).load_config()
    if not cfg.get("projectRoot"):
        raise SystemExit("No project folder saved yet: run the setup wizard first (/video-editor:kallaway-edit setup).")
    return Path(cfg["projectRoot"])


def probe(path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"w": int(s["width"]), "h": int(s["height"]), "fps": float(num) / float(den),
            "duration": float(j["format"]["duration"])}


def frames(path, w, h, fps=None, gray=False):
    """Yield (time, frame as numpy array) decoded by ffmpeg at w x h (and fps if given)."""
    import numpy as np
    vf = (f"fps={fps}," if fps else "") + f"scale={w}:{h}:flags=area"
    fmt, ch = ("gray", 1) if gray else ("rgb24", 3)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", fmt, "-"], stdout=subprocess.PIPE)
    size = w * h * ch
    rate = fps or probe(path)["fps"]
    i = 0
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        a = np.frombuffer(buf, np.uint8).reshape((h, w) if gray else (h, w, 3))
        yield i / rate, a
        i += 1
    p.wait()


def audio(path, channels=2, rate=8000):
    """Decoded audio as float32 numpy, shape (n, channels)."""
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", str(channels), "-ar",
                          str(rate), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, channels)


def loudness(path) -> dict:
    err = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null",
                          "-"], capture_output=True, text=True).stderr
    summ = err[err.rfind("Summary:"):]
    get = lambda key: float(summ.split(key)[1].split()[0]) if key in summ else None  # noqa: E731
    return {"lufs": get("I:"), "true_peak": get("Peak:"), "lra": get("LRA:")}


def font(size, bold=True):
    from PIL import ImageFont
    for f in ["/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]:
        try:
            return ImageFont.truetype(f, size, index=1 if bold and f.endswith(".ttc") else 0)
        except OSError:
            continue
    return ImageFont.load_default()
