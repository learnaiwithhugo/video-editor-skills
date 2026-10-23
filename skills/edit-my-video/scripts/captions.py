#!/usr/bin/env python3
"""Captions from the real word timings: 2-3 word chunks that swap as the speaker talks (soft fade-up in the kit).

Usage:
  python3 captions.py make   <WORK> [--skip 0-2.9 --skip 7.6-11.4] [--fix "cloud=Claude"] [--top 1198]
        words.json -> caps.json. Breaks on punctuation, pauses over 0.3 s and hard cuts. --skip drops captions in
        moments where intro text or a visual already says the words. Only words the speaker says, spelled right.
  python3 captions.py fix    <WORK> "49=ArtCraft" "cloud=Claude"
        fix a misheard word in words.json itself (by its number in words.txt, or every match of old=new), so the
        captions AND the self-review both use the right word. Only ever to match what was really said.
  python3 captions.py inject <WORK>
        caps.json -> the captions host in WORK/hf/index.html (between the CAPTIONS:START / END markers).

caps.json is yours to edit before inject: each chunk is {text, start, end, cls, top, html?}.
  cls: plain (white + locked shadow, the default) | box (solid accent box) | frost (frosted accent glass) | ink
  top: y of the caption box in px (keep inside the safe zone: 220 to 1500, and clear of the mouth)
  html: optional, same words with <b>word</b> to put one key word in the accent colour (no underlines)
"""
import html as H
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import jdump, jload  # noqa: E402

PUNCT = re.compile(r"[.,!?;:]+$")


def clean(w):
    w = w.replace("—", " ").replace("–", " ").strip()
    return PUNCT.sub("", w).strip(" \"'") if not re.fullmatch(r"[\w.]+\.[a-z]{2,4}", w) else w.rstrip(".,")


def make(work, skips, fixes, top):
    words = jload(work / "words.json")
    segs = jload(work / "segments.json")
    seg_end = {s["id"]: s["start"] + s["dur"] for s in segs}
    chunks, cur = [], []

    def flush():
        if cur:
            chunks.append(list(cur))
            cur.clear()
    for i, w in enumerate(words):
        if any(a <= w["s"] < b for a, b in skips):
            flush()
            continue
        if cur and (w["seg"] != cur[-1]["seg"] or w["s"] - cur[-1]["e"] > 0.3 or len(cur) >= 3
                    or len(" ".join(clean(x["w"]) for x in cur + [w])) > 20):
            flush()
        cur.append(w)
        if PUNCT.search(w["w"]):
            flush()
    flush()
    for k in range(1, len(chunks)):  # no lonely last word: borrow one from a full chunk before it
        a, b = chunks[k - 1], chunks[k]
        if len(b) == 1 and len(a) == 3 and a[-1]["seg"] == b[0]["seg"] and not PUNCT.search(a[-1]["w"]) \
                and b[0]["s"] - a[-1]["e"] < 0.3:
            b.insert(0, a.pop())
    out = []
    for k, ch in enumerate(chunks):
        text = " ".join(clean(x["w"]) for x in ch)
        for f in fixes:
            a, b = f.split("=", 1)
            text = re.sub(rf"\b{re.escape(a)}\b", b, text, flags=re.I)
        start = ch[0]["s"]
        nxt = chunks[k + 1][0]["s"] if k + 1 < len(chunks) else 1e9
        end = min(nxt, ch[-1]["e"] + 0.35, seg_end[ch[-1]["seg"]])
        out.append({"text": text, "start": round(start, 3), "end": round(max(end, start + 0.2), 3), "cls": "plain", "top": top})
    jdump(out, work / "caps.json")
    for c in out:
        print(f"  {c['start']:6.2f}-{c['end']:6.2f}  {c['text']}")
    print(f"{len(out)} captions -> {work / 'caps.json'} (edit cls/top/html per chunk, then run inject)")


def fix(work, pairs):
    words = jload(work / "words.json")
    for p in pairs:
        old, new = p.split("=", 1)
        hits = [int(old)] if old.isdigit() else [i for i, w in enumerate(words) if norm(w["w"]) == norm(old)]
        for i in hits:
            tail = re.search(r"[.,!?;:]+$", words[i]["w"])
            print(f"  {i:3d} {words[i]['w']!r} -> {new + (tail.group(0) if tail else '')!r}")
            words[i]["w"] = new + (tail.group(0) if tail else "")
        if not hits:
            print(f"  no word matches {old!r}")
    jdump(words, work / "words.json")
    (work / "words.txt").write_text("\n".join(f"{i:3d} {w['s']:6.2f}-{w['e']:6.2f} {w['seg']} {w['w']}" for i, w in enumerate(words)) + "\n")


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def inject(work):
    caps = jload(work / "caps.json")
    idx = work / "hf" / "index.html"
    page = idx.read_text()
    rows = []
    for i, c in enumerate(caps):
        inner = c.get("html") or H.escape(c["text"], quote=False)
        plain = re.sub(r"<[^>]+>", "", inner)
        if H.unescape(plain).strip() != c["text"].strip():
            sys.exit(f"caption {i}: html words '{plain}' differ from text '{c['text']}'")
        if "—" in inner:
            sys.exit(f"caption {i} has an em dash")
        rows.append(f'        <div id="cap{i}" class="cap {c.get("cls", "plain")} clip" data-start="{c["start"]:.3f}" '
                    f'data-duration="{c["end"] - c["start"]:.3f}" data-track-index="8" style="top: {int(c.get("top", 1198))}px">'
                    f'<span class="t">{inner}</span></div>')
    block = ('<!-- CAPTIONS:START (written by scripts/captions.py inject) -->\n'
             '      <div id="captions" class="layer" data-track-kind="captions" style="z-index: 50; pointer-events: none">\n'
             + "\n".join(rows) + "\n      </div>\n      <!-- CAPTIONS:END -->")
    new, n = re.subn(r"<!-- CAPTIONS:START.*?<!-- CAPTIONS:END -->", lambda m: block, page, flags=re.S)
    if not n:
        sys.exit("No CAPTIONS:START / CAPTIONS:END markers in index.html")
    idx.write_text(new)
    print(f"{len(caps)} captions written into {idx}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    work = Path(a[1]).resolve()
    if a[0] == "make":
        skips = [tuple(map(float, a[i + 1].split("-"))) for i, x in enumerate(a) if x == "--skip"]
        fixes = [a[i + 1] for i, x in enumerate(a) if x == "--fix"]
        top = int(a[a.index("--top") + 1]) if "--top" in a else 1198
        make(work, skips, fixes, top)
    elif a[0] == "fix":
        fix(work, a[2:])
    elif a[0] == "inject":
        inject(work)
    else:
        sys.exit(__doc__)
