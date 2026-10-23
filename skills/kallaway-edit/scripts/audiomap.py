#!/usr/bin/env python3
"""Draw where every sound effect and the music sit against the voice, and check the voice stays on top.

Usage:
  PY scripts/audiomap.py <work_dir> [--out progress/NN-audio-map.png]

Rebuilds the three stems exactly as build.py placed them (voice = cut.mp4, effects from
build.json's cue list + their files/volumes, music with its ducking lane) and measures:
  - music under the voice: short-term loudness difference while he talks (target 18-24 dB)
  - every effect's peak against the voice's peak in the half second around it (target 10-16 dB under)
  - two hits on the same frame (should be none)
Writes a timeline PNG (voice envelope, music level, one labelled tick per effect) and prints a report.
Measured, not listened to: say so when you report it.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SK = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True  # never write into the skill folder: a plugin update replaces it
sys.path.insert(0, str(SK / "scripts"))
import sounds  # noqa: E402

SR = 16000


def pcm(cmd):
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def env_db(a, hop=0.05, win=0.4):
    h, w = int(SR * hop), int(SR * win)
    out = []
    for i in range(0, max(1, len(a) - w), h):
        out.append(10 * np.log10((a[i:i + w] ** 2).mean() + 1e-10))
    return np.array(out)


def main():
    args = sys.argv[1:]
    work = Path(args[0]).resolve()
    out = Path(args[args.index("--out") + 1]) if "--out" in args else work / "qa" / "audio-map.png"
    if not out.is_absolute():
        out = work / out
    b = json.loads((work / "build.json").read_text())
    plan = json.loads((work / "plan.json").read_text())
    D = b["duration"]
    n = int(D * SR)
    voice = pcm(["ffmpeg", "-v", "error", "-i", str(work / "cut.mp4"), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])[:n]
    lv = sounds.measure()
    sfx = np.zeros(n, dtype=np.float32)
    hits = []
    for c in b["sfx"]:
        f, win, hit, _pk, _pr = sounds.MAP[c["s"]]
        start = max(0.0, c["t"] - hit + 1 / 30) if c["s"] != "riser" else c["t"] - lv["riser"]["dur"]
        cmd = ["ffmpeg", "-v", "error"]
        if win:
            cmd += ["-ss", str(win[0]), "-t", str(win[1])]
        a = pcm(cmd + ["-i", str(sounds.LIB / f), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]) * c["vol"]
        i0 = int(start * SR)
        a = a[: max(0, n - i0)]
        sfx[i0:i0 + len(a)] += a
        # voice peak in the half second around the hit vs this effect's own peak
        lo, hi = int(max(0, c["t"] - 0.25) * SR), int(min(D, c["t"] + 0.25) * SR)
        vpk = 20 * np.log10(np.abs(voice[lo:hi]).max() + 1e-9)
        spk = 20 * np.log10(np.abs(a).max() + 1e-9)
        hits.append({"t": c["t"], "s": c["s"], "under_voice_db": round(vpk - spk, 1)})
    music = np.zeros(n, dtype=np.float32)
    mus = plan.get("music", {})
    lane = b.get("music_lane") or []
    if mus.get("on") and lane:
        m = pcm(["ffmpeg", "-v", "error", "-ss", str(mus.get("start", 0)), "-t", f"{D:.3f}", "-i", str(work / mus["file"]),
                 "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])[:n]
        t = np.arange(len(m)) / SR
        g = np.interp(t, [p["t"] for p in lane], [p["v"] for p in lane])
        music[:len(m)] = m * g
    ve, me, se = env_db(voice), env_db(music), env_db(sfx)
    talking = ve > -32
    under = (ve - me)[talking & (me > -80)]
    rep = []
    if len(under):
        rep.append(f"music under the voice while talking: median {np.median(under):.1f} dB, "
                   f"closest {np.percentile(under, 5):.1f} dB (target 18-24)")
    else:
        rep.append("music: off")
    hu = [h["under_voice_db"] for h in hits]
    if hu:
        rep.append(f"effects under the local voice peak: median {np.median(hu):.1f} dB, closest {min(hu):.1f} dB "
                   f"(target ~10-16); {len(hits)} effects")
        loud = [h for h in hits if h["under_voice_db"] < 8]
        for h in loud:
            rep.append(f"  ! {h['s']} at {h['t']:.2f}s only {h['under_voice_db']:.1f} dB under the voice")
    same = [(a["t"], b2["t"]) for a, b2 in zip(hits, hits[1:]) if b2["t"] - a["t"] < 2 / 30]
    rep.append(f"two hits on one frame: {len(same)}")

    # ---- the picture ----
    from PIL import Image, ImageDraw, ImageFont
    Wp, Hp, L = 2400, 760, 60
    img = Image.new("RGB", (Wp, Hp), (14, 14, 14))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=18)
    small = ImageFont.load_default(size=15)
    X = lambda t: L + (Wp - L - 20) * t / D
    Y = lambda db, top, h: top + h * (1 - (max(-60, min(0, db)) + 60) / 60)
    d.text((L, 10), "Audio map: voice (white), music after ducking (blue), sound effects (red ticks, labelled)", fill=(230, 230, 230), font=font)
    top, h = 50, 380
    for db in (0, -20, -40, -60):
        y = Y(db, top, h); d.line([(L, y), (Wp - 20, y)], fill=(40, 40, 40)); d.text((8, y - 8), f"{db}", fill=(120, 120, 120), font=small)
    for arr, col in ((ve, (235, 235, 235)), (me, (90, 150, 255))):
        pts = [(X(i * 0.05), Y(v, top, h)) for i, v in enumerate(arr)]
        d.line(pts, fill=col, width=2)
    for s in b.get("shots", []):
        x = X(s["t0"]); d.line([(x, top), (x, top + h)], fill=(70, 70, 70))
        d.text((x + 3, top + h + 4), s["layout"], fill=(130, 130, 130), font=small)
    rows = {}
    for hh in hits:
        x = X(hh["t"])
        row = 0
        while rows.get(row, -1e9) > x - 70:
            row += 1
        rows[row] = x
        y0 = top + h + 30 + row * 36
        d.line([(x, top + h - 30), (x, y0)], fill=(196, 21, 20), width=2)
        d.text((x + 3, y0), f"{hh['s']}", fill=(255, 120, 110), font=small)
    for t in range(0, int(D) + 1, 2):
        d.text((X(t) - 6, Hp - 24), f"{t}s", fill=(140, 140, 140), font=small)
    d.text((Wp - 760, 10), " | ".join(rep[:1] + [r for r in rep[1:2]])[:110], fill=(180, 180, 180), font=small)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    (work / "qa").mkdir(exist_ok=True)
    (work / "qa" / "audio-report.txt").write_text("\n".join(rep) + "\n")
    print("\n".join(rep)); print(out)


if __name__ == "__main__":
    main()
