#!/usr/bin/env python3
"""The sound-effect map: which real recorded sound goes on which animation, and how loud.

Run directly to fetch/check the library:  PY scripts/sounds.py
The sounds are HyperFrames' bundled media-use SFX (recorded, from Pixabay, Pixabay Content
License: free to use inside videos, but the files may not be redistributed on their own). So
this skill never ships copies: they are copied from a HyperFrames media-use skill on this
machine, or downloaded from the HyperFrames repo, into the editor's data folder (DATA/sfx/, see
state.py), never into the skill folder.
The table is mirrored in references/sound-map.md; change both together.
"""
import json
import math
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import state  # noqa: E402

SK = state.SK
LIB = state.SFX
REPO = "https://raw.githubusercontent.com/heygen-com/hyperframes/main/skills/media-use/audio/assets/sfx/"

# cue -> file, window inside the file (start, length; None = whole), the time inside the window
# that should land ON the picture (the hit), the target peak in the mix (dBFS, voice peaks ~-1),
# and priority (when two cues land within 2 frames, the higher priority plays, the other is dropped).
MAP = {
    #  cue          file                   window          hit    peak  prio   used for
    "whoosh":     ("whoosh.mp3",           None,           0.16, -13.0, 5),  # virtual-camera move, scene cut
    "whoosh-big": ("whoosh-cinematic.mp3", (2.05, 1.05),   0.49, -12.0, 6),  # layout cut into the stage, title swap
    "pop":        ("pop.mp3",              None,           0.12, -14.0, 4),  # pill, label, numeral, card landing
    "click":      ("click.mp3",            None,           0.05, -15.0, 3),  # slider snap, tick, strike, counter step
    "key":        ("key-press.mp3",        None,           0.07, -18.0, 2),  # a single typed character / slash
    "typing":     ("typing.mp3",           None,           0.0,  -18.0, 2),  # typed chat text (trimmed to the typing)
    "impact":     ("impact-bass-1.mp3",    (0.0, 1.4),     0.14, -12.0, 8),  # the big moments: the numerals, the claim box
    "sparkle":    ("sparkle.mp3",          (0.0, 1.2),     0.09, -20.0, 1),  # a payoff, sparingly
    "chime":      ("chime.mp3",            (0.0, 1.6),     0.42, -18.0, 1),  # a positive payoff, sparingly
    "riser":      ("riser.mp3",            (2.30, 1.25),   1.25, -12.0, 9),  # into a snap punch-in, ends ON the snap
}
NEEDED = sorted({v[0] for v in MAP.values()})
MEDIA_USE_CANDIDATES = [
    SK.parent / "media-use" / "audio" / "assets" / "sfx",                       # sibling skill
    Path.home() / ".claude" / "skills" / "media-use" / "audio" / "assets" / "sfx",
    Path.home() / ".agents" / "skills" / "media-use" / "audio" / "assets" / "sfx",
]


def ensure_library(quiet=False):
    """Copy (or download) the recorded SFX into DATA/sfx. Returns the folder."""
    LIB.mkdir(parents=True, exist_ok=True)
    missing = [f for f in NEEDED if not (LIB / f).exists()]
    if not missing:
        return LIB
    src = next((c for c in MEDIA_USE_CANDIDATES if all((c / f).exists() for f in missing)), None)
    for f in missing:
        if src:
            shutil.copy(src / f, LIB / f)
        else:
            with urllib.request.urlopen(urllib.request.Request(REPO + f, headers={"User-Agent": "video-editor-plugin"}),
                                        timeout=60) as r:
                (LIB / f).write_bytes(r.read())
    if not quiet:
        print(f"  sound effects: {len(missing)} files from {'HyperFrames media-use on this Mac' if src else 'the HyperFrames repo'}")
    return LIB


def measure():
    """Peak (dBFS) of each cue's window, cached in DATA/sfx/levels.json."""
    cache = LIB / "levels.json"
    if cache.exists():
        lv = json.loads(cache.read_text())
        if set(lv) == set(MAP):
            return lv
    lv = {}
    for cue, (f, win, *_r) in MAP.items():
        cmd = ["ffmpeg", "-v", "error"]
        if win:
            cmd += ["-ss", str(win[0]), "-t", str(win[1])]
        cmd += ["-i", str(LIB / f), "-ac", "1", "-f", "f32le", "-"]
        import numpy as np
        a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                    "csv=p=0", str(LIB / f)], capture_output=True, text=True).stdout)
        lv[cue] = {"peak": round(20 * math.log10(float(np.abs(a).max()) + 1e-9), 2),
                   "dur": round(win[1] if win else dur, 3)}
    cache.write_text(json.dumps(lv, indent=1))
    return lv


def volume(cue, lv, extra_db=0.0):
    """data-volume that puts this cue's peak at its target level (+ an optional per-cue trim)."""
    target = MAP[cue][3] + extra_db
    return round(min(1.0, 10 ** ((target - lv[cue]["peak"]) / 20)), 3)


if __name__ == "__main__":
    ensure_library()
    lv = measure()
    for cue in MAP:
        print(f"  {cue:11s} {MAP[cue][0]:22s} peak {lv[cue]['peak']:6.1f} dBFS -> volume {volume(cue, lv)}")
