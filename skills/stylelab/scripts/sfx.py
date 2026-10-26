#!/usr/bin/env python3
"""Sound effects for the style: find them in the person's own library, fetch free ones on their Mac
(Openverse, Mixkit), or make them in code (Earshot). Cleans them up and keeps sfx/sfx.json (the list the
Sounds tab plays and the editor reads).

Usage (STYLE = the style folder):
  sfx.py scan "<their sound folder>" [--need whoosh]
      Lists audio files by what they probably are (cut, rise, blur, shine, tick, panel, icon, click, hero),
      shortest first. Nothing is copied or changed.
  sfx.py feel STYLE [barely|noticeable|punchy] [--all]
      How their sounds should feel. Sets the level of every sound that hasn't been adjusted by hand
      (--all: every sound) and is the starting level for every sound added after. No word: shows the current one.
  sfx.py add STYLE "<file>" --need cut --name "Shutter crunch" [--source "<path or link>"] [--licence "..."]
        [--mix -12] [--max 2.5]
      Copies it in as sfx/NN-<need>-<name>.wav: trims the silence before the sound, short fades, peak at
      -1 dB, 48 kHz 24-bit. The original is only read. --mix is how loud it sits in an edit (dB under the
      file's peak); without it the level comes from the feel above. Works on any audio file, including one
      Earshot made (pass --licence "Made in code with Earshot (MIT), no credit needed").
  sfx.py openverse STYLE ["<what to search>"] --need click [--n 4] [--max-seconds 3] [--licence cc0|by]
        [--source freesound] [--pages 3]
      Searches Openverse (api.openverse.org, free, no account), keeps clips under --max-seconds, downloads
      them to sfx/downloads/ on THIS Mac and adds them as candidates with licence, source link and creator.
      cc0 only by default (no credit needed). --licence by also allows CC BY: then a credit is required and
      the attribution line is stored (sfx.py credits STYLE prints the ones to paste into the post).
  sfx.py fetch STYLE "<direct download link>" --need shine --name "..." --licence "..."
      Downloads a free sound (e.g. Mixkit) into sfx/downloads/ on THIS Mac, then runs add.
      Never bundle third-party sounds.
  sfx.py earshot-help
      Prints, in plain English, how to install Earshot and make sounds in code (always ask first).
  sfx.py level STYLE <file> <dB>        sfx.py drop STYLE <file> ["why"]        sfx.py pick STYLE <file> ...
  sfx.py apply-review STYLE             apply the Keep / Drop marks sent from the Sounds tab
  sfx.py credits STYLE                  credit lines for picked sounds that need one (CC BY)
  sfx.py list STYLE

Needs: cut (hard cuts, punch-ins), rise (clean rise), blur (blur rise), shine, tick (rings, ticks),
panel (a panel sliding over the face), icon (app icons rising), click (mouse clicks, lines drawing), hero (hero word).
"""
import array
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

NEEDS = ["cut", "rise", "blur", "shine", "tick", "panel", "icon", "click", "hero"]
# Neutral starting levels: dB under each file's peak (every file is stored with its peak at -1 dB), for a
# voice at about -16 LUFS. This is "noticeable": you hear it, but the voice stays in front. "barely there" and
# "punchy" shift the whole set by FEEL (below). Nobody's taste is built in: the person answers, we set it.
DEFAULT_MIX = {"cut": -6, "rise": -10, "blur": -10, "shine": -12, "tick": -8, "panel": -10, "icon": -8, "click": -8, "hero": -8}
FEEL = {"barely": -6, "noticeable": 0, "punchy": 4}          # dB added to DEFAULT_MIX (negative = quieter)
FEEL_WORDS = {"barely": "barely there", "noticeable": "noticeable", "punchy": "punchy"}
MIX_CEILING = -2                                              # nothing ever sits above -2 dB under its peak
DEFAULT_QUERY = {"cut": "camera shutter", "rise": "swoosh", "blur": "air whoosh", "shine": "sparkle", "tick": "ui tick",
                 "panel": "slide whoosh", "icon": "soft pop", "click": "mouse click", "hero": "deep impact"}
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
# Titles like "Mouse clicks" or "Whoosh pack" are usually several sounds in one file, which is no good for one moment.
PACKISH = re.compile(r"\b(pack|packs|collection|compilation|loops?|variations|multiple|series|sounds|clicks|whooshes|swooshes|"
                     r"hits|sfx set|set of|assorted|various|library)\b", re.I)
