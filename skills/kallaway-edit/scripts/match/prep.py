#!/usr/bin/env python3
"""Everything mechanical about the reference reels, done before any agent looks at them.

Usage (run with the editor's Python, PY in the skill):
  PY scripts/prep.py <style_dir> <reel.mp4> [<reel.mp4> ...] [--model small.en]

Writes, per reel, into <style_dir>/prep/<reel-stem>/:
  transcripts/<stem>.words.json + .txt   every word with its time (free local faster-whisper)
  words.txt                              "[12.34] word" one per line, for agents
  cuts.txt / events.txt                  hard cuts and smaller visual changes, from every frame
  sheets/sheet_NNN.png                   4 frames a second, 4x3 tiles (3 s a sheet), time burned in
  stills/<t>s-cut.png, <t>s-even.png     full-size frames just after each cut + 12 evenly spaced
  spectrum.png                           the whole soundtrack as a picture
  audio.json                             loudness, stereo-only bursts (added sound effects), music floor
  summary.json                           all of the above as numbers
And <style_dir>/style-check.png: 3 frames from each reel side by side, to confirm they share one style
before spending any agents on them.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

SHEET_FPS, TW, TH, COLS, ROWS = 4, 360, 640, 4, 3


def cut_scan(path, info):
    """Mean absolute difference between consecutive frames, every frame, at 72x128 grey."""
    diffs, prev = [], None
    for _, f in engine.frames(path, 72, 128, gray=True):
        f = f.astype(np.int16)
        diffs.append(0.0 if prev is None else float(np.abs(f - prev).mean()))
        prev = f
    d = np.array(diffs)
    fps = info["fps"]
    cuts, events = [], []
    for i in range(1, len(d)):
        local = np.median(d[max(0, i - 6):i + 7])
        if d[i] > 18 and d[i] > 4 * max(local, 1.0) and (not cuts or i / fps - cuts[-1] > 0.25):
            cuts.append(round(i / fps, 3))
        elif d[i] > 2.5 and d[i] > 2 * max(local, 0.5) and (not events or i / fps - events[-1] > 0.25):
            events.append(round(i / fps, 3))
    return d, cuts, events


def sheets(path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    per = COLS * ROWS
    fnt = engine.font(26)
    tiles, n = [], 0

    def flush():
        nonlocal tiles, n
        if not tiles:
            return
        sheet = Image.new("RGB", (TW * COLS, TH * ROWS), (0, 0, 0))
        for k, (t, im) in enumerate(tiles):
            x, y = (k % COLS) * TW, (k // COLS) * TH
            sheet.paste(im, (x, y))
            d = ImageDraw.Draw(sheet)
            label = f"{t:6.2f}s"
            d.rectangle([x + 4, y + 4, x + 112, y + 36], fill=(0, 0, 0))
            d.text((x + 8, y + 6), label, fill=(255, 230, 0), font=fnt)
        n += 1
        sheet.save(out / f"sheet_{n:03d}.png")
        tiles = []

    for t, f in engine.frames(path, TW, TH, fps=SHEET_FPS):
        tiles.append((t, Image.fromarray(f)))
        if len(tiles) == per:
            flush()
    flush()
    return n


def still(path, t, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                    str(dst)], check=True)


def audio_scan(path):
    a = engine.audio(path, 2, 8000)
    win = 400  # 50 ms
    n = len(a) // win
    if n == 0:
        return {}
    a = a[:n * win]
    mid = ((a[:, 0] + a[:, 1]) / 2).reshape(n, win)
    side = ((a[:, 0] - a[:, 1]) / 2).reshape(n, win)
    db = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean(axis=1)) + 1e-9)  # noqa: E731
    mid_db, side_db = db(mid), db(side)
    mono = bool(side_db.max() < -80)
    # A stereo-wide sound effect makes the stereo difference jump relative to the voice. Some reels leak a
    # little voice into it, so the test is a jump in the side/mid ratio, not a fixed level. Calibrated on
    # Kallaway reel 1: 5 hits found, matching the 6 effects verified by hand (k = 14 dB).
    ratio = side_db - mid_db
    hot = (ratio > np.median(ratio) + 14) & (side_db > np.median(side_db) + 6)
    hits = []
    for i in np.where(hot)[0]:
        if not hits or i * 0.05 - hits[-1]["t"] > 0.4:
            hits.append({"t": round(i * 0.05, 2), "side_db": round(float(side_db[i]), 1)})
    return {"mono_mix": mono, "stereo_sfx_hits": hits,
            "stereo_sfx_per_min": round(len(hits) / (n * 0.05) * 60, 1),
            "quiet_floor_db": round(float(np.percentile(mid_db, 5)), 1),
            "music": "unknown: tight cuts and compression hide a quiet bed from the numbers; ask the ear check",
            "note": "Voice is recorded mono, so a jump in stereo-only energy was added in the edit (a stereo "
                    "sound effect). Mono effects can't be seen this way. Inferred from the signal, not heard."}


def prep(path: Path, root: Path, eng: Path, model: str):
    stem = path.stem
    out = root / "prep" / stem
    out.mkdir(parents=True, exist_ok=True)
    info = engine.probe(path)
    print(f"[{stem}] {info['w']}x{info['h']} {info['fps']:.3f} fps {info['duration']:.1f} s")

    py = engine.engine_python(eng)
    subprocess.run([str(py), "-I", str(eng / "scripts" / "transcribe.py"), str(out), str(path),
                    "--model", model], check=True, stdout=subprocess.DEVNULL)
    words = json.loads((out / "transcripts" / f"{stem}.words.json").read_text())
    (out / "words.txt").write_text("".join(f"[{w['start']:.2f}] {w['w']}\n" for w in words))
    print(f"[{stem}] {len(words)} words")

    d, cuts, events = cut_scan(path, info)
    (out / "cuts.txt").write_text("".join(f"{c}\n" for c in cuts))
    (out / "events.txt").write_text("".join(f"{e}\n" for e in events))
    print(f"[{stem}] {len(cuts)} hard cuts, {len(events)} smaller changes")

    n = sheets(path, out / "sheets")
    print(f"[{stem}] {n} contact sheets")

    st = out / "stills"
    st.mkdir(exist_ok=True)
    for c in cuts:
        still(path, min(c + 0.15, info["duration"] - 0.05), st / f"{c:06.2f}s-cut.png")
    for t in np.linspace(0.2, info["duration"] - 0.2, 12):
        still(path, t, st / f"{t:06.2f}s-even.png")

    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-lavfi",
                    "showspectrumpic=s=3000x500:legend=1", str(out / "spectrum.png")], check=True)
    aud = audio_scan(path)
    aud.update(engine.loudness(path))
    (out / "audio.json").write_text(json.dumps(aud, indent=1))
    print(f"[{stem}] loudness {aud.get('lufs')} LUFS, {len(aud.get('stereo_sfx_hits', []))} stereo sound-effect hits")

    dur = info["duration"]
    summ = {"file": str(path), **info, "words": len(words), "words_per_min": round(len(words) / dur * 60),
            "hard_cuts": len(cuts), "avg_shot_s": round(dur / (len(cuts) + 1), 2),
            "visual_changes_per_s": round((len(cuts) + len(events)) / dur, 2), "sheets": n,
            "audio": {k: v for k, v in aud.items() if k != "stereo_sfx_hits"}}
    (out / "summary.json").write_text(json.dumps(summ, indent=1))
    return summ


def style_check(reels, root: Path):
    (root / "prep").mkdir(parents=True, exist_ok=True)
    cols = []
    for p in reels:
        dur = engine.probe(p)["duration"]
        ims = []
        for frac in (0.25, 0.5, 0.75):
            tmp = root / "prep" / f".check-{p.stem}-{frac}.png"
            still(p, dur * frac, tmp)
            ims.append(Image.open(tmp).convert("RGB").resize((300, 533)))
            tmp.unlink()
        col = Image.new("RGB", (300, 533 * 3))
        for k, im in enumerate(ims):
            col.paste(im, (0, 533 * k))
        cols.append(col)
    sheet = Image.new("RGB", (310 * len(cols), 533 * 3), (40, 40, 40))
    for k, c in enumerate(cols):
        sheet.paste(c, (310 * k, 0))
    sheet.save(root / "style-check.png")


def main():
    args = [a for a in sys.argv[1:]]
    model = "small.en"
    if "--model" in args:
        model = args[args.index("--model") + 1]
        del args[args.index("--model"):args.index("--model") + 2]
    root, reels = Path(args[0]), [Path(a) for a in args[1:]]
    if not reels:
        raise SystemExit(__doc__)
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is missing: run the setup wizard first.")
    eng = engine.engine_dir()
    root.mkdir(parents=True, exist_ok=True)
    style_check(reels, root)
    print(f"style check sheet: {root / 'style-check.png'}")
    all_s = [prep(p, root, eng, model) for p in reels]
    (root / "prep" / "summary.json").write_text(json.dumps(all_s, indent=1))
    import fingerprint  # measured style numbers per reel, and the spec the style skill is scored against
    fps = []
    for p in reels:
        fp = fingerprint.measure(p)
        (root / "prep" / p.stem / "fingerprint.json").write_text(json.dumps(fp, indent=1))
        fps.append(fp)
    fingerprint.make_spec(root / "style-spec.json", reels, fps)
    print(f"style spec: {root / 'style-spec.json'}\n\nPrep done.")


if __name__ == "__main__":
    main()
