#!/usr/bin/env python3
"""The golden test: how close is a recreation of a reference moment to the real thing?

Usage (run with the engine's Python):
  golden.py <reference.mp4> <ref_start> <ref_end> <recreation.mp4> <out_dir> [--rec-start 0]

Rebuild a short window (5-10 s) of a reference reel with the style skill, using that reel's own audio
and words (see SKILL.md, "Lock the style"), then run this. It lines the two windows up, scores the
picture similarity (SSIM, 1.0 = identical) for the whole frame and for each part of the layout, and
writes <out_dir>/golden.png (8 matched frame pairs, reference on the left) and golden.json.
Regions: stage (top 62 %), caption band (58-70 %), card (73-100 %).
Iterate the style pack (style.json, the kit CSS, the scene) until the scores stop improving; record the
before/after numbers in the style's references/lock-log.md.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

REGIONS = {"frame": (0, 1920), "stage": (0, 1190), "caption": (1114, 1344), "card": (1402, 1920)}


def ssim(ref, a0, a1, rec, b0, y0, y1):
    dur = a1 - a0
    crop = f"crop=1080:{y1 - y0}:0:{y0}"
    f = (f"[0:v]trim={a0}:{a1},setpts=PTS-STARTPTS,fps=12,scale=1080:1920,{crop}[a];"
         f"[1:v]trim={b0}:{b0 + dur},setpts=PTS-STARTPTS,fps=12,scale=1080:1920,{crop}[b];[a][b]ssim")
    err = subprocess.run(["ffmpeg", "-i", str(ref), "-i", str(rec), "-lavfi", f, "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    m = re.findall(r"All:([0-9.]+)", err)
    return float(m[-1]) if m else None


def grab(path, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-vf", "scale=270:480", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return Image.frombytes("RGB", (270, 480), raw)


def main():
    a = sys.argv[1:]
    b0 = float(a[a.index("--rec-start") + 1]) if "--rec-start" in a else 0.0
    ref, a0, a1, rec, out = Path(a[0]), float(a[1]), float(a[2]), Path(a[3]), Path(a[4])
    out.mkdir(parents=True, exist_ok=True)
    scores = {k: ssim(ref, a0, a1, rec, b0, *v) for k, v in REGIONS.items()}
    (out / "golden.json").write_text(json.dumps({"reference": str(ref), "window": [a0, a1],
                                                 "recreation": str(rec), "ssim": scores}, indent=1))
    n = 8
    sheet = Image.new("RGB", (n * 280, 2 * 490 + 30), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    d.text((8, 4), "top: reference   bottom: recreation   " +
           "  ".join(f"{k} {v:.3f}" for k, v in scores.items() if v is not None), fill=(255, 230, 0),
           font=engine.font(20))
    for k in range(n):
        t = (a1 - a0) * (k + 0.5) / n
        sheet.paste(grab(ref, a0 + t), (k * 280, 30))
        sheet.paste(grab(rec, b0 + t), (k * 280, 520))
    sheet.save(out / "golden.png")
    print(json.dumps(scores, indent=1))


if __name__ == "__main__":
    main()
