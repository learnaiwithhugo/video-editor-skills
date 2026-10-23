#!/usr/bin/env python3
"""Write the person's brand (colours + font) to locked/brand.json and fetch the font onto their Mac.

Usage:
  python3 -I brand.py "<style folder>" --name "Coral" --accent "#FF6B3D" [--paper "#FFFFFF"]
        [--soft "#..."] [--deep "#..."] [--ink "#..."] [--font "General Sans"] [--handle "@them"]
        [--lines '{"intro": ["The simplest way to", "edit", "your videos"]}']
  python3 -I brand.py "<style folder>" --font "Switzer"          (change just the font)
  python3 -I brand.py --font-info "Geist"                         (where a font comes from, nothing written)

Colours: only --accent is required. Missing ones are made from it: soft = accent mixed into white,
deep = accent darkened (rings and dark pills), ink = a near-black tinted with the accent (text).
Fonts: free fonts come from Fontshare or Google Fonts and are downloaded into page/assets/fonts/ so the
page and the renders work offline. "Helvetica Neue" (or "Helvetica") uses the Mac's own copy.
Prints contrast numbers so you can warn about hard-to-read pairs (white text on a light accent).
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
SYSTEM = {"helvetica", "helvetica neue", "sf pro", "sf pro display", "arial"}
FONTSHARE = {"switzer", "general sans", "cabinet grotesk", "satoshi", "clash grotesk", "supreme", "chillax", "boska", "zodiak", "erode", "author", "plus jakarta sans", "telma", "sentient", "outfit", "excon", "synonym"}
WEIGHTS = (500, 600, 700)


def hex_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        raise SystemExit(f"'{h}' isn't a colour code. Use the six-character kind, like #FF6B3D.")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in c)


def mix(a, b, t):   # t of a, (1 - t) of b
    return tuple(x * t + y * (1 - t) for x, y in zip(a, b))


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def font_source(name):
    key = name.strip().lower()
    if key in SYSTEM:
        return {"family": "Helvetica Neue" if key.startswith("helvetica") else name, "source": "system", "remote_css": "",
                "licence": "Comes with macOS (fine to use in your own videos on your Mac)"}
    slug = key.replace(" ", "-")
    if key in FONTSHARE:
        return {"family": name, "source": "fontshare", "remote_css": f"https://api.fontshare.com/v2/css?f[]={slug}@{','.join(map(str, WEIGHTS))}&display=swap",
                "licence": "Fontshare free font licence (free for personal and commercial use)"}
    fam = "+".join(w.capitalize() if w.islower() else w for w in name.split())
    return {"family": name, "source": "google", "remote_css": f"https://fonts.googleapis.com/css2?family={fam}:wght@{';'.join(map(str, WEIGHTS))}&display=swap",
            "licence": "Google Fonts, SIL Open Font License (free for personal and commercial use)"}


def fetch(url):
    if url.startswith("//"):
        url = "https:" + url
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def download_font(name, dest: Path):
    """Download the font's CSS and files into dest/ and rewrite the CSS to point at them. Returns the font dict."""
    f = font_source(name)
    if f["source"] == "system":
        return {**f, "css": ""}
    try:
        css = fetch(f["remote_css"]).decode()
    except Exception as e:
        if f["source"] == "google":   # not on Google: try Fontshare before giving up
            f2 = {**f, "source": "fontshare", "remote_css": f"https://api.fontshare.com/v2/css?f[]={name.lower().replace(' ', '-')}@500,600,700&display=swap",
                  "licence": "Fontshare free font licence (free for personal and commercial use)"}
            try:
                css, f = fetch(f2["remote_css"]).decode(), f2
            except Exception:
                raise SystemExit(f"Couldn't find the font '{name}' on Google Fonts or Fontshare ({e}). Check the spelling, or pick another.")
        else:
            raise SystemExit(f"Couldn't download '{name}' ({e}). Check the internet connection.")
    if "@font-face" not in css:
        raise SystemExit(f"'{name}' came back empty from {f['source']}. Check the spelling, or pick another.")
    dest.mkdir(parents=True, exist_ok=True)
    files = []
    def grab(m):
        url = m.group(1).strip("'\"")
        fn = re.sub(r"[^A-Za-z0-9._-]", "_", url.split("/")[-1].split("?")[0])[-60:] or "font.woff2"
        if not (dest / fn).exists():
            (dest / fn).write_bytes(fetch(url))
        files.append(fn)
        return f"url('{fn}')"
    local = re.sub(r"url\(([^)]+)\)", grab, css)
    (dest / "fonts.css").write_text(local)
    return {**f, "files": sorted(set(files))}


