#!/usr/bin/env python3
"""Sound effects for the style: find them in the person's own library or fetch free ones on their Mac,
clean them up, and keep sfx/sfx.json (the list the Sounds page plays and the editor reads).

Usage (STYLE = the style folder):
  sfx.py scan "<their sound folder>" [--need whoosh]
      Lists audio files by what they probably are (cut, rise, blur, shine, tick, panel, icon, click, hero),
      shortest first. Nothing is copied or changed.
  sfx.py add STYLE "<file>" --need cut --name "Shutter crunch" [--source "<path or link>"] [--licence "..."]
        [--mix -12] [--max 2.5]
      Copies it in as sfx/NN-<need>-<name>.wav: trims the silence before the sound, short fades, peak at
      -1 dB, 48 kHz 24-bit. The original is only read. --mix is how loud it sits in an edit (dB under the
      file's peak); the default per need is very quiet on purpose.
  sfx.py fetch STYLE "<direct download link>" --need shine --name "..." --licence "..."
      Downloads a free sound into sfx/downloads/ on THIS Mac, then runs add. Never bundle third-party sounds.
  sfx.py level STYLE <file> <dB>        sfx.py drop STYLE <file> ["why"]        sfx.py pick STYLE <file> ...
  sfx.py apply-review STYLE             apply the Keep / Drop marks sent from the Sounds page
  sfx.py list STYLE

Needs: cut (hard cuts, punch-ins), rise (clean rise), blur (blur rise), shine, tick (rings, ticks),
panel (a panel sliding over the face), icon (app icons rising), click (mouse clicks, lines drawing), hero (hero word).
"""
import array
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

NEEDS = ["cut", "rise", "blur", "shine", "tick", "panel", "icon", "click", "hero"]
# Default levels: barely noticeable under a voice at about -16 LUFS. If you can clearly hear it, it's too loud.
DEFAULT_MIX = {"cut": -8, "rise": -16, "blur": -16, "shine": -18, "tick": -12, "panel": -16, "icon": -12, "click": -10, "hero": -16}
WORDS = {
    "cut": ["shutter", "camera", "snap", "cut", "crunch"],
    "rise": ["swoosh", "swish", "rise", "riser", "up"],
    "blur": ["whoosh", "woosh", "wooshe", "air", "breath", "soft"],
    "shine": ["shine", "sparkle", "glint", "shimmer", "sweep", "magic", "twinkle", "metal"],
    "tick": ["tick", "ui", "pop", "check", "blip", "tap"],
    "panel": ["whoosh", "woosh", "swoosh", "slide", "transition", "swipe"],
    "icon": ["tap", "click", "pop", "soft", "bubble"],
    "click": ["click", "mouse", "keyboard", "type"],
    "hero": ["drop", "thump", "impact", "deep", "boom", "hit", "bass"],
}
AUDIO = {".wav", ".mp3", ".aif", ".aiff", ".m4a", ".flac", ".ogg"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ffmpeg failed: {r.stderr[-500:]}")
    return r


def duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def lst(style):
    p = style / "sfx" / "sfx.json"
    return json.loads(p.read_text()) if p.exists() else []


def save(style, data):
    (style / "sfx" / "sfx.json").write_text(json.dumps(data, indent=1))


def scan(folder, only=None):
    folder = Path(os.path.expanduser(folder))
    files = [p for p in folder.rglob("*") if p.suffix.lower() in AUDIO]
    print(f"{len(files)} audio files in {folder}\n")
    for need in ([only] if only else NEEDS):
        hits = [p for p in files if any(w in p.stem.lower() for w in WORDS.get(need, [need]))]
        hits = sorted(((duration(p), p) for p in hits[:200]), key=lambda x: x[0])
        hits = [(d, p) for d, p in hits if 0.05 < d < 6][:12]
        if hits:
            print(f"{need}:")
            for d, p in hits:
                print(f"  {d:5.2f}s  {p}")


def peak_time(wav):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2])
    if not a:
        return 0.0
    i = max(range(len(a)), key=lambda k: abs(a[k]))
    return round(i / 8000, 3)


