#!/usr/bin/env python3
"""Find the free font that best matches a reference reel's captions, by pixels, not by guessing.

Usage (run with the engine's Python):
  font_match.py <reel.mp4> <words.json> <out_dir> [--samples 10] [--fonts intertight,inter,...]

It cuts real caption words out of the reel (white text in the caption band), renders the same words
in free Google Fonts (OFL, downloaded once into the editor's data folder, DATA/fonts/) at several weights and letter
spacings, and scores the overlap of the letter shapes (1.0 = identical). Writes:
  <out_dir>/font-match.md    ranking: font, weight, tracking, score
  <out_dir>/font-match.png   each sample next to the top 3 fonts, to check by eye
Helvetica (Mac system font, NOT free to give away) is scored as a benchmark only.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402
import fingerprint  # noqa: E402

FONTS = {  # google/fonts path -> file
    "intertight": "InterTight[wght].ttf", "inter": "Inter[opsz,wght].ttf", "archivo": "Archivo[wdth,wght].ttf",
    "manrope": "Manrope[wght].ttf", "figtree": "Figtree[wght].ttf", "instrumentsans": "InstrumentSans[wdth,wght].ttf",
    "hankengrotesk": "HankenGrotesk[wght].ttf", "schibstedgrotesk": "SchibstedGrotesk[wght].ttf",
    "onest": "Onest[wght].ttf", "geist": "Geist[wght].ttf", "publicsans": "PublicSans[wght].ttf",
    "worksans": "WorkSans[wght].ttf",
}
BENCH = ("helvetica-neue (benchmark, not free)", "/System/Library/Fonts/HelveticaNeue.ttc")
CACHE = engine.state().FONTS  # the editor's data folder, never the skill folder
WEIGHTS, TRACKS = (700, 800, 900), (-0.06, -0.045, -0.03, -0.015, 0.0)


def fetch(name):
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / FONTS[name]
    if not dst.exists():
        url = ("https://raw.githubusercontent.com/google/fonts/main/ofl/" + name + "/" +
               FONTS[name].replace("[", "%5B").replace("]", "%5D"))
        urllib.request.urlretrieve(url, dst)
    return dst


def load(path, size, weight):
    if str(path).endswith(".ttc"):  # Helvetica Neue: index 1 = Bold, 10 ~ Condensed Black; use Bold
        return ImageFont.truetype(str(path), size, index=1)
    f = ImageFont.truetype(str(path), size)
    try:
        axes = f.get_variation_axes()
        vals = []
        for a in axes:
            nm = a.get("name", b"")
            nm = nm.decode() if isinstance(nm, bytes) else str(nm)
            if "eight" in nm:
                vals.append(min(max(weight, a["minimum"]), a["maximum"]))
            elif "ptical" in nm:
                vals.append(min(max(32, a["minimum"]), a["maximum"]))  # display optical size
            else:
                vals.append(a["default"])
        f.set_variation_by_axes(vals)
    except Exception:
        pass
    return f


def ink(mask):
    ys, xs = np.where(mask)
    return mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else None


def render(text, path, weight, track, height):
    def draw(size):
        f = load(path, size, weight)
        w = int(sum(f.getlength(c) for c in text) + size * 2)
        im = Image.new("L", (w, int(size * 2)), 0)
        d, x = ImageDraw.Draw(im), size * 0.3
        for c in text:
            d.text((x, size * 0.3), c, font=f, fill=255)
            x += f.getlength(c) + track * size
        return ink(np.array(im) > 127)
    m = draw(200)
    if m is None:
        return None
    m2 = draw(max(8, int(round(200 * height / m.shape[0]))))
    return m2


def iou(a, b):
    h, w = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    pa, pb = np.zeros((h, w), bool), np.zeros((h, w), bool)
    pa[(h - a.shape[0]) // 2:(h - a.shape[0]) // 2 + a.shape[0], (w - a.shape[1]) // 2:(w - a.shape[1]) // 2 + a.shape[1]] = a
    pb[(h - b.shape[0]) // 2:(h - b.shape[0]) // 2 + b.shape[0], (w - b.shape[1]) // 2:(w - b.shape[1]) // 2 + b.shape[1]] = b
    return (pa & pb).sum() / max(1, (pa | pb).sum())


def samples(reel, words, n):
    """Caption crops (full-res masks) with the words that could be on screen."""
    found = []
    for t, small in engine.frames(reel, fingerprint.FW, fingerprint.FH, fps=2):
        cap = fingerprint.caption(small)
        if not cap:
            continue
        i = max([k for k, w in enumerate(words) if w["start"] <= t] or [0])
        near = [words[k]["w"].strip() for k in range(max(0, i - 1), min(len(words), i + 2))]
        cands = set(near) | {f"{x} {y}" for x, y in zip(near, near[1:])}
        cands |= {c.rstrip(".,!?") + p for c in list(cands) for p in ("", ",", ".")}
        found.append((t, cap[0], cap[1], [c for c in cands if c.replace(" ", "").strip(".,!?\"'").isalpha()]))
    found = [f for f in found if f[3]]
    pick = [found[int(k)] for k in np.linspace(0, len(found) - 1, min(n, len(found)))] if found else []
    out = []
    for t, yc, hh, cands in pick:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(reel), "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        img = np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3).astype(int)
        y0, y1 = int((yc - hh * 1.2) / 100 * 1920), int((yc + hh * 1.2) / 100 * 1920)
        band = img[y0:y1, 60:1020]
        m = ink((band.min(2) > 200) & (band.max(2) - band.min(2) < 40))
        if m is not None and m.shape[0] > 12:
            out.append((t, m, cands))
    return out


def main():
    a = sys.argv[1:]
    n = int(a[a.index("--samples") + 1]) if "--samples" in a else 10
    names = a[a.index("--fonts") + 1].split(",") if "--fonts" in a else list(FONTS)
    reel, words, out = Path(a[0]), json.loads(Path(a[1]).read_text()), Path(a[2])
    out.mkdir(parents=True, exist_ok=True)
    fonts = [(nm, fetch(nm)) for nm in names]
    if Path(BENCH[1]).exists():
        fonts.append(BENCH)
    smp = samples(reel, words, n)
    print(f"{len(smp)} caption samples")
    table = {}
    best_renders = {}
    for nm, path in fonts:
        for wt in (WEIGHTS if not str(path).endswith(".ttc") else (700,)):
            for tr in TRACKS:
                scores, rends = [], []
                for t, m, cands in smp:
                    best = (0, None)
                    for c in cands:
                        r = render(c, path, wt, tr, m.shape[0])
                        if r is not None:
                            s = iou(m, r)
                            best = max(best, (s, r), key=lambda x: x[0])
                    scores.append(best[0])
                    rends.append(best[1])
                table[(nm, wt, tr)] = scores
                best_renders[(nm, wt, tr)] = rends
    # A sample only counts when some font really matches it (the right words were found on screen).
    valid = [k for k in range(len(smp)) if max(s[k] for s in table.values()) >= 0.6]
    print(f"{len(valid)} of {len(smp)} samples matched their words")
    table = {key: float(np.mean([s[k] for k in valid])) if valid else 0 for key, s in table.items()}
    smp = [smp[k] for k in valid]
    best_renders = {key: [r[k] for k in valid] for key, r in best_renders.items()}
    per_font = {}
    for (nm, wt, tr), s in table.items():
        if s > per_font.get(nm, (0,))[0]:
            per_font[nm] = (s, wt, tr)
    rank = sorted(per_font.items(), key=lambda x: -x[1][0])
    lines = ["# Caption font match", "", f"Reel: {reel.name}, {len(smp)} caption words. Score = overlap of the "
             "letter shapes (1.0 = identical).", "", "| Rank | Font | Weight | Tracking (em) | Score |",
             "|---|---|---|---|---|"]
    for k, (nm, (s, wt, tr)) in enumerate(rank, 1):
        lines.append(f"| {k} | {nm} | {wt} | {tr} | {s:.3f} |")
    (out / "font-match.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    top = [(nm, wt, tr) for nm, (s, wt, tr) in rank[:3]]
    rows = []
    for k, (t, m, _) in enumerate(smp[:6]):
        cells = [m] + [best_renders[key][k] for key in top]
        hmax = max(c.shape[0] for c in cells if c is not None)
        row = Image.new("L", (sum((c.shape[1] if c is not None else 10) + 30 for c in cells), hmax + 20), 0)
        x = 10
        for c in cells:
            if c is not None:
                row.paste(Image.fromarray((c * 255).astype(np.uint8)), (x, 10))
                x += c.shape[1] + 30
        rows.append(row)
    if rows:
        sheet = Image.new("L", (max(r.width for r in rows), sum(r.height for r in rows) + 40), 40)
        d = ImageDraw.Draw(sheet)
        d.text((10, 8), "reference | " + " | ".join(f"{nm} {wt}" for nm, wt, _ in top), fill=255, font=engine.font(22))
        y = 40
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height
        sheet.save(out / "font-match.png")


if __name__ == "__main__":
    main()
