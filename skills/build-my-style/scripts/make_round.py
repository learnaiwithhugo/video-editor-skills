#!/usr/bin/env python3
"""Build and update the rounds on the style page (page/round.json). The page only ever shows what's
still in play: drops leave the page for good, keeps stay, maybes stay until they're fixed.

Usage (STYLE = the style folder):
  make_round.py STYLE fonts "Switzer" "General Sans" "Geist" "Instrument Sans" "Helvetica Neue"
      A font round: the same line with the same clean rise in each font (fonts are downloaded locally).
  make_round.py STYLE first
      Round 1: the whole animation library, already in their colours and font.
  make_round.py STYLE next
      Reads reviews/latest.json and starts the next round: Drops are removed (kept on record in
      round.json "dropped" and STYLE.md's rejected list), Keeps stay and are recorded in locked/kept.json,
      Maybes stay with their notes for you to fix. Prints what to fix. The old round is archived in page/rounds/.
  make_round.py STYLE add "<Section>" <library id> ['{"param": 1}'] ["Label"]
  make_round.py STYLE set <option id> '{"param": 1}' ["New label"]       (tweak an option, e.g. a Maybe)
  make_round.py STYLE remove <option id> ["why"]                          (the person dropped it in chat)
  make_round.py STYLE keep-only "<Section>" <option id> [<option id> ...] (everything else in that section goes)
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


def first(style):
    R = Round(style)
    R.archive()
    R.r = {"round": 1, "sections": [], "dropped": R.r.get("dropped", [])}
    for sec in json.loads((SK / "engine" / "first-round.json").read_text()):
        for item in sec["options"]:
            use, params, label = (item + [None, None])[:3]
            R.add(sec["name"], use, params, label, sec["code"])
    R.save()
    print(f"Round 1 written: {len(R.options())} options in {len(R.r['sections'])} sections.")


def fonts(style, names):
    import brand
    R = Round(style)
    R.archive()
    R.r = {"round": 0, "title": "Fonts", "sections": [], "dropped": R.r.get("dropped", [])}
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


def nxt(style):
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
                                                               "label": item.get("label"), "note": note, "kept_at": datetime.now().isoformat(timespec="seconds")}]
        elif v == "maybe":
            maybes.append(item)
            o["fix"] = note or "(no note: ask what's off)"
        else:
            unrated.append(item)
    R.r["round"] = (R.r["round"] or 0) + 1
    R.r.pop("title", None)
    R.save()
    kept_path.parent.mkdir(parents=True, exist_ok=True)
    kept_path.write_text(json.dumps(kept, indent=1))
    show_list = lambda xs: "\n".join(f"  {x['id']} {x['section']} / {x['label']}" + (f"  NOTE: {x['note']}" if x.get("note") else "") for x in xs) or "  none"
    print(f"Now on round {R.r['round']}.\nKEEP ({len(keeps)}):\n{show_list(keeps)}\nMAYBE, fix these ({len(maybes)}):\n{show_list(maybes)}"
          f"\nDROP, gone for good ({len(drops)}):\n{show_list(drops)}\nNOT RATED ({len(unrated)}):\n{show_list(unrated)}")
    print("\nNotes on Keeps and unrated options can still ask for changes. Read every note above.")


def show(style):
    R = Round(style)
    print(f"Round {R.r['round']}" + (f" ({R.r['title']})" if R.r.get("title") else ""))
    for s in R.r["sections"]:
        print(f"{s['name']}:")
        for o in s["options"]:
            tags = (" KEPT" if o.get("kept") else "") + (f" FIX: {o['fix']}" if o.get("fix") else "")
            print(f"  {o['id']:8} {o.get('label') or o['use']}  [{o['use']} {json.dumps(o.get('params', {}))}]{tags}")
    print(f"Dropped so far: {len(R.r['dropped'])}")


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    style, cmd, rest = Path(os.path.expanduser(a[0])).resolve(), a[1], a[2:]
    if cmd == "first":
        first(style)
    elif cmd == "fonts":
        fonts(style, rest)
    elif cmd == "next":
        nxt(style)
    elif cmd == "show":
        show(style)
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