def add(style, src, need, name, source=None, licence=None, mix=None, maxlen=2.5):
    if need not in NEEDS:
        raise SystemExit(f"need must be one of {NEEDS}")
    src = Path(os.path.expanduser(src))
    if not src.exists():
        raise SystemExit(f"Can't find {src}")
    data = lst(style)
    n = max([int(m.group(1)) for d in data if (m := re.match(r"(\d+)-", d["file"]))] + [0]) + 1
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30]
    out = style / "sfx" / f"{n:02d}-{need}-{slug}.wav"
    tmp = out.with_suffix(".tmp.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
         f"silenceremove=start_periods=1:start_threshold=-50dB,atrim=0:{maxlen},afade=t=in:d=0.004,areverse,afade=t=in:d=0.03,areverse",
         "-ar", "48000", "-c:a", "pcm_s24le", str(tmp)])
    vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", vol)
    gain = round(-1.0 - float(m.group(1)), 1) if m else 0.0
    run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", f"volume={gain}dB", "-ar", "48000", "-c:a", "pcm_s24le", str(out)])
    tmp.unlink()
    d, pk = round(duration(out), 3), peak_time(out)
    data.append({"file": out.name, "need": need, "name": name, "mix_db": mix if mix is not None else DEFAULT_MIX[need], "picked": False,
                 "source": source or str(src), "licence": licence or "the person's own library", "duration_s": d, "peak_s": pk,
                 "hit_s": pk if need in ("cut", "tick", "click", "icon") else None, "gain_db": gain})
    save(style, data)
    print(f"added {out.name}: {d}s, peak at {pk}s, sits at {data[-1]['mix_db']} dB in an edit")


def fetch(style, url, need, name, licence):
    dl = style / "sfx" / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    fn = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("?")[0].split("/")[-1]) or "sound.wav"
    dst = dl / fn
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            dst.write_bytes(r.read())
    except (urllib.error.URLError, OSError) as e:   # a wrong id answers 403/404; no internet answers URLError
        raise SystemExit(f"Couldn't download that sound ({e}). Check the link is right and the internet is on, then try another sound.")
    add(style, dst, need, name, source=url, licence=licence)


def find(data, f):
    for d in data:
        if d["file"] == f:
            return d
    raise SystemExit(f"No sound called {f}. Run: sfx.py list STYLE")


def drop(style, f, why=""):
    data = lst(style)
    d = find(data, f)
    data.remove(d)
    old = style / "sfx" / "old"
    old.mkdir(exist_ok=True)
    if (style / "sfx" / f).exists():
        shutil.move(str(style / "sfx" / f), old / f)
    rec = old / "dropped.json"
    gone = json.loads(rec.read_text()) if rec.exists() else []
    rec.write_text(json.dumps(gone + [{**d, "why": why, "dropped_at": datetime.now().isoformat(timespec="seconds")}], indent=1))
    save(style, data)
    print(f"dropped {f} (moved to sfx/old/)")


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    cmd = a[0]
    if cmd == "scan":
        return scan(a[1], opt("--need"))
    style = Path(os.path.expanduser(a[1])).resolve()
    (style / "sfx").mkdir(parents=True, exist_ok=True)
    if cmd == "add":
        add(style, a[2], opt("--need"), opt("--name", Path(a[2]).stem), opt("--source"), opt("--licence"),
            float(opt("--mix")) if opt("--mix") else None, float(opt("--max", 2.5)))
    elif cmd == "fetch":
        fetch(style, a[2], opt("--need"), opt("--name", "sound"), opt("--licence", "free licence (check the site)"))
    elif cmd == "level":
        data = lst(style); find(data, a[2])["mix_db"] = float(a[3]); save(style, data); print(f"{a[2]} now sits at {a[3]} dB")
    elif cmd == "pick":
        data = lst(style)
        for f in a[2:]:
            find(data, f)["picked"] = True
        save(style, data); print("picked " + ", ".join(a[2:]))
    elif cmd == "drop":
        drop(style, a[2], a[3] if len(a) > 3 else "")
    elif cmd == "apply-review":
        rev = json.loads((style / "reviews" / "latest-sfx.json").read_text())
        data = lst(style)
        for o in rev["options"]:
            if o["verdict"] == "keep" and any(d["file"] == o["id"] for d in data):
                find(data, o["id"])["picked"] = True
        save(style, data)
        for o in rev["options"]:
            if o["verdict"] == "drop" and any(d["file"] == o["id"] for d in lst(style)):
                drop(style, o["id"], "dropped on the Sounds page")
        print("picked: " + (", ".join(d["file"] for d in lst(style) if d.get("picked")) or "none yet"))
    elif cmd == "list":
        for d in lst(style):
            print(f"{'*' if d.get('picked') else ' '} {d['file']:34} {d['need']:6} {d['mix_db']:>5} dB  {d['name']}  [{d['licence']}]")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
