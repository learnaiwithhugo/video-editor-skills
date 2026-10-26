#!/usr/bin/env python3
"""Build and update the rounds on the style page (page/round.json). The page only ever shows what's
still in play: drops leave the page for good, keeps stay, maybes stay until they're fixed.

Usage (STYLE = the style folder):
  make_round.py STYLE fonts "Switzer" "General Sans" "Geist" "Instrument Sans" "Helvetica Neue" [--title T]
      A font round: the same line with the same clean rise in each font (fonts are downloaded locally).
  make_round.py STYLE first
      Prints the catalogue (every section round 1 could be built from, with its options) and writes NOTHING.
      Round 1 comes from the person's brief, never from the whole library.
  make_round.py STYLE first --sections "Default captions" "Accent text" ... [--title T] [--intro "one line"]
      Round 1 with ONLY the sections named (names from the catalogue, case-insensitive), in the order given, already
      in their colours and font. A wrong name stops with the list of valid ones. --skip "<Section>" ... still works:
      on its own it builds the whole library minus those sections (the old way, kept for compatibility).
  make_round.py STYLE next [--title T] [--intro "one line"]
      Reads reviews/latest.json and starts the next round: Drops are removed (kept on record in
      round.json "dropped" and STYLE.md's rejected list), Keeps stay and are recorded in locked/kept.json,
      Maybes stay with their notes for you to fix. Prints what to fix. The old round is archived in page/rounds/.
      The round's notes, title and intro belong to ONE round: next clears them (set the new ones with the flags
      above or with round-notes).
  make_round.py STYLE round-notes "line" ["line" ...] [--title T] [--intro "one line"]
      What changed since last round, one short line each (shown at the top of the page). With only --title /
      --intro it leaves the notes alone.
  make_round.py STYLE section-note "<Section>" "<one line>"       what that section is for (shown under its heading)
  make_round.py STYLE add "<Section>" <library id> ['{"param": 1}'] ["Label"]
  make_round.py STYLE set <option id> '{"param": 1}' ["New label"]       (tweak an option, e.g. a Maybe)
  make_round.py STYLE remove <option id> ["why"]                          (the person dropped it in chat)
  make_round.py STYLE keep-only "<Section>" <option id> [<option id> ...] (everything else in that section goes)
  make_round.py STYLE lock <option id> <shine|zoom|shadow|text_fade>
      Saves a KEPT option's settings as locked/<name>.json, in the format the old lab pages saved and
      edit-my-video's style.py reads (the old lock goes to locked/old/). Says what is missing when the option
      can't become that lock: shine <- intro-shine, zoom <- zoom-long-out / zoom-quick-punch / zoom-hard-punch,
      shadow <- shadow, text_fade <- text-fade.
  make_round.py STYLE show                                                (what's on the page now)
"""
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


def load(p, d):
    return json.loads(p.read_text()) if p.exists() else d


class Round:
    def __init__(self, style):
        self.style = style
        self.path = style / "page" / "round.json"
        self.r = load(self.path, {"round": 0, "sections": [], "dropped": []})
        self.r.setdefault("dropped", [])

    def options(self):
        return [(s, o) for s in self.r["sections"] for o in s["options"]]

    def find(self, oid):
        for s, o in self.options():
            if o["id"] == oid:
                return s, o
        raise SystemExit(f"No option {oid} on the page. Run: make_round.py STYLE show")

    def section(self, name, code=None):
        for s in self.r["sections"]:
            if s["name"].lower() == name.lower():
                return s
        s = {"name": name, "code": code or "".join(w[0] for w in name.split()).upper()[:2], "options": []}
        self.r["sections"].append(s)
        return s

    def new_id(self, sec):
        n, code = self.r["round"], sec.get("code", "X")
        used = {o["id"] for _, o in self.options()} | {d["id"] for d in self.r["dropped"]}
        k = 1
        while f"R{n}-{code}{k}" in used:
            k += 1
        return f"R{n}-{code}{k}"

    def add(self, sec_name, use, params=None, label=None, code=None):
        sec = self.section(sec_name, code)
        o = {"id": self.new_id(sec), "use": use, "params": params or {}}
        if label:
            o["label"] = label
        sec["options"].append(o)
        return o

    def drop(self, oid, why="", rnd=None):
        sec, o = self.find(oid)
        sec["options"].remove(o)
        self.r["dropped"].append({**o, "section": sec["name"], "why": why, "round": rnd or self.r["round"]})

    def save(self):
        self.r["sections"] = [s for s in self.r["sections"] if s["options"]]
        self.r["updated"] = datetime.now().isoformat(timespec="seconds")
        self.path.write_text(json.dumps(self.r, indent=1))

    def archive(self):
        if self.path.exists():
            d = self.style / "page" / "rounds"
            d.mkdir(exist_ok=True)
            shutil.copy2(self.path, d / f"round-{self.r['round']}.json")


