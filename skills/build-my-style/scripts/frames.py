#!/usr/bin/env python3
"""Copy-exact mode: let the person point at the exact moment of a reference reel they want, then study it.

Usage:
  python3 -I frames.py gallery "<style folder>" "<video>" [--fps 2]
      Every frame at 2 per second, numbered, on one page they can scroll: references/analysis/<name>-frames/index.html
      (also linked from the style page as /refs/analysis/<name>-frames/). They answer with numbers ("7 to 16").
  python3 -I frames.py study "<style folder>" "<video>" <start s> <seconds> [--fps 12.5] [--cols 12] [--width 160] [--crop W:H:X:Y]
      A labelled motion sheet (each frame stamped with its time) for matching an animation frame by frame:
      references/analysis/study/<name>-<start>s.jpg. Use 12.5-25 fps over the 1-2 seconds where the motion
      happens, and --crop to zoom on the moving part.
  python3 -I frames.py when "<style folder>" "<video>" <frame number> [--fps 2]
      The time in seconds of a gallery frame number.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def opt(args, key, default):
    return args[args.index(key) + 1] if key in args else default


def extract(video, out_dir, vf, start=None, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(video)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-vf", vf, "-q:v", "3", str(out_dir / "f%04d.jpg")]
    subprocess.run(cmd, check=True)
    return sorted(out_dir.glob("f*.jpg"))


def gallery(style, video, fps):
    name = video.stem
    out = style / "references" / "analysis" / f"{name}-frames"
    (out / "frames").mkdir(parents=True, exist_ok=True)
    for old in (out / "frames").glob("f*.jpg"):
        old.unlink()   # frames are rebuilt from the video every time, nothing of theirs lives here
    frames = extract(video, out / "frames", f"fps={fps},scale=360:-2")
    figs = "\n".join(f'<figure><img src="frames/{f.name}" loading="lazy"><figcaption><b>#{i}</b> {(i - 1) / fps:.1f}s</figcaption></figure>'
                     for i, f in enumerate(frames, 1))
    (out / "index.html").write_text(f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,"><title>{name}: every frame</title><style>
body{{margin:0;background:#F6F7F9;font-family:-apple-system,Helvetica,sans-serif;color:#111}}
h1{{font-size:20px;margin:20px 20px 4px}} p{{margin:0 20px 16px;color:#667;font-size:14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;padding:0 20px 40px}}
figure{{margin:0;background:#fff;border:1px solid #E3E6EA}} img{{width:100%;display:block}} figcaption{{padding:5px 7px;font-size:13px}}
</style></head><body><h1>Every frame, {fps:g} per second</h1>
<p>{len(frames)} frames. Tell Claude the numbers of the part you want, like "7 to 16".</p>
<div class="grid">{figs}</div></body></html>""")
    (out / "info.json").write_text(json.dumps({"video": str(video), "fps": fps, "frames": len(frames)}, indent=1))
    print(f"{len(frames)} frames: {out / 'index.html'}")
    print(f"On the style page: /refs/analysis/{name}-frames/index.html (frame N = {1 / fps:g} x (N - 1) seconds)")


def study(style, video, start, dur, fps, cols, width, crop):
    out_dir = style / "references" / "analysis" / "study"
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        vf = (f"crop={crop}," if crop else "") + f"fps={fps},scale={width}:-2"
        frames = extract(video, Path(tmp), vf, start, dur)
        if not frames:
            sys.exit("No frames in that range. Check the start time and length.")
        f = font(max(14, width // 9))
        ims = []
        for k, p in enumerate(frames):
            im = Image.open(p).convert("RGB")
            d = ImageDraw.Draw(im)
            label = f"{start + k / fps:.2f}"
            box = d.textbbox((0, 0), label, font=f)
            d.rectangle([0, 0, box[2] + 8, box[3] + 6], fill="white")
            d.text((4, 2), label, fill="red", font=f)
            ims.append(im)
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 3), rows * (h + 3)), "white")
    for k, im in enumerate(ims):
        sheet.paste(im, ((k % cols) * (w + 3), (k // cols) * (h + 3)))
    out = out_dir / f"{video.stem}-{start:g}s.jpg"
    sheet.save(out, quality=82)
    print(f"{len(ims)} frames from {start:g}s to {start + dur:g}s: {out}")


def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[0] not in ("gallery", "study", "when"):
        sys.exit(__doc__)
    cmd, style, video = a[0], Path(a[1]).expanduser(), Path(a[2]).expanduser()
    if not video.exists():
        sys.exit(f"Can't find the video: {video}")
    if cmd == "gallery":
        gallery(style, video, float(opt(a, "--fps", 2)))
    elif cmd == "when":
        print(f"frame {a[3]} = {(int(a[3]) - 1) / float(opt(a, '--fps', 2)):.2f} s")
    else:
        study(style, video, float(a[3]), float(a[4]), float(opt(a, "--fps", 12.5)), int(opt(a, "--cols", 12)),
              int(opt(a, "--width", 160)), opt(a, "--crop", None))


if __name__ == "__main__":
    main()
