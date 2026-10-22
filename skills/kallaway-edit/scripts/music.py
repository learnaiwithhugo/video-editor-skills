#!/usr/bin/env python3
"""Pick a quiet background track: free and legal (CC0 / CC BY from Openverse) or the user's own.

Usage:
  PY scripts/music.py <work_dir>                       # search Openverse, pick one
  PY scripts/music.py <work_dir> --file "/path/song.mp3"   # use your own track
  PY scripts/music.py <work_dir> --query "lofi beat" --pick 2   # another search / candidate
  PY scripts/music.py <work_dir> --off                 # no music (plan.json music.on=false)

Writes <work_dir>/music/track.<ext>, <work_dir>/music/track.json (title, creator, licence, link,
loudness, the start offset to use) and <work_dir>/music-credit.txt (paste it into the caption when
the licence is CC BY; CC0 needs no credit, the line is there as a courtesy). Updates plan.json "music".

How it picks: Openverse search (no account, no key), CC0 and CC BY only (never NC/SA/ND), at least
reel length + 10 s, then for up to 4 candidates it downloads the preview and measures: loudness
range (steady beats dramatic), whether Whisper hears any words (vocals are rejected), and the
steadiest stretch to start from. CC0 wins ties. It cannot judge taste: say what was picked, and let
the user swap it with --pick N or --file.
"""
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

QUERIES = ["lofi beat", "chill lofi instrumental", "minimal chill electronic"]
UA = {"User-Agent": "video-editor-plugin/1.0 (free reel editor for Claude Code)"}


def get_json(url):
    """Openverse is free but can be slow or rate limited: curl with retries; {} if it stays down."""
    r = subprocess.run(["curl", "-sS", "--retry", "3", "--retry-delay", "3", "--max-time", "60", "-A",
                        UA["User-Agent"], url], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"  (Openverse didn't answer for this search: {r.stderr.strip()[:80]})")
        return {}


def download(url, dst):
    """Freesound previews can be slow: curl with retries (always on a Mac), urllib as a fallback."""
    try:
        subprocess.run(["curl", "-sSL", "--retry", "3", "--max-time", "300", "-A", UA["User-Agent"], "-o", str(dst),
                        url], check=True)
        return
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        dst.write_bytes(r.read())


def analyse(path, need):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null",
                          "-"], capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
    lra = float(re.search(r"LRA:\s+(-?[\d.]+) LU", tail).group(1))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    w = 8000  # 1 s windows
    rms = np.array([10 * np.log10((a[i:i + w] ** 2).mean() + 1e-12) for i in range(0, len(a) - w, w)])
    # steadiest stretch of `need` seconds that is also near the track's full level
    best, start = 1e9, 0
    full = np.percentile(rms, 75)
    for s in range(0, max(1, len(rms) - need)):
        seg = rms[s:s + need]
        score = seg.std() + max(0, full - seg.mean())
        if score < best:
            best, start = score, s
    return {"lufs": lufs, "lra": lra, "start": float(start), "steadiness": round(float(best), 2)}


def has_words(path):
    from faster_whisper import WhisperModel
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-t", "90", "-ac", "1", "-ar", "16000", "-f",
                          "f32le", "-"], capture_output=True).stdout
    m = WhisperModel("small.en", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(np.frombuffer(raw, dtype=np.float32).copy(), language="en", vad_filter=True)
    return any(s.no_speech_prob < 0.5 and len(s.text.strip()) > 8 for s in segs)


def set_plan(work, music):
    p = work / "plan.json"
    plan = json.loads(p.read_text()) if p.exists() else {}
    plan["music"] = music
    p.write_text(json.dumps(plan, indent=1))


def main():
    args = sys.argv[1:]
    work = Path(args[0]).resolve()
    mdir = work / "music"; mdir.mkdir(exist_ok=True)
    if "--off" in args:
        set_plan(work, {"on": False}); print("Music off."); return
    reel = json.loads((work / "segments.json").read_text())["duration"]
    need = int(reel) + 2
    if "--file" in args:
        src = Path(args[args.index("--file") + 1]).expanduser().resolve()
        dst = mdir / f"track{src.suffix.lower()}"
        dst.write_bytes(src.read_bytes())
        info = {"title": src.stem, "creator": "your own track", "license": "yours", "link": "", **analyse(dst, need)}
    else:
        queries = [args[args.index("--query") + 1]] if "--query" in args else QUERIES
        pick = int(args[args.index("--pick") + 1]) if "--pick" in args else 1
        seen, cands = set(), []
        for q in queries:
            url = ("https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode(
                {"q": q, "license": "cc0,by", "page_size": 20}))
            for r in get_json(url).get("results", []):
                d = (r.get("duration") or 0) / 1000
                if r["id"] in seen or r.get("license") not in ("cc0", "by") or d < reel + 10 or d > 600:
                    continue
                tags = " ".join(t["name"].lower() for t in (r.get("tags") or []))
                if re.search(r"vocal|voice|sing|rap|horror|dark|epic|trailer", tags + " " + r["title"].lower()):
                    continue
                seen.add(r["id"]); cands.append(r)
        if not cands:
            sys.exit("No free track found. Drop your own song in and run with --file.")
        print(f"Checking {min(4, len(cands))} free tracks ...", flush=True)
        scored = []
        for r in cands[:4]:
            f = mdir / f"cand-{r['id'][:8]}.mp3"
            try:
                download(r["url"], f)
            except Exception as e:  # noqa: BLE001  a dead link just drops the candidate
                print(f"  skip {r['title']}: {e}"); continue
            a = analyse(f, need)
            if has_words(f):
                print(f"  skip {r['title']}: has vocals"); continue
            score = a["lra"] + a["steadiness"] + (0 if r["license"] == "cc0" else 1.5)
            scored.append((score, r, f, a))
            print(f"  {r['title']} ({r['license']}) LRA {a['lra']} LU, steadiness {a['steadiness']}")
        if not scored:
            sys.exit("Every candidate had vocals or failed to download. Try --query or --file.")
        scored.sort(key=lambda x: x[0])
        _, r, f, a = scored[min(pick, len(scored)) - 1]
        dst = mdir / "track.mp3"
        dst.write_bytes(f.read_bytes())
        for _, _, g, _ in scored:
            g.unlink(missing_ok=True)
        info = {"title": r["title"], "creator": r.get("creator", ""), "license": r["license"],
                "license_url": r.get("license_url", ""), "link": r.get("foreign_landing_url", ""), **a}
    (mdir / "track.json").write_text(json.dumps(info, indent=1))
    lic = {"cc0": "CC0 (public domain, no credit needed)", "by": "CC BY 4.0 (credit required)"}.get(
        info["license"], info["license"])
    credit = f'Music: "{info["title"]}" by {info["creator"]}, {lic}. {info.get("link", "")}'.strip()
    (work / "music-credit.txt").write_text(credit + "\n")
    set_plan(work, {"on": True, "file": f"music/{dst.name}", "start": info["start"], "lufs": info["lufs"]})
    print(f"Music: {info['title']} by {info['creator']} ({info['license']}), starts {info['start']:.0f} s in.\n"
          f"Credit line saved to music-credit.txt")


if __name__ == "__main__":
    main()