def catalogue():
    return json.loads((SK / "engine" / "first-round.json").read_text())


def library_labels():
    """Plain names for library ids (read from the page's library.js), so the catalogue reads in words."""
    import re
    try:
        text = (SK / "engine" / "page" / "library.js").read_text()
    except OSError:
        return {}
    return dict(re.findall(r'def\("([^"]+)",\s*\{\s*section:\s*"[^"]*",\s*label:\s*"([^"]*)"', text))


def print_catalogue():
    names = library_labels()
    print("Round 1 is built from the person's brief, only the sections they asked for:\n"
          '  make_round.py STYLE first --sections "<Section>" "<Section>" ...\n'
          "Nothing was written. The catalogue (each section, then its options as: name [library id and settings]):\n")
    for sec in catalogue():
        n = len(sec["options"])
        print(f"{sec['name']}  ({n} option{'s' if n != 1 else ''})" + (f"\n    for: {sec['use']}" if sec.get("use") else ""))
        for item in sec["options"]:
            use, params, label = (item + [None, None])[:3]
            print(f"    - {label or names.get(use) or use}  [{use}{' ' + json.dumps(params) if params else ''}]")
    print("\nGive each section you use a one-line job:  make_round.py STYLE section-note \"<Section>\" \"<what it's for>\"")


def split_flags(args, flags):
    """Words -> (loose words, {flag: [words after it, up to the next --flag]}). Only the flags listed are flags."""
    loose, got, cur = [], {}, None
    for a in args:
        if a in flags:
            cur = a
            got.setdefault(cur, [])
        elif cur:
            got[cur].append(a)
        else:
            loose.append(a)
    return loose, got


def set_headline(R, flags):
    """--title / --intro belong to the round that is on the page now."""
    for flag, key in (("--title", "title"), ("--intro", "intro")):
        if flag in flags and flags[flag]:
            R.r[key] = " ".join(flags[flag]).strip()


def first(style, sections=(), skip=(), flags=None):
    cat = catalogue()
    valid = [c["name"] for c in cat]
    by_name = {n.lower(): c for n, c in zip(valid, cat)}
    wanted = []
    for name in sections:
        if name.lower() not in by_name:
            raise SystemExit(f"There is no section called '{name}'. The sections are:\n  " + "\n  ".join(valid))
        if by_name[name.lower()] not in wanted:
            wanted.append(by_name[name.lower()])
    skipped = {x.lower() for x in skip}
    for x in skipped - set(by_name):
        print(f"Note: --skip '{x}' isn't a section name, ignored. (The sections are: {', '.join(valid)})")
    if not wanted:
        print("Note: no --sections given, so this builds the WHOLE library minus --skip (the old way). "
              "Round 1 should normally come from the person's brief: --sections \"<Section>\" ...")
        wanted = cat
    wanted = [c for c in wanted if c["name"].lower() not in skipped]
    if not wanted:
        raise SystemExit("Nothing left to build: every section was skipped.")
    R = Round(style)
    R.archive()
    R.r = {"round": 1, "sections": [], "dropped": R.r.get("dropped", [])}
    for sec in wanted:
        for item in sec["options"]:
            use, params, label = (item + [None, None])[:3]
            R.add(sec["name"], use, params, label, sec["code"])
        if sec.get("use"):
            R.section(sec["name"])["use"] = sec["use"]
    set_headline(R, flags or {})
    R.save()
    print(f"Round 1 written: {len(R.options())} options in {len(R.r['sections'])} sections ({', '.join(c['name'] for c in wanted)})."
          + (f" Left out: {', '.join(sorted(skipped & set(by_name)))}." if skipped & set(by_name) else ""))


