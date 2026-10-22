#!/usr/bin/env python3
"""Cut the speaker out of cut.mp4 (free, local AI model) and track where their head is.

Usage:
  PY scripts/cutout.py <work_dir> [--choke 2] [--choke-only] [--track-only]

Writes:
  cutout-raw.webm the model's cut-out, frame-for-frame with cut.mp4
  cutout.webm     the same with its edge pulled in 2 px (no halo over the black stage)
  headtrack.json  per sampled frame (5 fps): top of the head (y), left/right of the head, in
                  cut.mp4 pixels. build.py uses it to frame the face card and the full layout
                  so the head pops out of the card by the right amount.

Runs `npx hyperframes remove-background` (CoreML on Apple Silicon: roughly 6-15 frames a
second at 1080x1920; the first run downloads the ~170 MB model). It refuses to finish if
the cut-out has a different frame count from cut.mp4: a single extra frame makes the
pop-out drift away from the face after every cut.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import state  # noqa: E402

SK = state.SK
PIN = state.PIN  # the pinned HyperFrames version (setup.py installs exactly this one)


def nframes(p):
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                               "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
                              capture_output=True, text=True).stdout.strip())


def track(webm: Path, out: Path, fps_sample=10):
    """Read the alpha channel at low res and find the head top per sampled frame."""
    W, H = 540, 960  # half res: a thin tuft of hair on top still registers
    raw = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(webm),
                          "-vf", f"fps={fps_sample},format=yuva420p,alphaextract,scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W)
    rows = []
    for i, f in enumerate(a):
        m = f > 48   # low threshold: wispy hair counts as head (it is what touches the caption)
        ys = np.where(m.sum(1) > 1)[0]
        if len(ys) == 0:
            rows.append({"t": round(i / fps_sample, 3), "top": None})
            continue
        top = int(ys[0])
        band = m[top:top + int(0.12 * H)]          # the top of the head
        xs = np.where(band.any(0))[0]
        rows.append({"t": round(i / fps_sample, 3), "top": top * 2,
                     "left": int(xs[0]) * 2, "right": int(xs[-1]) * 2})
    tops = [r["top"] for r in rows if r["top"] is not None]
    summary = {"head_top_median": int(np.median(tops)), "head_top_min": int(min(tops)),
               "head_top_max": int(max(tops)),
               "head_cx_median": int(np.median([(r["left"] + r["right"]) / 2 for r in rows
                                                if r["top"] is not None]))}
    out.write_text(json.dumps({"summary": summary, "samples": rows}, indent=1))
    return summary


def choke(src: Path, dst: Path, px: int):
    """Pull the matte edge in by `px` pixels and soften it by 1 px. The model's edge carries a
    rim of the room's colour (a light halo on hair against a bright wall); over the black
    stage that rim shows. Two pixels in removes it without visibly thinning the hair."""
    erode = ",".join(["erosion"] * px) if px > 0 else "null"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-i", str(src),
                    "-filter_complex",
                    f"[0:v]format=yuva420p,split[c][a];[a]alphaextract,{erode},gblur=sigma=0.8[m];"
                    f"[c][m]alphamerge,format=yuva420p[o]",
                    "-map", "[o]", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
                    "-crf", "20", "-b:v", "0", "-deadline", "good", "-cpu-used", "5", "-row-mt", "1",
                    "-g", "30", str(dst)], check=True)


def main():
    work = Path(sys.argv[1]).resolve()
    cut, webm, raw = work / "cut.mp4", work / "cutout.webm", work / "cutout-raw.webm"
    px = 2
    if "--choke" in sys.argv:
        px = int(sys.argv[sys.argv.index("--choke") + 1])
    if "--track-only" not in sys.argv and "--choke-only" not in sys.argv:
        env = dict(os.environ, HYPERFRAMES_SKIP_SKILLS="1", HYPERFRAMES_NO_TELEMETRY="1")
        print("Cutting the speaker out of the background (a few minutes) ...", flush=True)
        subprocess.run(["npx", "-y", f"hyperframes@{PIN}", "remove-background", str(cut),
                        "-o", str(raw), "--quality", "best"], check=True, env=env, cwd=work)
        a, b = nframes(cut), nframes(raw)
        if a != b:
            sys.exit(f"Cut-out has {b} frames but the cut has {a}. Re-run assemble.py "
                     "(it makes a constant frame rate clip), then this script.")
        print(f"  cut-out: {b} frames, matches cut.mp4", flush=True)
    if "--track-only" not in sys.argv:
        print(f"Cleaning the cut-out edge ({px} px) ...", flush=True)
        choke(raw, webm, px)
        if nframes(webm) != nframes(cut):
            sys.exit("Edge clean-up changed the frame count; something is wrong with ffmpeg.")
    s = track(webm, work / "headtrack.json")
    print(f"  head top: median y={s['head_top_median']} (range {s['head_top_min']}-"
          f"{s['head_top_max']}), centre x={s['head_cx_median']}")


if __name__ == "__main__":
    main()
