#!/usr/bin/env python3
"""Check a RENDERED reel the way a picky editor would. Run on the real render, not on snapshots.

Usage:
  PY scripts/qa.py <work_dir> <video.mp4> [--ref <reference.mp4> --ref-at 12.3 --at 4.1]
  PY scripts/qa.py <work_dir> --takes        (progress sheet of the picked takes)

Writes into <work_dir>/qa/ (and copies the headline sheets into <work_dir>/progress/):
  cuts.png        every cut: the frame before and the frame after, side by side, labelled
  beats.png       one frame per caption chunk (every ~0.5 s), to read captions against the words
  report.txt      length, every cut's distance to the next word onset, caption text vs the words,
                  loudness (integrated LUFS, true peak), frames per second, anything suspicious
  side-by-side.png  (with --ref) a frame of a reference reel next to ours, same layout
Then LOOK at the PNGs at full size: halo or drift on the pop-out after a cut, captions over the
face, text in the Instagram no-go zones, empty or frozen moments.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

FPS = 30


def frame(video, t, out, w=540):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t):.4f}", "-i", str(video), "-frames:v", "1",
                    "-vf", f"scale={w}:-2", str(out)], check=True)


def label(img, text, out):
    """Write a caption bar on top of a still (Pillow: ffmpeg builds often lack drawtext)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(img).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 34], fill=(0, 0, 0))
    d.text((8, 6), text, fill=(255, 255, 255), font=ImageFont.load_default(size=20))
    im.save(out)


def tile(images, out, cols):
    """Grid of equal-size stills."""
    from PIL import Image
    if not images:
        return
    ims = [Image.open(p).convert("RGB") for p in images]
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (32, 32, 32))
    for k, im in enumerate(ims):
        sheet.paste(im.resize((w, h)), ((k % cols) * (w + 4), (k // cols) * (h + 4)))
    sheet.save(out)


def loud(video):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    g = lambda k: (re.search(k, tail) or [None, "?"])[1]
    return g(r"I:\s+(-?[\d.]+) LUFS"), g(r"Peak:\s+(-?[\d.]+) dBFS"), g(r"LRA:\s+(-?[\d.]+) LU")


def takes_sheet(work):
    seg = json.loads((work / "segments.json").read_text())
    words = json.loads((work / "words.json").read_text())
    qa = work / "qa"; qa.mkdir(exist_ok=True)
    imgs, seen = [], set()
    for p in seg["pieces"]:
        if p["line"] in seen:
            continue
        seen.add(p["line"])
        text = " ".join(w["w"] for w in words if w["line"] == p["line"])
        f = qa / f"take-{p['line']:02d}.png"
        frame(work / "cut.mp4", p["start"] + 0.4, f, w=360)
        label(f, f"{p['line']}  {p['start']:.1f}s  {text[:34]}", f)
        imgs.append(f)
    out = work / "progress" / "01-takes-picked.png"
    out.parent.mkdir(exist_ok=True)
    tile(imgs, out, 6)
    for f in imgs:
        f.unlink()
    print(out)


def main():
    args = sys.argv[1:]
    work = Path(args[0]).resolve()
    if "--takes" in args:
        return takes_sheet(work)
    video = Path(args[1]).resolve()
    qa = work / "qa"; qa.mkdir(exist_ok=True)
    build = json.loads((work / "build.json").read_text())
    words = json.loads((work / "words.json").read_text())
    rep = []
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=duration", "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout)
    fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=r_frame_rate,width,height", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True).stdout.strip()
    rep.append(f"video: {video.name}  {dur:.2f} s (plan {build['duration']:.2f} s)  {fps}")

    # cuts: distance from each cut to the next word onset
    # real speech onsets from the audio (10 ms windows): Whisper's word starts are often late
    import numpy as np
    # (read the voice-only cut.mp4: the render's sound effects sit right on the cuts)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(work / "cut.mp4"), "-vn", "-ac", "1", "-ar", "8000",
                          "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32); n = len(a) // 80
    db = 20 * np.log10(np.sqrt((a[:n * 80].reshape(n, 80) ** 2).mean(1)) + 1e-9)
    rep.append("\ncuts (cut -> first speech after it, from the audio; Kallaway lands cuts 0-80 ms before the word):")
    cut_imgs = []
    for k, c in enumerate(build["cuts"]):
        i0 = int(c * 100)
        lvl = db[max(0, i0 - 1):i0 + 1].max()
        on = next((j for j, v in enumerate(db[i0:i0 + 50]) if v > -34), None)
        nxt = next((w for w in words if w["start"] >= c - 0.12), None)
        if lvl > -34:
            note = "cut inside a word (between words of one line)" if on == 0 else ""
            gap_txt = "mid-speech"
        else:
            gap_txt = f"+{on * 10} ms" if on is not None else "no speech within 0.5 s"
            note = "" if on is not None and on * 10 <= 120 else "   <-- check"
        rep.append(f"  {c:6.3f}s -> '{nxt['w'] if nxt else '-'}' speech {gap_txt} {note}")
        a, b = qa / f"cut{k:02d}a.png", qa / f"cut{k:02d}b.png"
        frame(video, c - 1.5 / FPS, a, w=300)
        frame(video, c + 1.5 / FPS, b, w=300)
        label(a, f"{c:.2f}s before", a); label(b, "after", b)
        cut_imgs += [a, b]
    tile(cut_imgs, qa / "cuts.png", 8)
    for f in cut_imgs:
        f.unlink()

    # captions: one frame per chunk, ~0.12 s after it appears
    beat_imgs = []
    for k, ch in enumerate(build["chunks"]):
        f = qa / f"beat{k:03d}.png"
        frame(video, ch["t"] + 0.12, f, w=240)
        beat_imgs.append(f)
    tile(beat_imgs, qa / "beats.png", 12)
    for f in beat_imgs:
        f.unlink()
    rep.append("\ncaption chunks (read them against beats.png):")
    rep.append("  " + " | ".join(c["text"] for c in build["chunks"]))

    i, tp, lra = loud(video)
    rep.append(f"\nloudness: {i} LUFS integrated (target -14), true peak {tp} dBFS (target <= -1), LRA {lra} LU")

    if "--ref" in args:
        ref = Path(args[args.index("--ref") + 1]); rt = float(args[args.index("--ref-at") + 1])
        ot = float(args[args.index("--at") + 1])
        a, b = qa / "ref.png", qa / "ours.png"
        frame(ref, rt, a, w=720); frame(video, ot, b, w=720)
        label(a, "reference", a); label(b, "ours", b)
        tile([a, b], qa / "side-by-side.png", 2)
        a.unlink(); b.unlink()
    (qa / "report.txt").write_text("\n".join(rep) + "\n")
    print("\n".join(rep))
    print(f"\nsheets: {qa / 'cuts.png'}  {qa / 'beats.png'}")


if __name__ == "__main__":
    main()
