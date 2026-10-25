#!/usr/bin/env python3
"""The creators whose reels shaped this style: shown on the style page's Creators page (/creators.html)
and listed in STYLE.md. Stored in <style folder>/creators.json.

Usage:
  python3 -I creators.py add "<style folder>" --name "Sam Lee" [--handle samlee]
        [--url https://www.youtube.com/@x] [--took "clean system explainers"] [--fav]
        [--reel "<file in references/>" "<link to the post>" "<short title>"] ...
      Adds the creator, or updates them (matched by name) and adds any new reels.
  python3 -I creators.py list "<style folder>"
  python3 -I creators.py remove "<style folder>" --name "<name>"     (kept in creators-old.json)
"""
import json
import sys
from pathlib import Path


def load(style):
    p = style / "creators.json"
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, ValueError):
        return {"creators": []}


def save(style, data):
    (style / "creators.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))


def parse(a):
    o = {"reels": []}
    i = 0
    while i < len(a):
        k = a[i]
        if k == "--fav":
            o["fav"] = True
            i += 1
        elif k == "--reel":
            o["reels"].append({"file": a[i + 1], "link": a[i + 2], "title": a[i + 3]})
            i += 4
        elif k.startswith("--"):
            o[k[2:]] = a[i + 1]
            i += 2
        else:
            sys.exit(f"Didn't understand: {k}")
    return o


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("add", "list", "remove"):
        sys.exit(__doc__)
    cmd, style = a[0], Path(a[1]).expanduser()
    data = load(style)
    people = data["creators"]
    if cmd == "list":
        for c in people:
            print(f"{c['name']}{' (favourite)' if c.get('fav') else ''}: {len(c.get('reels', []))} reels. {c.get('took', '')}")
        if not people:
            print("No creators yet.")
        return
    o = parse(a[2:])
    if "name" not in o:
        sys.exit("--name is required")
    found = next((c for c in people if c["name"].lower() == o["name"].lower()), None)
    if cmd == "remove":
        if not found:
            sys.exit(f"No creator called {o['name']}")
        old = style / "creators-old.json"
        kept = json.loads(old.read_text()) if old.exists() else []
        kept.append(found)
        old.write_text(json.dumps(kept, indent=1, ensure_ascii=False))
        people.remove(found)
        save(style, data)
        print(f"Removed {found['name']} (kept in creators-old.json).")
        return
    for r in o["reels"]:
        if not (style / "references" / r["file"]).exists():
            print(f"Note: references/{r['file']} isn't there yet, the page will show the link only.")
    if found:
        for k in ("handle", "url", "took", "fav"):
            if k in o:
                found[k] = o[k]
        have = {r["file"] for r in found.setdefault("reels", [])}
        found["reels"] += [r for r in o["reels"] if r["file"] not in have]
        print(f"Updated {found['name']} ({len(found['reels'])} reels).")
    else:
        people.append({k: o[k] for k in ("name", "handle", "url", "took", "fav", "reels") if k in o})
        print(f"Added {o['name']}.")
    people.sort(key=lambda c: not c.get("fav"))
    save(style, data)


if __name__ == "__main__":
    main()