def main():
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    if "--font-info" in a:
        print(json.dumps(font_source(opt("--font-info")), indent=1))
        return
    style = Path(os.path.expanduser(a[0])).resolve()
    path = style / "locked" / "brand.json"
    b = json.loads(path.read_text()) if path.exists() else {"colours": {}, "font": {}}
    if opt("--name"):
        b["name"] = opt("--name")
    if opt("--handle"):
        b["handle"] = opt("--handle")
    if opt("--lines"):
        b["lines"] = {**b.get("lines", {}), **json.loads(opt("--lines"))}
    c = b.setdefault("colours", {})
    if opt("--accent"):
        acc = hex_rgb(opt("--accent"))
        c["accent"] = rgb_hex(acc)
        c["paper"] = rgb_hex(hex_rgb(opt("--paper"))) if opt("--paper") else c.get("paper", "#FFFFFF")
        c["accent_soft"] = rgb_hex(hex_rgb(opt("--soft"))) if opt("--soft") else rgb_hex(mix(acc, (255, 255, 255), 0.45))
        c["accent_deep"] = rgb_hex(hex_rgb(opt("--deep"))) if opt("--deep") else rgb_hex(mix(acc, (0, 0, 0), 0.55))
        c["ink"] = rgb_hex(hex_rgb(opt("--ink"))) if opt("--ink") else rgb_hex(mix(acc, (8, 10, 16), 0.14))
    else:
        for k, flag in [("paper", "--paper"), ("accent_soft", "--soft"), ("accent_deep", "--deep"), ("ink", "--ink")]:
            if opt(flag):
                c[k] = rgb_hex(hex_rgb(opt(flag)))
    if not c.get("accent"):
        raise SystemExit("An accent colour is needed: --accent \"#RRGGBB\"")
    b.setdefault("caption_colour", "#FFFFFF")
    if opt("--font") or not b.get("font", {}).get("family"):
        name = opt("--font") or "Helvetica Neue"
        f = download_font(name, style / "page" / "assets" / "fonts")
        b["font"] = {"family": f["family"], "source": f["source"], "css": "assets/fonts/fonts.css" if f["source"] != "system" else "",
                     "remote_css": f["remote_css"], "files_dir": "page/assets/fonts" if f["source"] != "system" else "",
                     "licence": f["licence"], "weights": {"title": 700, "caption": 600, "label": 500}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(b, indent=1))
    w, ink, paper, acc, deep = (255, 255, 255), hex_rgb(c["ink"]), hex_rgb(c["paper"]), hex_rgb(c["accent"]), hex_rgb(c["accent_deep"])
    print(f"Saved {path}")
    print(f"  colours: paper {c['paper']}  accent {c['accent']}  soft {c['accent_soft']}  deep {c['accent_deep']}  ink {c['ink']}")
    print(f"  font: {b['font']['family']} ({b['font']['source']})")
    print(f"  contrast: white text on accent {contrast(w, acc):.1f}:1 | ink on paper {contrast(ink, paper):.1f}:1 | "
          f"white on deep {contrast(w, deep):.1f}:1   (3:1 or more reads fine for big captions)")


if __name__ == "__main__":
    main()
