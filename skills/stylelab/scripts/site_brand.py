#!/usr/bin/env python3
"""Read an existing brand off a website: the colours it really uses (weighted by how much of the page
they cover) and its fonts, so someone with a brand never has to know their hex codes.

Usage:
  python3 -I site_brand.py "<url>" [--out "<file.png>"]
Prints JSON: {"paper", "ink", "accent", "accent_options": [...], "fonts": {"headings", "body"}, "shot"}
and a screenshot of the page to look at. Then confirm with the person and run brand.py with the picks.
"""
import colorsys
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SK = Path(__file__).resolve().parent.parent

PROBE = r"""(() => {
  const area = {}, add = (c, a) => { if (!c || c === "transparent" || c.startsWith("rgba(0, 0, 0, 0")) return; area[c] = (area[c] || 0) + a; };
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 2 && r.height > 2 && r.bottom > 0 && r.top < innerHeight * 3 ? r : null; };
  for (const el of document.querySelectorAll("body, body *")) {
    const r = vis(el); if (!r) continue;
    const s = getComputedStyle(el); if (s.visibility === "hidden" || +s.opacity < .3) continue;
    add(s.backgroundColor, Math.min(r.width * r.height, innerWidth * innerHeight * 3));
    const txt = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (txt) add(s.color, r.width * r.height * .6);
    if (["A", "BUTTON"].includes(el.tagName) || el.getAttribute("role") === "button") { add(s.backgroundColor, 40000); add(s.color, 15000); }
  }
  const font = sel => { const e = document.querySelector(sel); return e ? getComputedStyle(e).fontFamily : null; };
  return JSON.stringify({ colours: Object.entries(area).sort((a, b) => b[1] - a[1]).slice(0, 40),
    fonts: { headings: font("h1") || font("h2"), body: font("p") || font("body") } });
})()"""


def rgb(css):
    nums = css[css.index("(") + 1:css.index(")")].replace("/", ",").split(",")
    return tuple(int(float(n)) for n in nums[:3])


def hexify(c):
    return "#%02X%02X%02X" % c


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    url = a[0]
    out = a[a.index("--out") + 1] if "--out" in a else str(Path(tempfile.gettempdir()) / "site-brand.png")
    r = subprocess.run(["node", str(SK / "scripts" / "shot.mjs"), "--url", url, "--out", out, "--width", "1440", "--height", "1000",
                        "--wait", "2500", "--eval", PROBE], capture_output=True, text=True, timeout=120)
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
        data = json.loads(res["eval"])
    except (ValueError, IndexError, KeyError, TypeError):
        sys.exit("Couldn't read that site. Try its homepage, or ask them for their colours instead.\n" + r.stderr[-400:])
    cols = [(rgb(c), w) for c, w in data["colours"] if c.startswith("rgb")]
    light = lambda c: sum(c) / 3
    sat = lambda c: colorsys.rgb_to_hls(*[v / 255 for v in c])[2]
    paper = max(cols[:6], key=lambda x: x[1] * (light(x[0]) > 200))[0] if cols else (255, 255, 255)
    darks = [c for c, w in cols if light(c) < 80]
    ink = darks[0] if darks else (17, 24, 39)
    seen, accents = set(), []
    for c, w in cols:   # coloured, not near-white or near-black, most-used first
        if sat(c) > .28 and 40 < light(c) < 235 and hexify(c) not in seen:
            seen.add(hexify(c))
            accents.append(hexify(c))
    print(json.dumps({"paper": hexify(paper), "ink": hexify(ink), "accent": accents[0] if accents else None,
                      "accent_options": accents[:5], "fonts": data["fonts"], "shot": out}, indent=1))


if __name__ == "__main__":
    main()