def fonts(style, names, flags=None):
    import brand
    R = Round(style)
    R.archive()
    R.r = {"round": 0, "title": "Fonts", "sections": [], "dropped": R.r.get("dropped", [])}
    set_headline(R, flags or {})
    for name in names:
        info = brand.font_source(name)
        css = ""
        if info["source"] != "system":
            slug = name.lower().replace(" ", "-")
            brand.download_font(name, style / "page" / "assets" / "fonts" / slug)
            css = f"assets/fonts/{slug}/fonts.css"
        R.add("Fonts", "font-compare", {"family": info["family"], "css": css}, info["family"], "F")
        print(f"  {info['family']}: {info['source']} ({info['licence']})")
    R.save()
    print(f"Font round written: {len(names)} fonts.")


def nxt(style, flags=None):
    R = Round(style)
    rev = load(style / "reviews" / "latest.json", None)
    if not rev:
        raise SystemExit("No review yet. The person needs to press Submit review on the page first.")
    if str(rev.get("round")) != str(R.r["round"]):
        print(f"WARNING: the latest review is for round {rev.get('round')}, the page is on round {R.r['round']}. "
              "They may have submitted from an old tab. Ask before acting on it.")
    R.archive()
    kept_path = style / "locked" / "kept.json"
    kept = load(kept_path, [])
    on_page = {o["id"] for _, o in R.options()}
    keeps, maybes, drops, unrated = [], [], [], []
    for item in rev["options"]:
        if item["id"] not in on_page:
            continue
        v, note = item.get("verdict"), (item.get("note") or "").strip()
        sec, o = R.find(item["id"])
        if item.get("label") and not o.get("label"):
            o["label"] = item["label"]
        if note:
            o["note"] = note
        if v == "drop":
            drops.append(item)
            R.drop(item["id"], note, rev.get("round"))
        elif v == "keep":
            keeps.append(item)
            o["kept"] = True
            o.pop("fix", None)
            kept = [k for k in kept if k["id"] != o["id"]] + [{"id": o["id"], "section": sec["name"], "use": o["use"], "params": o.get("params", {}),
                                                               "label": item.get("label") or o.get("label"), "note": note, "kept_at": datetime.now().isoformat(timespec="seconds")}]
        elif v == "maybe":
            maybes.append(item)
            o["fix"] = note or "(no note: ask what's off)"
        else:
            unrated.append(item)
    R.r["round"] = (R.r["round"] or 0) + 1
    for key in ("title", "intro", "notes"):   # these describe ONE round
        R.r.pop(key, None)
    set_headline(R, flags or {})
    R.save()
    kept_path.parent.mkdir(parents=True, exist_ok=True)
    kept_path.write_text(json.dumps(kept, indent=1))
    show_list = lambda xs: "\n".join(f"  {x['id']} {x.get('section', '')} / {x.get('label') or x.get('use', '')}" + (f"  NOTE: {x['note']}" if x.get("note") else "") for x in xs) or "  none"
    print(f"Now on round {R.r['round']}.\nKEEP ({len(keeps)}):\n{show_list(keeps)}\nMAYBE, fix these ({len(maybes)}):\n{show_list(maybes)}"
          f"\nDROP, gone for good ({len(drops)}):\n{show_list(drops)}\nNOT RATED ({len(unrated)}):\n{show_list(unrated)}")
    print("\nNotes on Keeps and unrated options can still ask for changes. Read every note above.")


