#!/usr/bin/env python3
"""Everything mechanical about the reference reels, done before any agent looks at them.
Needs only ffmpeg (Pillow, if present, adds time labels to the contact sheets).

Usage:
  python3 -I prep_refs.py <STYLE_DIR> [ref-1.mp4 ...]      (default: every references/ref-*.mp4)

Writes, per reel, into STYLE_DIR/references/analysis/<reel>/:
  info.json        size, fps, length, loudness, cut times
  frames/          4 frames a second (small), the raw material for the sheets
  sheets/          contact sheets, 12 tiles = 3 seconds each, read left to right, top to bottom,
                   file name says the time range (sheet_03_6.0-9.0s.jpg); tiles are labelled if Pillow exists
  stills/          full-size frames just after every cut, plus 10 evenly spaced
  cuts.txt         hard cuts (seconds), from ffmpeg's scene detector
  words.txt        "[12.34] word" per line, only if a local Whisper is installed (optional)
And references/analysis/overview.jpg: 3 frames from each reel side by side.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # labels are a nice-to-have
    Image = None

FPS, COLS, ROWS, TW = 4, 4, 3, 300


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)])
    j = json.loads(r.stdout)
    s, f = j["streams"][0], j["format"]
    n, d = s["r_frame_rate"].split("/")
    return {"width": s["width"], "height": s["height"], "fps": round(int(n) / max(int(d), 1), 2),
            "duration": round(float(f["duration"]), 2)}


def cuts(path):
    r = run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", "scale=270:-2,scdet=threshold=14", "-an", "-f", "null", "-"])
    times = [float(m) for m in re.findall(r"lavfi\.scd\.time:\s*([\d.]+)", r.stderr)]
    out = []
    for t in times:
        if not out or t - out[-1] > 0.25:
            out.append(round(t, 2))
    return out


def loudness(path):
    r = run(["ffmpeg", "-hide_banner", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"])
    i = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr)
    lra = re.findall(r"LRA:\s*([\d.]+) LU", r.stderr)
    return {"integrated_lufs": float(i[-1]) if i else None, "range_lu": float(lra[-1]) if lra else None,
            "note": "Measured loudness only. Nobody can hear sounds from this: sound effects are a guess until a person listens."}


def sheets(frames_dir, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(frames_dir.glob("f_*.jpg"))
    per = COLS * ROWS
    for si in range(0, len(files), per):
        chunk = files[si:si + per]
        a, b = si / FPS, (si + len(chunk)) / FPS
        name = out_dir / f"sheet_{si // per + 1:02d}_{a:.1f}-{b:.1f}s.jpg"
        if Image:
            ims = [Image.open(f).convert("RGB") for f in chunk]
            w, h = ims[0].size
            sheet = Image.new("RGB", (COLS * w, ROWS * (h + 28)), "white")
            draw = ImageDraw.Draw(sheet)
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
            except OSError:
                font = ImageFont.load_default()
            for k, im in enumerate(ims):
                x, y = (k % COLS) * w, (k // COLS) * (h + 28)
                sheet.paste(im, (x, y + 28))
                draw.text((x + 6, y + 3), f"{(si + k) / FPS:.2f}s", fill="black", font=font)
            sheet.save(name, quality=82)
        else:
            lst = out_dir / "_list.txt"
            lst.write_text("".join(f"file '{f}'\n" for f in chunk))
            run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                 "-vf", f"tile={COLS}x{ROWS}", "-frames:v", "1", str(name)])
            lst.unlink()


def stills(path, info, cut_times, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = [(round(t + 0.12, 2), "cut") for t in cut_times]
    ts += [(round(info["duration"] * (k + 0.5) / 10, 2), "even") for k in range(10)]
    for t, kind in sorted(ts):
        if t < info["duration"]:
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(path), "-frames:v", "1", "-q:v", "3",
                 str(out_dir / f"{t:06.2f}s-{kind}.jpg")])


def words(path, out_dir):
    """Optional transcript with word times, from whatever local Whisper is installed. Never required."""
    txt = out_dir / "words.txt"
    try:
        from faster_whisper import WhisperModel  # noqa: F401
        model = WhisperModel("small.en", device="cpu", compute_type="int8")
        segs, _ = model.transcribe(str(path), word_timestamps=True)
        txt.write_text("".join(f"[{w.start:.2f}] {w.word.strip()}\n" for s in segs for w in s.words))
        return True
    except Exception:
        pass
    cli = shutil.which("whisper")
    if cli:
        tmp = out_dir / "_whisper"
        r = run([cli, str(path), "--model", "base.en", "--word_timestamps", "True", "--output_format", "json",
                 "--output_dir", str(tmp), "--fp16", "False"])
        js = list(tmp.glob("*.json"))
        if r.returncode == 0 and js:
            data = json.loads(js[0].read_text())
            txt.write_text("".join(f"[{w['start']:.2f}] {w['word'].strip()}\n"
                                   for s in data.get("segments", []) for w in s.get("words", [])))
            shutil.rmtree(tmp, ignore_errors=True)
            return True
        shutil.rmtree(tmp, ignore_errors=True)
    return False


def overview(reels, out):
    if not Image:
        return
    rows = []
    for reel in reels:
        st = sorted((out / reel.stem / "stills").glob("*-even.jpg"))
        pick = [st[i] for i in (1, 5, 8) if i < len(st)]
        ims = [Image.open(p).convert("RGB") for p in pick]
        ims = [im.resize((360, int(360 * im.height / im.width))) for im in ims]
        if ims:
            h = max(im.height for im in ims)
            row = Image.new("RGB", (360 * 3, h), "white")
            for k, im in enumerate(ims):
                row.paste(im, (k * 360, 0))
            rows.append(row)
    if rows:
        sheet = Image.new("RGB", (1080, sum(r.height for r in rows)), "white")
        y = 0
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height
        sheet.save(out / "overview.jpg", quality=85)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    style = Path(sys.argv[1]).expanduser()
    reels = [Path(p) for p in sys.argv[2:]] or sorted((style / "references").glob("ref-*.mp4"))
    out = style / "references" / "analysis"
    for reel in reels:
        d = out / reel.stem
        (d / "frames").mkdir(parents=True, exist_ok=True)
        info = probe(reel)
        run(["ffmpeg", "-v", "error", "-y", "-i", str(reel), "-vf", f"fps={FPS},scale={TW}:-2", "-q:v", "4",
             str(d / "frames" / "f_%04d.jpg")])
        info["cuts"] = cuts(reel)
        info["loudness"] = loudness(reel)
        (d / "cuts.txt").write_text("\n".join(f"{t:.2f}" for t in info["cuts"]) + "\n")
        sheets(d / "frames", d / "sheets")
        stills(reel, info, info["cuts"], d / "stills")
        info["has_words"] = words(reel, d)
        (d / "info.json").write_text(json.dumps(info, indent=1))
        print(f"{reel.name}: {info['duration']}s, {len(info['cuts'])} cuts, "
              f"{len(list((d / 'sheets').glob('*.jpg')))} sheets, words: {'yes' if info['has_words'] else 'no'}")
    overview(reels, out)


if __name__ == "__main__":
    main()