AUDIO = {".wav", ".mp3", ".aif", ".aiff", ".m4a", ".flac", ".ogg"}
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
      "Version/17.0 Safari/605.1.15 StyleLab/1.0")
OPENVERSE = "https://api.openverse.org/v1/audio/"
EARSHOT_HOME = Path.home() / "earshot"


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


def feel_of(style):
    try:
        f = json.loads((style / "sfx" / "feel.json").read_text()).get("feel")
    except (OSError, ValueError):
        f = None
    return f if f in FEEL else "noticeable"


def default_mix(style, need):
    return float(min(MIX_CEILING, DEFAULT_MIX[need] + FEEL[feel_of(style)]))


def set_feel(style, word, everything=False):
    """Save how their sounds should feel and move every sound that hasn't been adjusted by hand."""
    w = word.lower().strip()
    key = next((k for k in FEEL if w.startswith(k[:6]) or w.startswith(FEEL_WORDS[k][:6])), None)
    if key is None and w in ("subtle", "quiet", "soft", "low"):
        key = "barely"
    if key is None and w in ("loud", "strong", "bold", "big"):
        key = "punchy"
    if key is None:
        raise SystemExit("Pick one: barely there, noticeable, or punchy.")
    (style / "sfx").mkdir(parents=True, exist_ok=True)
    (style / "sfx" / "feel.json").write_text(json.dumps({"feel": key, "set_at": datetime.now().isoformat(timespec="seconds")}, indent=1))
    data, moved = lst(style), 0
    for d in data:
        if d["need"] in DEFAULT_MIX and (everything or not d.get("mix_custom")):
            d["mix_db"] = default_mix(style, d["need"])
            if everything:
                d.pop("mix_custom", None)
            moved += 1
    save(style, data)
    table = ", ".join(f"{n} {default_mix(style, n):g}" for n in NEEDS)
    print(f"feel: {FEEL_WORDS[key]}. Levels (dB under each sound's peak): {table}. Moved {moved} sound(s).")


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


def add(style, src, need, name, source=None, licence=None, mix=None, maxlen=2.5, extra=None):
    if need not in NEEDS:
        raise SystemExit(f"need must be one of {NEEDS}")
    src = Path(os.path.expanduser(src))
    if not src.exists():
        raise SystemExit(f"Can't find {src}")
    data = lst(style)
    n = max([int(m.group(1)) for d in data if (m := re.match(r"(\d+)-", d["file"]))] + [0]) + 1
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30].strip("-")
    out = style / "sfx" / f"{n:02d}-{need}-{slug}.wav"
    raw, tmp = out.with_suffix(".raw.wav"), out.with_suffix(".tmp.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", f"silenceremove=start_periods=1:start_threshold=-50dB,atrim=0:{maxlen}",
         "-ar", "48000", "-c:a", "pcm_f32le", str(raw)])
    fade_out = max(0.002, min(0.03, duration(raw) * 0.15))          # a tiny click must not be faded away
    run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", f"afade=t=in:d=0.004,areverse,afade=t=in:d={fade_out:.4f},areverse",
         "-ar", "48000", "-c:a", "pcm_f32le", str(tmp)])      # float until the peak is set: a hot MP3 can decode above 0 dBFS
    raw.unlink()
    st = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp), "-af", "astats=measure_perchannel=none:measure_overall=Peak_level",
                         "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.findall(r"Peak level dB:\s*(-?[\d.]+)", st)
    gain = math.floor((-1.0 - float(m[-1])) * 100) / 100 if m else 0.0     # rounds down: the peak is never above -1 dB
    run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", f"volume={gain}dB", "-ar", "48000", "-c:a", "pcm_s24le", str(out)])
    tmp.unlink()
    d, pk = round(duration(out), 3), peak_time(out)
    entry = {"file": out.name, "need": need, "name": name, "mix_db": mix if mix is not None else default_mix(style, need), "picked": False,
             "source": source or str(src), "licence": licence or "the person's own library", "duration_s": d, "peak_s": pk,
             "hit_s": pk if need in ("cut", "tick", "click", "icon") else None, "gain_db": gain}
    if mix is not None:
        entry["mix_custom"] = True
    entry.update(extra or {})
    data.append(entry)
    save(style, data)
    print(f"added {out.name}: {d}s, peak at {pk}s, sits at {entry['mix_db']:g} dB in an edit")
    return entry