def show(style):
    R = Round(style)
    print(f"Round {R.r['round']}" + (f" ({R.r['title']})" if R.r.get("title") else ""))
    if R.r.get("intro"):
        print(f"Intro: {R.r['intro']}")
    for n in R.r.get("notes", []):
        print(f"Changed: {n}")
    for s in R.r["sections"]:
        print(f"{s['name']}:" + (f"  ({s['use']})" if s.get("use") else ""))
        for o in s["options"]:
            tags = (" KEPT" if o.get("kept") else "") + (f" LOCKED({o['locked']})" if o.get("locked") else "") + (f" FIX: {o['fix']}" if o.get("fix") else "")
            print(f"  {o['id']:8} {o.get('label') or o['use']}  [{o['use']} {json.dumps(o.get('params', {}))}]{tags}")
    print(f"Dropped so far: {len(R.r['dropped'])}")


# ---------------------------------------------------------------- lock: a kept option becomes locked/<name>.json
SMOOTH = [0.65, 0, 0.35, 1]      # the long face zoom's curve (slow at both ends)
EXPO = [0.16, 1, 0.3, 1]         # the quick punch-in's curve (fast, then settles)
LOCK_NAMES = ("shine", "zoom", "shadow", "text_fade")
TEXT_FADE_MOTION = {"rise_px": 42, "duration_ms": 820, "easing": "cubic-bezier(.19,1,.22,1)", "stagger_ms": 200}


def hex_rgb(h):
    h = str(h).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def bezier_css(curve):
    return "cubic-bezier(" + ", ".join(f"{float(n):.2f}".rstrip("0").rstrip(".") for n in curve) + ")"


def parse_bezier(text):
    import re
    m = re.fullmatch(r"\s*cubic-bezier\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)\s*", str(text))
    return [float(x) for x in m.groups()] if m else None


def brand_of(style):
    b = load(style / "locked" / "brand.json", None)
    if not b or not b.get("colours", {}).get("accent"):
        raise SystemExit("There is no brand yet (locked/brand.json). Run brand.py first, the locks use the person's colours.")
    c = b["colours"]
    return b, {"paper": c.get("paper", "#FFFFFF"), "accent": c["accent"], "soft": c.get("accent_soft", c["accent"]),
               "deep": c.get("accent_deep", c["accent"]), "ink": c.get("ink", "#10203A"), "text": b.get("caption_colour", "#FFFFFF")}


def cannot(o, name, needs):
    raise SystemExit(f"{o['id']} ('{o['use']}') can't become a {name} lock: {needs}")


def lock_shine(o, brand, c):
    p = o.get("params", {})
    shine_keys = ("width", "strength", "soft", "glow", "angle", "gap", "ease", "shine", "base")
    if o["use"] != "intro-shine" and not any(k in p for k in shine_keys):
        cannot(o, "shine", "a shine lock comes from an 'intro-shine' option (the hero word shine). A custom option works too if its "
                           "params carry the shine settings: width, strength, soft, glow, angle, dur, gap, ease, shine (band colour), base (text colour).")
    lines = brand.get("lines", {}).get("intro") or []
    return {"size": p.get("heroSize", p.get("size", 240)), "width": p.get("width", 14), "strength": p.get("strength", 70),
            "soft": p.get("soft", 45), "glow": p.get("glow", 0), "angle": p.get("angle", 100), "dur": p.get("dur", 1400),
            "gap": p.get("gap", 900), "ease": p.get("ease", "cubic-bezier(.45,0,.2,1)"),
            "shine": str(p.get("shine", c["text"])).upper(), "base": str(p.get("base", c["accent"])).upper(),
            "sample_word": p.get("sample_word") or (lines[1] if len(lines) > 1 else "edit")}


