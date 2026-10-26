#!/usr/bin/env python3
"""Keep STYLE.md in step with what's locked. You write the plain-English sections yourself; this fills
the blocks between <!-- auto:x --> markers from the files, so numbers are never retyped by hand.

Usage:
  python3 -I style_md.py "<style folder>"            make STYLE.md from the template if it's missing, then sync
  python3 -I style_md.py "<style folder>" --check    list the sections still saying "Not decided yet"

Blocks: brand (locked/brand.json), labs (locked/shine|zoom|shadow.json), sfx (picked sounds in sfx/sfx.json),
kept (locked/kept.json), rejected (page/round.json "dropped" + sfx/old/dropped.json).
Anything outside the markers is never touched.
"""
import json
import os
import re
import sys
from pathlib import Path

SK = Path(__file__).resolve().parent.parent


def load(p, d=None):
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, ValueError):
        return d


def brand_block(style):
    b = load(style / "locked" / "brand.json", {})
    if not b:
        return "_No brand yet._"
    c, f = b.get("colours", {}), b.get("font", {})
    w = f.get("weights", {})
    return "\n".join([
        f"- **Colours:** paper `{c.get('paper')}` (backgrounds), accent `{c.get('accent')}` (the one colour that pops),"
        f" accent soft `{c.get('accent_soft')}` (washes), accent deep `{c.get('accent_deep')}` (rings, dark pills), ink `{c.get('ink')}` (text on light).",
        f"- **Captions:** `{b.get('caption_colour', '#FFFFFF')}` text.",
        f"- **Font:** {f.get('family')} ({f.get('source')}; {f.get('licence')}). Weight {w.get('title', 700)} for titles, intro and accent text,"
        f" {w.get('caption', 600)} for captions, {w.get('label', 500)} for labels." + (f" Files: `{f['files_dir']}` (CSS `page/{f['css']}`)." if f.get("files_dir") else ""),
    ])


def labs_block(style):
    out = []
    sh = load(style / "locked" / "shine.json")
    if sh:
        out.append(f"- **Shine** (`locked/shine.json`, locked {sh.get('locked_at', '')[:16].replace('T', ' ')}): `{sh['base']}` text, `{sh['shine']}` band at "
                   f"{sh['strength']}% strength, {sh['width']}% wide, {sh['soft']}% soft edges, {sh['glow']}px glow on the band only (never the whole word), "
                   f"{sh['angle']}° angle, {sh['dur'] / 1000:.2f}s sweep on `{sh['ease']}`, {sh['gap'] / 1000:.2f}s between sweeps.")
    z = load(style / "locked" / "zoom.json")
    if z:
        how = "starts zoomed and glides out" if z.get("dir") == "out" else f"zooms in, holds {z['hold'] / 1000:.2f}s, then {'eases back out' if z.get('out') == 'same' else 'hard-cuts back'}"
        out.append(f"- **Main face zoom** (`locked/zoom.json`): {z['amount']}%, {z['dur'] / 1000:.2f}s, {how}, curve `{z.get('easing')}`.")
    s = load(style / "locked" / "shadow.json")
    if s:
        out.append(f"- **Caption shadow** (`locked/shadow.json`): `text-shadow: {s['text_shadow']}` on a {s.get('frame_width', 1080)}-wide frame "
                   f"(scale the px values for other widths), captions at {s.get('size')}px. Every plain white caption uses exactly this.")
    t = load(style / "locked" / "text_fade.json")
    if t and t.get("background_image"):
        out.append(f"- **Faded titles** (`locked/text_fade.json`): text filled with `{t['background_image']}` (background-clip: text, "
                   f"transparent colour), {t.get('weight', 700)} weight, {t.get('size', '')}px on a {t.get('frame_width', 1080)}-wide frame. Every faded title uses exactly this.")
    return "\n".join(out) or "_Nothing locked in the labs yet._"


def sfx_block(style):
    picked = [d for d in load(style / "sfx" / "sfx.json", []) if d.get("picked")]
    if not picked:
        return "_No sounds picked yet._"
    names = {"cut": "Hard cut / punch-in", "rise": "Clean rise", "blur": "Blur rise", "shine": "Shine", "tick": "Rings and ticks",
             "panel": "Panel slide", "icon": "App icons rising", "click": "Mouse clicks, lines drawing on", "hero": "Hero word landing"}
    rows = ["| Moment | Sound | Level | Source |", "|---|---|---|---|"]
    rows += [f"| {names.get(d['need'], d['need'])} | `sfx/{d['file']}` ({d['name']}) | {d['mix_db']:g} dB | {d.get('licence', '')} |" for d in picked]
    return "\n".join(rows)


def kept_block(style):
    kept = [k for k in load(style / "locked" / "kept.json", []) if k.get("section") != "Fonts"]
    if not kept:
        return "_Nothing kept yet._"
    return "\n".join(f"- **{k['section']}**: {k.get('label') or k['use']} = `{k['use']}` {json.dumps(k.get('params', {}))}" +
                     (f" (note: {k['note']})" if k.get("note") else "") for k in kept)


def rejected_block(style):
    rnd = load(style / "page" / "round.json", {}) or {}
    rows = [f"- {d['section']}: {d.get('label') or d['use']}" + (f" ({d['why']})" if d.get("why") else "") + f" (round {d.get('round')})"
            for d in rnd.get("dropped", [])]
    rows += [f"- Sound: {d['name']} for {d['need']}" + (f" ({d['why']})" if d.get("why") else "") for d in load(style / "sfx" / "old" / "dropped.json", [])]
    return "\n".join(rows) or "_Nothing yet._"


BLOCKS = {"brand": brand_block, "labs": labs_block, "sfx": sfx_block, "kept": kept_block, "rejected": rejected_block}


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    style = Path(os.path.expanduser(a[0])).resolve()
    md = style / "STYLE.md"
    if not md.exists():
        b = load(style / "locked" / "brand.json", {}) or {}
        name = b.get("name", "My")
        md.write_text((SK / "templates" / "STYLE.md").read_text().replace("{{NAME}}", f"{name}'s" if not name.endswith("s") else f"{name}'"))
        print(f"made {md}")
    text = md.read_text()
    if "--check" in a:
        todo = [sec.split("\n", 1)[0] for sec in text.split("\n## ")[1:] if "ot decided yet" in sec]
        print("Still open: " + (", ".join(todo) or "nothing"))
        return
    for key, fn in BLOCKS.items():
        text = re.sub(rf"(<!-- auto:{key} -->\n).*?(<!-- /auto:{key} -->)", lambda m: m.group(1) + fn(style) + "\n" + m.group(2), text, flags=re.S)
    md.write_text(text)
    print(f"synced {md}")


if __name__ == "__main__":
    main()