def download(url, dst, max_bytes=8_000_000):
    """Download one file with a real User-Agent, logged out. Network errors (including HTTP 429) are raised for the caller."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise OSError("file is bigger than 8 MB, so it isn't a short effect")
    dst.write_bytes(body)


def fetch(style, url, need, name, licence):
    dl = style / "sfx" / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    fn = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("?")[0].split("/")[-1]) or "sound.wav"
    dst = dl / fn
    try:
        download(url, dst)
    except (urllib.error.URLError, OSError) as e:   # a wrong id answers 403/404; no internet answers URLError
        raise SystemExit(f"Couldn't download that sound ({e}). Check the link is right and the internet is on, then try another sound.")
    add(style, dst, need, name, source=url, licence=licence)


class Busy(Exception):
    def __init__(self, wait):
        self.wait = wait


def api_get(url):
    """One polite JSON call to Openverse. 429 raises Busy(seconds to wait); other failures are plain messages."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            left = r.headers.get("x-ratelimit-available-anon_sustained")
            return json.loads(r.read()), (int(left) if left and left.isdigit() else None)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            ra = e.headers.get("Retry-After", "")
            raise Busy(int(ra) if ra.isdigit() else 60)
        raise
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise SystemExit(f"Couldn't reach Openverse ({e}). Check the internet is on and try again, or use Mixkit or their own library.")


def busy_message(b, got):
    kept = f" The {got} sound(s) already added are kept." if got else ""
    return (f"Openverse asks us to slow down for a bit (free use is 20 searches a minute and 200 a day). "
            f"Wait about {b.wait} seconds and run the same line again.{kept} Mixkit or their own library work in the meantime.")