def lock_zoom(o, brand, c):
    p = o.get("params", {})
    use = o["use"]
    if use == "zoom-long-out":
        d = {"dir": "out", "amount": round(float(p.get("from", 1.2)) * 100), "dur": int(p.get("dur", 3500)), "hold": 800, "out": "same", "curve": list(SMOOTH)}
    elif use == "zoom-quick-punch":
        dur = int(p.get("dur", 750))
        d = {"dir": "in", "amount": round(float(p.get("to", 1.15)) * 100), "dur": dur, "hold": max(0, 1500 - dur), "out": "cut", "curve": list(EXPO)}
    elif use == "zoom-hard-punch":
        d = {"dir": "in", "amount": round(float(p.get("to", 1.15)) * 100), "dur": 150, "hold": 1350, "out": "cut", "curve": list(EXPO)}
    elif "amount" in p and "dur" in p:
        d = {"dir": p.get("dir", "out"), "amount": int(p["amount"]), "dur": int(p["dur"]), "hold": int(p.get("hold", 800)), "out": p.get("out", "same"),
             "curve": list(p.get("curve") or SMOOTH)}
    else:
        cannot(o, "zoom", "a zoom lock comes from a zoom-long-out, zoom-quick-punch or zoom-hard-punch option (or a custom one whose params "
                          "carry amount and dur, plus optionally dir, hold, out, curve).")
    curve = p.get("curve") if isinstance(p.get("curve"), list) and len(p["curve"]) == 4 else (parse_bezier(p.get("ease") or p.get("easing")) if (p.get("ease") or p.get("easing")) else None)
    if curve:
        d["curve"] = [float(n) for n in curve]
    d["easing"] = bezier_css(d["curve"])
    # edit-my-video's style.py reads from / to / ease (not the lab's amount / easing) for the main face zoom: write both.
    z = d["amount"] / 100
    d["from"], d["to"], d["ease"] = (z, 1.0, d["easing"]) if d["dir"] == "out" else (1.0, z, d["easing"])
    return d


def parse_shadow(css):
    import re
    layers, depth, cur = [], 0, ""
    for ch in css:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            layers.append(cur)
            cur = ""
        else:
            cur += ch
    layers.append(cur)
    num = r"(-?\d+(?:\.\d+)?)(?:px)?"
    out = []
    for lyr in layers:
        m = re.fullmatch(rf"\s*{num}\s+{num}\s+{num}\s+rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)\s*", lyr)
        if not m:
            return None
        x, y, blur, r, g, b, a = m.groups()
        out.append({"x": float(x), "y": float(y), "blur": float(blur), "rgb": f"{r},{g},{b}", "alpha": float(a if a is not None else 1)})
    return out


def lock_shadow(o, brand, c):
    p = o.get("params", {})
    if o["use"] != "shadow" and "css" not in p:
        cannot(o, "shadow", "a shadow lock comes from a 'shadow' option (white text drop shadows), whose params hold the css text-shadow.")
    css = str(p.get("css", "")).strip()
    if not css:
        cannot(o, "shadow", "its params have no 'css' text-shadow.")
    d = {"size": p.get("size", 84), "text_shadow": css, "frame_width": 1080}
    if css.lower() == "none":
        d.update({"rgb": "0,0,0", "blur": 0, "alpha": 0, "y": 0, "edge": 0, "edgeBlur": 0})
        return d
    layers = parse_shadow(css)
    if layers:   # the lab's own sliders: the last layer is the spread, a first extra layer is the crisp edge
        main = layers[-1]
        d.update({"rgb": main["rgb"], "blur": round(main["blur"]), "alpha": round(main["alpha"] * 100), "y": round(main["y"]),
                  "edge": round(layers[0]["alpha"] * 100) if len(layers) > 1 else 0, "edgeBlur": round(layers[0]["blur"]) if len(layers) > 1 else 2})
    return d


