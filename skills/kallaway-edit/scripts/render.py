#!/usr/bin/env python3
"""Render the project, level the loudness, and (with --final) deliver to exports/.

Usage:
  PY scripts/render.py <work_dir> [--final] [--name draft2] [--exports <dir>]

- Draft (default): fast draft-quality render to <work_dir>/renders/<name>.mp4 (~1 min for 35 s).
- --final: delivery quality, then <exports>/<slug>-<style>-vN.mp4 (<style> = this skill's name minus "-edit") (1080x1920, 30 fps) plus a
  720p phone copy next to it (<...>-720p.mp4), never overwriting an earlier version.
Every render: the frame cache lives in <work_dir>/.hf-cache and is deleted afterwards (it
grows to ~2 GB), and the mix is levelled to -14 LUFS integrated, -1 dBTP (two-pass loudnorm,
picture copied untouched).
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import state  # noqa: E402

SK = state.SK
PIN = state.PIN  # the pinned HyperFrames version (setup.py installs exactly this one)
TAG = SK.name[:-5] if SK.name.endswith("-edit") else SK.name  # "kallaway" -> <slug>-kallaway-v1.mp4


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    return float(i.group(1)) if i else None, float(tp.group(1)) if tp else None


def level(src: Path, dst: Path, target=-14.0, tp=-1.5):  # -1.5 leaves room for AAC overshoot
    first = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                            f"loudnorm=I={target}:TP={tp}:LRA=9:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    m = json.loads(first[first.rfind("{"):first.rfind("}") + 1])
    af = (f"loudnorm=I={target}:TP={tp}:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
          f"linear=true,aresample=48000")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "copy", "-af", af,
                    "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", str(dst)],
                   check=True)


def main():
    args = sys.argv[1:]
    work = Path(args[0]).resolve()
    final = "--final" in args
    name = args[args.index("--name") + 1] if "--name" in args else ("final" if final else "draft")
    exports = Path(args[args.index("--exports") + 1]) if "--exports" in args else work.parent.parent / "exports"
    proj, renders, cache = work / "project", work / "renders", work / ".hf-cache"
    renders.mkdir(exist_ok=True)
    free = shutil.disk_usage(work).free / 1e9
    if free < 4:
        sys.exit(f"Only {free:.1f} GB free on disk; a render needs ~3 GB of scratch space. Free some up first.")
    raw = renders / f"{name}-raw.mp4"
    env = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1", HYPERFRAMES_NO_TELEMETRY="1")
    print(f"Rendering ({'delivery' if final else 'draft'} quality) ...", flush=True)
    try:
        subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "render", "--quality", "delivery" if final else "draft",
                        "--frames-cache-dir", str(cache), "--output", str(raw), "--quiet"],
                       check=True, cwd=proj, env=env)
    finally:
        shutil.rmtree(cache, ignore_errors=True)
    out = renders / f"{name}.mp4"
    level(raw, out)
    raw.unlink()
    i, tp = loudness(out)
    # the picture's length (AAC adds a few ms of padding to the audio, so not the container's)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout)
    want = json.loads((work / "segments.json").read_text())["duration"]
    print(f"  {out}  {dur:.2f} s (plan {want:.2f} s)  loudness {i} LUFS, true peak {tp} dBFS")
    if abs(dur - want) > 0.05:
        print("  ! length differs from the plan")
    if final:
        exports.mkdir(parents=True, exist_ok=True)
        slug = work.name
        v = 1
        while (exports / f"{slug}-{TAG}-v{v}.mp4").exists():
            v += 1
        dst = exports / f"{slug}-{TAG}-v{v}.mp4"
        shutil.copy(out, dst)
        phone = exports / f"{slug}-{TAG}-v{v}-720p.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(dst), "-vf", "scale=720:1280:flags=lanczos",
                        "-c:v", "libx264", "-crf", "24", "-preset", "slow", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", "-movflags", "+faststart", str(phone)], check=True)
        print(f"  delivered: {dst}\n  phone copy: {phone}")


if __name__ == "__main__":
    main()
