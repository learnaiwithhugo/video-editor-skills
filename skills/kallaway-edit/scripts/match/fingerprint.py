#!/usr/bin/env python3
"""Measure a reel's editing style as numbers, and score an edit against the reference reels.

Usage (run with the engine's Python):
  fingerprint.py measure <video> [--out fp.json]          the numbers for one reel
  fingerprint.py spec <out spec.json> <ref.mp4> [...]      measure the references, write the allowed ranges
  fingerprint.py score <spec.json> <edit.mp4> [--out report.md]   PASS / FAIL per number, with what to fix

References and edits are measured by the same code, so any bias in the measuring cancels out. The
spec is the machine-readable half of a style: the style guide says it in words, the spec checks it.

What it measures (sampled at 12 fps unless noted):
  cuts_per_min, avg_shot_s, changes_per_s   every frame at 72x128 (hard cuts, plus smaller visual changes)
  stage_share, full_share, paper_share      layout per frame: the frame's lower-left margin is plain stage
                                            background in a "graphic above, face card below" layout
  card_top_pct, card_x0_pct                 where the face card starts (stage frames)
  stage_bg                                  the stage background colour (hex)
  cap_y_stage_pct, cap_y_full_pct           caption centre height as % of the frame, per layout
  cap_h_pct                                 caption text height (% of frame height), a stand-in for size
  cap_changes_per_s                         how fast the caption text changes (pace of chunks)
  red_share                                 share of strongly coloured stage pixels that are red
  lufs, true_peak                           loudness (EBU R128)
  stereo_sfx_per_min                        stereo-wide sound-effect hits (see prep.py)
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402
import prep  # noqa: E402

FW, FH, FPS = 270, 480, 12

# How far an edit may sit outside the references' own spread and still pass: (absolute, relative).
TOL = {
    "cuts_per_min": (2, 0.25), "avg_shot_s": (0.4, 0.25), "changes_per_s": (0.1, 0.3),
    "stage_share": (0.08, 0), "full_share": (0.08, 0), "paper_share": (0.06, 0),
    "card_top_pct": (1.0, 0), "card_x0_pct": (0.8, 0),
    "cap_y_stage_pct": (1.2, 0), "cap_y_full_pct": (2.0, 0), "cap_h_pct": (0.25, 0.1),
    "cap_changes_per_s": (0.3, 0.15), "red_share": (0.1, 0),
    "lufs": (1.0, 0), "true_peak": (1.0, 0), "stereo_sfx_per_min": (3, 0.3),
}
FIX = {
    "cuts_per_min": "cut more (or less) often: switch layout or stage scene on more sentence starts",
    "avg_shot_s": "shots run too long/short: add or remove layout switches and scene cuts",
    "changes_per_s": "add (or remove) beats inside scenes: a new element or camera move about every second",
    "stage_share": "spend more (or less) of the reel in the graphic layout",
    "full_share": "use more (or fewer) full-face breathers on connective lines",
    "paper_share": "the light 'paper' scenes are over- or under-used",
    "card_top_pct": "move the face card's top edge (style.json card.top)",
    "card_x0_pct": "change the face card's side margins (style.json card.x0/x1)",
    "cap_y_stage_pct": "move the caption in the graphic layout (style.json caption_y_stage)",
    "cap_y_full_pct": "move the caption in the full-face layout",
    "cap_h_pct": "make the caption text bigger or smaller (caption font size)",
    "cap_changes_per_s": "show fewer or more words per caption chunk",
    "red_share": "the accent colour is off: use the style's accent (or fewer other colours)",
    "lufs": "re-level the final mix",
    "true_peak": "the mix clips or sits too low: limit the master",
    "stereo_sfx_per_min": "sound effects are missing, too sparse, or mixed mono (the reference's are stereo)",
}


def classify(f):
    """'stage' (dark stage + card), 'paper' (light stage + card) or 'full', from the lower-left margin."""
    m = f[int(FH * 0.78):int(FH * 0.97), 0:int(FW * 0.04)].reshape(-1, 3).astype(int)
    mx, mn = m.max(1), m.min(1)
    if (mx < 22).mean() > 0.9:
        return "stage"
    if ((mn > 190) & (mx < 242) & (mx - mn < 18)).mean() > 0.9:
        return "paper"
    return "full"


def caption(f):
    """(centre y %, height %, mask signature) of the caption line in the 50-72 % band, or None."""
    y0, y1, x0, x1 = int(FH * 0.50), int(FH * 0.72), int(FW * 0.06), int(FW * 0.94)
    reg = f[y0:y1, x0:x1].astype(int)
    white = (reg.min(2) > 200) & (reg.max(2) - reg.min(2) < 40)
    rows = white.sum(1)
    best, run = None, None
    for i in range(len(rows) + 1):
        on = i < len(rows) and rows[i] >= 3
        if on and run is None:
            run = i
        if not on and run is not None:
            h = i - run
            if 4 <= h <= 30:
                cols = np.where(white[run:i].any(0))[0]
                if len(cols) >= 8:
                    bw = cols[-1] - cols[0] + 1
                    fill = white[run:i].sum() / (h * bw)
                    cx = x0 + (cols[0] + cols[-1]) / 2
                    if fill < 0.55 and abs(cx - FW / 2) < FW * 0.12:
                        score = white[run:i].sum()
                        if best is None or score > best[0]:
                            best = (score, run, i, cols[0], cols[-1])
            run = None
    if best is None:
        return None
    _, r0, r1, c0, c1 = best
    sig = white[r0:r1, c0:c1 + 1]
    return ((y0 + (r0 + r1) / 2) / FH * 100, (r1 - r0) / FH * 100, sig)


def same_caption(a, b):
    if a.shape != b.shape:
        return abs(a.shape[1] - b.shape[1]) <= max(2, 0.08 * max(a.shape[1], b.shape[1])) and \
               abs(a.shape[0] - b.shape[0]) <= 1
    return (a ^ b).mean() < 0.12


def measure(path):
    info = engine.probe(path)
    dur = info["duration"]
    _, cuts, events = prep.cut_scan(path, info)
    lay = {"stage": 0, "paper": 0, "full": 0}
    card_top, card_x0, bg, caps = [], [], [], {"stage": [], "full": []}
    cap_h, red, sat_n, changes, prev = [], 0, 0, 0, None
    for t, f in engine.frames(path, FW, FH, fps=FPS):
        l = classify(f)
        lay[l] += 1
        if l in ("stage", "paper"):
            band = f[int(FH * 0.6):, int(FW * 0.07):int(FW * 0.11)].astype(int)
            is_bg = band.max(2) < 24 if l == "stage" else (band.min(2) > 190)
            notbg = (~is_bg).mean(1) > 0.6
            hit = np.where(notbg)[0]
            if len(hit):
                card_top.append((FH * 0.6 + hit[0]) / FH * 100)
            row = f[int(FH * 0.9)].astype(int)
            rb = row.max(1) < 24 if l == "stage" else row.min(1) > 190
            nb = np.where(~rb)[0]
            if len(nb):
                card_x0.append(nb[0] / FW * 100)
            if l == "stage":
                bg.append(np.median(f[int(FH * 0.78):int(FH * 0.97), 0:int(FW * 0.04)].reshape(-1, 3), 0))
                top = f[int(FH * 0.03):int(FH * 0.62)].reshape(-1, 3).astype(float) / 255
                mx, mn = top.max(1), top.min(1)
                s = (mx - mn) / (mx + 1e-6)
                col = (s > 0.45) & (mx > 0.3)
                if col.any():
                    c = top[col]
                    r, g, b = c[:, 0], c[:, 1], c[:, 2]
                    red += int(((r > g * 1.8) & (r > b * 1.8)).sum())
                    sat_n += int(col.sum())
        cap = caption(f)
        if cap:
            caps["full" if l == "full" else "stage"].append(cap[0])
            cap_h.append(cap[1])
            if prev is not None and not same_caption(prev, cap[2]):
                changes += 1
            prev = cap[2]
    n = max(1, sum(lay.values()))
    aud = prep.audio_scan(path)
    loud = engine.loudness(path)
    med = lambda v: round(float(np.median(v)), 2) if v else None  # noqa: E731
    fp = {
        "file": str(path), "duration": round(dur, 2),
        "cuts_per_min": round(len(cuts) / dur * 60, 1), "avg_shot_s": round(dur / (len(cuts) + 1), 2),
        "changes_per_s": round((len(cuts) + len(events)) / dur, 2),
        "stage_share": round(lay["stage"] / n, 2), "full_share": round(lay["full"] / n, 2),
        "paper_share": round(lay["paper"] / n, 2),
        "card_top_pct": med(card_top), "card_x0_pct": med(card_x0),
        "stage_bg": "#%02X%02X%02X" % tuple(int(x) for x in np.median(bg, 0)) if bg else None,
        "cap_y_stage_pct": med(caps["stage"]), "cap_y_full_pct": med(caps["full"]),
        "cap_h_pct": med(cap_h), "cap_changes_per_s": round(changes / dur, 2),
        "red_share": round(red / sat_n, 2) if sat_n else None,
        "lufs": loud["lufs"], "true_peak": loud["true_peak"],
        "stereo_sfx_per_min": aud.get("stereo_sfx_per_min"), "mono_mix": aud.get("mono_mix"),
    }
    return fp


def make_spec(out, refs, fps=None):
    fps = fps or [measure(r) for r in refs]
    spec = {"refs": [fp["file"] for fp in fps], "measured": fps, "ranges": {}}
    for k, (ab, rel) in TOL.items():
        vals = [fp[k] for fp in fps if fp.get(k) is not None]
        if not vals:
            continue
        lo, hi = min(vals), max(vals)
        pad = max(ab, rel * (abs(lo) + abs(hi)) / 2)
        spec["ranges"][k] = {"lo": round(lo - pad, 2), "hi": round(hi + pad, 2), "refs": vals}
    spec["stage_bg_refs"] = [fp["stage_bg"] for fp in fps]
    Path(out).write_text(json.dumps(spec, indent=1))
    return spec


def score(spec_path, video):
    spec = json.loads(Path(spec_path).read_text())
    fp = measure(video)
    lines = [f"# Style match: {Path(video).name}", "",
             f"Against {len(spec['refs'])} reference reels. PASS = inside the references' range (plus a small "
             "tolerance).", "", "| Measure | This edit | Allowed | References | Result |", "|---|---|---|---|---|"]
    passed = total = 0
    fixes = []
    for k, r in spec["ranges"].items():
        v = fp.get(k)
        if v is None:
            res = "n/a"
        else:
            total += 1
            ok = r["lo"] <= v <= r["hi"]
            passed += ok
            res = "PASS" if ok else "FAIL"
            if not ok:
                fixes.append(f"- **{k}** is {v} (allowed {r['lo']} to {r['hi']}): {FIX.get(k, '')}")
        lines.append(f"| {k} | {v} | {r['lo']} to {r['hi']} | {', '.join(str(x) for x in r['refs'])} | {res} |")
    lines += ["", f"Stage background: this edit {fp['stage_bg']}, references {', '.join(map(str, spec['stage_bg_refs']))}",
              f"Mono mix: {fp['mono_mix']}", "", f"**Score: {passed}/{total} pass.**", ""]
    if fixes:
        lines += ["What to fix:", *fixes]
    return "\n".join(lines), fp


def main():
    a = sys.argv[1:]
    out = a[a.index("--out") + 1] if "--out" in a else None
    if "--out" in a:
        del a[a.index("--out"):a.index("--out") + 2]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "measure":
        fp = measure(a[1])
        txt = json.dumps(fp, indent=1)
        Path(out).write_text(txt) if out else print(txt)
    elif a[0] == "spec":
        spec = make_spec(a[1], a[2:])
        print(json.dumps(spec["ranges"], indent=1))
    elif a[0] == "score":
        txt, _ = score(a[1], a[2])
        if out:
            Path(out).write_text(txt)
        print(txt)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