def lock_text_fade(o, brand, c):
    p = o.get("params", {})
    if o["use"] != "text-fade":
        cannot(o, "text_fade", "a text_fade lock comes from a 'text-fade' option (a title that melts away). (text-fade-locked just plays an existing lock.)")
    frm = {"ink": c["ink"], "deep": c["deep"], "accent": c["accent"], "text": c["text"]}.get(p.get("from", "ink"))
    if not frm:
        cannot(o, "text_fade", f"its 'from' is '{p.get('from')}', expected ink, deep, accent or text.")
    to = {"paper": "bg", "accent": "accent", "soft": "soft", "white": "white", "clear": "clear", "bg": "bg"}.get(p.get("to", "paper"))
    if not to:
        cannot(o, "text_fade", f"its 'to' is '{p.get('to')}', expected paper, accent or soft.")
    end = int(p.get("end", 100))
    target = {"bg": (*hex_rgb(c["paper"]), 1), "accent": (*hex_rgb(c["accent"]), 1), "soft": (*hex_rgb(c["soft"]), 1),
              "white": (255, 255, 255, 1), "clear": (*hex_rgb(frm), 0)}[to]
    k, (tr, tg, tb, ta), (fr, fg, fb) = end / 100, target, hex_rgb(frm)
    a = k * ta + (1 - k)
    if a <= 0:
        bottom = f"rgba({fr},{fg},{fb},0)"
    else:
        m = lambda t, f: round((k * ta * t + (1 - k) * f) / a)
        bottom = f"rgba({m(tr, fr)},{m(tg, fg)},{m(tb, fb)},{round(a, 3):g})"
    start = int(p.get("start", 52))
    lines = p.get("lines") or (brand.get("lines", {}).get("title") if len(brand.get("lines", {}).get("title") or []) >= 2 else None)
    intro = brand.get("lines", {}).get("intro") or []
    sample = list(lines[:2]) if lines else ([intro[1], intro[2]] if len(intro) >= 3 else ["Content", "Architecture"])
    weight = str(brand.get("font", {}).get("weights", {}).get("title", 700))
    return {"bg": "paper", "from": frm.upper(), "to": to, "start": start, "end": end, "only": "no", "size": p.get("size", 210), "top": p.get("top", 730),
            "weight": weight, "track": -45, "shadow": "off",
            "background_image": f"linear-gradient(180deg, {frm.upper()} 0%, {frm.upper()} {start}%, {bottom} 100%)",
            "sample": sample, "frame_width": 1080, "motion": dict(TEXT_FADE_MOTION)}