def clean_title(t, fallback):
    t = re.sub(r"\.(wav|mp3|flac|ogg|aiff?|m4a)$", "", (t or "").strip(), flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -_")
    if len(t) > 40:
        t = t[:40].rsplit(" ", 1)[0] if " " in t[:40] else t[:40]
    return t.strip(" ,;-_") or fallback


def openverse(style, query, need, n=4, max_seconds=3.0, licence="cc0", source="freesound", pages=3):
    if need not in NEEDS:
        raise SystemExit(f"Say which moment it's for: --need one of {NEEDS}")
    lic = {"cc0": "cc0", "by": "cc0,by"}.get(licence.lower())
    if lic is None:
        raise SystemExit("--licence is cc0 (default, no credit needed) or by (also allows CC BY, credit required).")
    have = {d.get("source_url") for d in lst(style)}
    found, seen, packs = [], set(), 0
    print(f'Searching Openverse for "{query}" ({lic.replace(",", " + ").upper()}, clips under {max_seconds:g}s) ...')
    for page in range(1, pages + 1):
        params = {"q": query[:200], "license": lic, "page_size": 20, "page": page, "filter_dead": "true", "mature": "false"}
        if source != "all":
            params["source"] = source
        try:
            res, left = api_get(OPENVERSE + "?" + urllib.parse.urlencode(params))
        except Busy as b:
            print(busy_message(b, 0)); return
        except urllib.error.HTTPError as e:
            if page > 1:
                break                              # asked for a page that doesn't exist
            raise SystemExit(f"Openverse said no ({e.code}). Try a simpler search word.")
        if left is not None and left < 15:
            print(f"(Heads up: only {left} free Openverse searches left today.)")
        for r in res.get("results", []):
            ms, url, landing = r.get("duration"), r.get("url"), r.get("foreign_landing_url") or r.get("detail_url")
            if not ms or not url or not url.startswith("http") or not (30 <= ms <= max_seconds * 1000):
                continue
            key = ((r.get("creator") or "").lower(), (r.get("title") or "").lower())
            if landing in have or key in seen:
                continue
            if PACKISH.search(r.get("title") or ""):
                packs += 1
                continue
            seen.add(key)
            found.append(r)
            if len(found) >= n:
                break
        if len(found) >= n or page >= (res.get("page_count") or 1):
            break
        time.sleep(1.5)
    if packs:
        print(f"(Skipped {packs} that look like packs of several sounds in one file.)")
    if not found:
        print(f'Nothing short enough for "{query}". Try another word, --max-seconds 5, or --licence by (needs a credit).')
        return
    dl = style / "sfx" / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    added = 0
    for r in found:
        secs = r["duration"] / 1000
        ext = (r.get("filetype") or r["url"].split("?")[0].rsplit(".", 1)[-1] or "mp3").lower()
        dst = dl / f"openverse-{r['id'][:8]}.{re.sub(r'[^a-z0-9]', '', ext)[:4] or 'mp3'}"
        by = r.get("creator") or "unknown"
        print(f'- "{r.get("title")}" by {by}, {secs:.2f}s, {r["license"].upper()}')
        try:
            download(r["url"], dst)
        except (urllib.error.URLError, OSError) as e:
            code = getattr(e, "code", None)
            if code == 429:
                print(busy_message(Busy(60), added)); return
            print(f"  skipped (couldn't download: {e})")
            continue
        credit = r["license"].lower() != "cc0"
        ver = f" {r['license_version']}" if r.get("license_version") else ""
        label = (f"CC {r['license'].upper()}{ver} via Openverse (credit required)" if credit
                 else f"CC0{ver} public domain via Openverse (no credit needed)")
        add(style, dst, need, clean_title(r.get("title"), query), source=r.get("foreign_landing_url") or r["url"],
            licence=label, maxlen=max_seconds,
            extra={"source_url": r.get("foreign_landing_url") or r["url"], "download_url": r["url"], "creator": by,
                   "creator_url": r.get("creator_url"), "attribution": r.get("attribution") or "",
                   "attribution_required": credit, "licence_url": r.get("license_url"), "openverse_id": r["id"],
                   "query": query})
        added += 1
        time.sleep(1.0)
    print(f"{added} candidate(s) added for {need}. I can't hear them: they're picks by title and length. Have a listen on the Sounds tab.")
    if lic != "cc0":
        print("Some of these need a credit if used (CC BY). Run: sfx.py credits STYLE  after they pick.")


def credits(style):
    rows = [d for d in lst(style) if d.get("picked") and d.get("attribution_required")]
    if not rows:
        print("None of the picked sounds needs a credit.")
        return
    print("Paste these in the post caption or video description:\n")
    for d in rows:
        print(d.get("attribution") or f'"{d["name"]}" by {d.get("creator", "unknown")} ({d["licence"]}) {d.get("source_url", "")}')


def earshot_help():
    py = EARSHOT_HOME / ".venv" / "bin" / "python"
    print(f"""EARSHOT: sounds made in code (free, MIT licence, by Leon Lin). github.com/Leonxlnx/earshot
Version 0.4.0, released Oct 2026 and still marked alpha, so treat it as new. Always ask the person before installing.

What it gives them
  1. A built-in bank of 252 sound effects (whooshes, clicks, hits, pops, shutters, bells) that it draws in
     seconds from code. No recordings, no licence worries, no credit needed. Needs only the install below.
  2. A brand-new sound that it designs and checks by listening ("forge"). Needs one extra download:
     two listening models, about 1.1 GB, fetched the first time you use it.
  3. A whole "kit" of sounds in one go, from a preset (calm, crisp, minimal or launch).

Check first
  - An Apple Silicon Mac (M1 or newer). It runs on the processor, no graphics card needed. Intel Macs can't
    run the version of PyTorch it requires.
  - Python 3.10 to 3.12 (3.12 is the safe pick). Check with: python3 --version
  - ffmpeg is already here (the skill uses it too).
  - Don't run "pip install earshot": that name on PyPI is a different, unrelated project.

Install, one time (about 1 GB of disk for the code and its libraries; PyTorch alone is a 127 MB download)
  git clone https://github.com/Leonxlnx/earshot {EARSHOT_HOME}
  python3.12 -m venv {EARSHOT_HOME}/.venv
  {py} -m pip install torch
  {py} -m pip install -e {EARSHOT_HOME}
  {py} -m earshot doctor
  (Leave out "doctor --load" and "--fetch": they download the 1.1 GB models. Only forge needs those.)
Status here: {"installed at " + str(EARSHOT_HOME) if py.exists() else "not installed yet"}

Make sounds (E = {py} -m earshot)
  See what's in the bank:        E sfx list --kind whoosh        (also: click, tick, hit, pop, shimmer, riser)
  Make one, aimed at a moment:   E sfx render whoosh_fast/tight -o whoosh.wav --dur 0.8 --apex 0.3
  A whole kit (4 presets):       E kit init --preset calm -o kit.json
                                 E kit render kit.json --out kit        (takes + kit.lock.json in ./kit)
  Design a brand-new one:        E forge whoosh --mode designed --budget 96 --variants 4 --dir made/whoosh
                                 (first run downloads the models, then each run loads them for 20-40 seconds and
                                 searches; not timed. It writes WAVs, report.md and an audition.wav into that folder)
  See all recipes to forge:      E forge --list

Good starting points per moment (confirm names with E sfx list --kind <word>)
  cut   cut_hit/sub, shutter/dslr            rise  riser/dark, swish/bright
  blur  whoosh_fast/tight, whoosh_fast/heavy panel swipe/velvet, whoosh_big/swell
  shine mallet/glock, mallet/celesta         tick  fit/tick/domino, pro_hover_tick/soft
  icon  ui_pop/soft, pro_pop_in/round        click fit/click/floss_lid, pro_click/soft
  hero  whoosh_big/thump, cut_hit/sub

Then put what it made into the style (add trims, fades and sets the peak; pick the level with sfx.py feel):
  sfx.py add STYLE whoosh.wav --need blur --name "Soft whoosh" --licence "Made in code with Earshot (MIT), no credit needed"
""")


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
    if cmd == "earshot-help":
        return earshot_help()
    if len(a) < 2:
        raise SystemExit(__doc__)
    style = Path(os.path.expanduser(a[1])).resolve()
    (style / "sfx").mkdir(parents=True, exist_ok=True)
    if cmd == "add":
        add(style, a[2], opt("--need"), opt("--name", Path(a[2]).stem), opt("--source"), opt("--licence"),
            float(opt("--mix")) if opt("--mix") else None, float(opt("--max", 2.5)))
    elif cmd == "feel":
        words = [x for x in a[2:] if not x.startswith("--")]
        if not words:
            print(f"feel: {FEEL_WORDS[feel_of(style)]}")
        else:
            set_feel(style, " ".join(words), everything="--all" in a)
    elif cmd == "fetch":
        fetch(style, a[2], opt("--need"), opt("--name", "sound"), opt("--licence", "free licence (check the site)"))
    elif cmd == "openverse":
        need = opt("--need")
        if need not in NEEDS:
            raise SystemExit(f"Say which moment it's for: --need one of {NEEDS}")
        q = a[2] if len(a) > 2 and not a[2].startswith("--") else DEFAULT_QUERY[need]
        openverse(style, q, need, int(opt("--n", 4)), float(opt("--max-seconds", 3)), opt("--licence", "cc0"),
                  opt("--source", "freesound"), int(opt("--pages", 3)))
    elif cmd == "level":
        data = lst(style); d = find(data, a[2]); d["mix_db"] = float(a[3]); d["mix_custom"] = True; save(style, data); print(f"{a[2]} now sits at {a[3]} dB")
    elif cmd == "pick":
        data = lst(style)
        for f in a[2:]:
            find(data, f)["picked"] = True
        save(style, data); print("picked " + ", ".join(a[2:]))
    elif cmd == "drop":
        drop(style, a[2], a[3] if len(a) > 3 else "")
    elif cmd == "credits":
        credits(style)
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
        print(f"feel: {FEEL_WORDS[feel_of(style)]}")
        for d in lst(style):
            print(f"{'*' if d.get('picked') else ' '} {d['file']:34} {d['need']:6} {d['mix_db']:>5} dB  {d['name']}  [{d['licence']}]")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