def lock(style, oid, name):
    name = name.lower().replace("-", "_")
    if name not in LOCK_NAMES:
        raise SystemExit(f"Don't know a lock called '{name}'. The locks are: {', '.join(LOCK_NAMES)}")
    R = Round(style)
    try:
        sec, o = R.find(oid)
        on_page = True
    except SystemExit:
        o = next((k for k in load(style / "locked" / "kept.json", []) if k["id"] == oid), None)
        if not o:
            raise
        sec, on_page = {"name": o.get("section", "")}, False
    brand, c = brand_of(style)
    if not o.get("kept"):
        print(f"Note: {oid} isn't marked Keep yet. Locking it anyway because you asked; check the person agreed.")
    data = {"zoom": lock_zoom, "shine": lock_shine, "shadow": lock_shadow, "text_fade": lock_text_fade}[name](o, brand, c)
    data["locked_at"] = datetime.now().isoformat(timespec="seconds")
    data["from_option"] = oid
    folder = style / "locked"
    (folder / "old").mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.json"
    if path.exists():
        shutil.move(str(path), str(folder / "old" / f"{name}-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.json"))
        print("The previous lock went to locked/old/.")
    path.write_text(json.dumps(data, indent=2))
    if on_page:
        o["locked"] = name
        R.save()
    summary = {
        "zoom": lambda d: f"{'starts at' if d['dir'] == 'out' else 'zooms in to'} {d['amount']}%, {d['dur'] / 1000:.2f}s on {d['easing']}"
                          + ("" if d["dir"] == "out" else f", holds {d['hold'] / 1000:.2f}s, then hard-cuts back"),
        "shine": lambda d: f"{d['base']} text with a {d['shine']} band, {d['width']}% wide, {d['dur'] / 1000:.2f}s sweep, {d['gap'] / 1000:.2f}s between sweeps",
        "shadow": lambda d: f"text-shadow: {d['text_shadow']} (captions {d['size']}px on a 1080 wide frame)",
        "text_fade": lambda d: f"{d['from']} solid down to {d['start']}%, then {d['background_image'].rsplit(', ', 1)[1].split(' ')[0]} at the bottom of each line, {d['size']}px",
    }[name](data)
    print(f"Locked {oid} ({sec['name']} / {o.get('label') or o['use']}) as locked/{name}.json: {summary}.")
    if name == "zoom" and data["dir"] == "in":
        print("Note: this is a punch-in, not the long face zoom. edit-my-video's style.py applies a zoom lock's timing to the MAIN "
              "face zoom, so lock a punch only if that is what they want the main zoom to be.")
    print('Next: style_md.py "STYLE" to refresh the guide\'s auto blocks.')


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    style, cmd, rest = Path(os.path.expanduser(a[0])).resolve(), a[1], a[2:]
    if cmd == "first":
        loose, flags = split_flags(rest, {"--sections", "--skip", "--title", "--intro"})
        if loose:
            raise SystemExit(f"Didn't understand '{' '.join(loose)}'. Name the sections after --sections, for example:\n"
                             '  make_round.py STYLE first --sections "Default captions" "Accent text"')
        if not flags.get("--sections") and not flags.get("--skip"):
            print_catalogue()
            return
        first(style, flags.get("--sections", []), flags.get("--skip", []), flags)
    elif cmd == "fonts":
        names, flags = split_flags(rest, {"--title", "--intro"})
        fonts(style, names, flags)
    elif cmd == "next":
        nxt(style, split_flags(rest, {"--title", "--intro"})[1])
    elif cmd == "show":
        show(style)
    elif cmd == "lock":
        if len(rest) != 2:
            raise SystemExit("Usage: make_round.py STYLE lock <option id> <shine|zoom|shadow|text_fade>")
        lock(style, rest[0], rest[1])
    elif cmd == "round-notes":
        lines, flags = split_flags(rest, {"--title", "--intro"})
        R = Round(style)
        if lines:
            R.r["notes"] = [x.strip() for x in lines if x.strip()]
        elif not flags:
            raise SystemExit('Usage: make_round.py STYLE round-notes "what changed" ["what changed" ...] [--title T] [--intro "..."]')
        set_headline(R, flags)
        R.save()
        print(f"Round {R.r['round']}: {len(R.r.get('notes', []))} note(s)" + (f", title '{R.r['title']}'" if R.r.get("title") else "") + ".")
    elif cmd == "section-note":
        if len(rest) != 2:
            raise SystemExit('Usage: make_round.py STYLE section-note "<Section>" "<one line on what it is for>"')
        R = Round(style)
        sec = next((x for x in R.r["sections"] if x["name"].lower() == rest[0].lower()), None)
        if not sec:
            raise SystemExit(f"There is no section called '{rest[0]}' on the page. The sections are: " + ", ".join(x["name"] for x in R.r["sections"]))
        sec["use"] = rest[1].strip()
        R.save()
        print(f"{sec['name']}: {sec['use']}")
    else:
        R = Round(style)
        if cmd == "add":
            o = R.add(rest[0], rest[1], json.loads(rest[2]) if len(rest) > 2 and rest[2] else {}, rest[3] if len(rest) > 3 else None)
            print(f"added {o['id']}")
        elif cmd == "set":
            _, o = R.find(rest[0])
            o["params"] = {**o.get("params", {}), **json.loads(rest[1])}
            if len(rest) > 2:
                o["label"] = rest[2]
            o.pop("fix", None)
            print(f"updated {o['id']}: {json.dumps(o['params'])}")
        elif cmd == "remove":
            R.drop(rest[0], rest[1] if len(rest) > 1 else "")
            print(f"removed {rest[0]}")
        elif cmd == "keep-only":
            sec = R.section(rest[0])
            for o in list(sec["options"]):
                if o["id"] not in rest[1:]:
                    R.drop(o["id"], "not picked when the person chose " + ", ".join(rest[1:]))
            print(f"{rest[0]}: kept {', '.join(rest[1:])}")
        else:
            raise SystemExit(__doc__)
        R.save()


if __name__ == "__main__":
    main()
