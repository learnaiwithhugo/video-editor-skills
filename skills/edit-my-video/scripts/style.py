#!/usr/bin/env python3
"""Read a style folder (made by build-my-style) and turn it into tokens the edit engine uses.

Usage:
  python3 style.py check  [<style_dir>]              is the folder complete? (plain-English report)
  python3 style.py resolve [<style_dir>] --out <WORK/style.json>
        writes style.json (colours, font, caption, shine, zooms, motion, sound effects, safe zone, taste checks)
  python3 style.py project [<style_dir>] <hf_dir>    copies fonts + sound list into a HyperFrames project and writes
        <hf_dir>/assets/style.css and style.js from the tokens (run after resolve, or it resolves itself)
  python3 style.py serve  [<style_dir>]              makes sure the style folder's page server is running; prints the URL

The style folder contract: STYLE.md; locked/*.json (shine, zoom, shadow, brand.json, motion.json, all optional);
sfx/sfx.json [{file, need, name, mix_db, picked}] + the WAVs; page/ (review pages) + a server (serve.py);
reviews/; references/. brand.json, when present, wins over anything parsed out of STYLE.md.
"""
import json
import re
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ENGINE, SK, jdump, jload, style_dir  # noqa: E402

EXPO = "cubic-bezier(.16,1,.3,1)"
GLIDE = "cubic-bezier(.19,1,.22,1)"
SMOOTH = "cubic-bezier(.65,0,.35,1)"
PUSH = "cubic-bezier(.7,0,.15,1)"

# Motion defaults = the values locked on the style page this skill was built with. A style folder overrides them with
# locked/motion.json (same keys). These are the *feel*, not a menu of layouts.
MOTION = {
    "caption": {"rise_px": 14, "dur_ms": 260, "ease": EXPO},
    "clean_rise": {"rise_px": 42, "dur_ms": 820, "gap_ms": 230, "ease": GLIDE},
    "blur_rise": {"rise_px": 26, "blur_px": 18, "dur_ms": 480, "gap_ms": 170, "ease": EXPO},
    "enter_fade": {"dur_ms": 600},
    "enter_rise": {"rise_px": 46, "dur_ms": 850, "ease": GLIDE},
    "enter_blur": {"rise_px": 34, "blur_px": 18, "dur_ms": 560, "ease": EXPO},
    "focus_in": {"from_scale": 1.35, "blur_px": 26, "dur_ms": 1000, "ease": GLIDE},
    "glide_in": {"from_px": 180, "dur_ms": 900, "ease": GLIDE},
    "draw": {"dur_ms": 420, "ease": EXPO},
    "push": {"dur_ms": 800, "ease": PUSH, "max_ms": 1000},
    "panel_slide": {"dur_ms": 650, "ease": GLIDE},
    "scroll": {"px": 700, "dur_ms": 4200, "ease": SMOOTH},
}
ZOOM = {
    "main": {"from": 1.2, "to": 1.0, "dur_ms": 3500, "ease": SMOOTH, "origin": "50% 32%"},
    "punch": {"to": 1.15, "dur_ms": 750, "ease": EXPO},
    "hard_punch": {"to": 1.15},
}
SAFE = {"top": 220, "bottom": 420, "right_x": 940, "right_y0": 1000, "right_y1": 1500, "side": 60}
TASTE = {"no_popin": True, "no_black_bg": True, "no_underline": True, "no_em_dash": True,
         "no_repeat_layout": True, "big_visuals": True}
FALLBACK = {"bg": "#FFFFFF", "accent": "#75B4DB", "wash": "#A9C2F2", "deep": "#17408F", "text": "#10203A"}


# ---------------------------------------------------------------- reading the folder
def parse_colours(md):
    line = next((l for l in md.splitlines() if re.search(r"colou?rs?\W", l, re.I) and "#" in l), "")
    found = re.findall(r"([A-Za-z][A-Za-z ]{0,24}?)\s*`?(#[0-9A-Fa-f]{6})`?\s*([a-z ]{0,20})", line)
    named, roles = {}, {}
    for name, hexv, role in found:
        name = name.strip().split("**")[-1].strip() or hexv
        named[name] = hexv.upper()
        for r in ("background", "accent", "wash", "text"):
            if r in role.lower():
                roles[r] = hexv.upper()
    return named, roles


def lum(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def colours(sd, md):
    brand = sd / "locked" / "brand.json"
    if brand.exists():
        b = jload(brand)
        c = b.get("colors") or b.get("colours") or {}
        if isinstance(c, list):  # [{name, hex, role}]
            c = {x.get("role") or x.get("name"): x.get("hex") for x in c}
        out = dict(FALLBACK)
        # Exact names first (incl. build-my-style's paper / accent_soft / accent_deep), so "accent_soft"
        # can never overwrite the accent; loose prefix matching only fills roles still unset.
        exact = {"bg": ("bg", "background", "base", "paper", "white"), "accent": ("accent", "primary", "brand", "blue"),
                 "wash": ("wash", "soft", "tint", "secondary", "accent_soft", "blue_soft"),
                 "deep": ("deep", "ink2", "dark", "navy", "accent_deep", "blue_ink"),
                 "text": ("text", "ink", "foreground")}
        found = set()
        for k, v in c.items():
            for role, keys in exact.items():
                if k.lower() in keys:
                    out[role] = v.upper(); found.add(role)
        for k, v in c.items():
            kl = k.lower()
            for role, keys in exact.items():
                if role not in found and any(kl.startswith(x) for x in keys):
                    out[role] = v.upper(); found.add(role)
        out["named"] = {k: v for k, v in c.items()}
        return out
    named, roles = parse_colours(md)
    out = dict(FALLBACK)
    if not named:
        out["named"] = {}
        return out
    out["bg"] = roles.get("background", out["bg"])
    out["accent"] = roles.get("accent", out["accent"])
    out["wash"] = roles.get("wash", out["wash"])
    out["text"] = roles.get("text", min(named.values(), key=lum))
    darks = [v for v in named.values() if lum(v) < 0.35 and v not in (out["text"],)]
    out["deep"] = darks[0] if darks else out["text"]
    out["named"] = named
    return out


def font_family(sd, md):
    brand = sd / "locked" / "brand.json"
    if brand.exists():
        f = jload(brand).get("font")
        if isinstance(f, str):
            return f, []
        if isinstance(f, dict):
            return f.get("family", "Helvetica Neue"), [str((sd / x) if not Path(x).is_absolute() else x)
                                                        for x in f.get("files", [])]
    m = re.search(r"\*\*Font:\*\*\s*([A-Z][\w]*(?: [A-Z][\w]*)*)", md)
    return (m.group(1) if m else "Helvetica Neue"), []


WEIGHTS = {"500": ("medium", "500"), "600": ("semibold", "600", "semi"), "700": ("bold", "700")}


def find_font_files(sd, family, given):
    """Weight -> file. Looks in brand.json, the style folder, ~/Library/Fonts, the skill's cache, then fetches
    a free copy from Fontshare or Google Fonts into the skill's cache (never into the style folder)."""
    cache = ENGINE / "fonts" / family.replace(" ", "")
    pools = [Path(x) for x in given] + list(sd.rglob("*")) + list((Path.home() / "Library/Fonts").glob("*")) + \
        (list(cache.glob("*")) if cache.exists() else [])
    key = family.lower().replace(" ", "")
    files = [p for p in pools if p.suffix.lower() in (".woff2", ".woff", ".otf", ".ttf")
             and key in p.name.lower().replace(" ", "").replace("-", "").replace("_", "")]
    out = {}
    for w, words in WEIGHTS.items():
        for p in sorted(files, key=lambda p: (p.suffix != ".woff2", len(p.name))):
            n = p.stem.lower().replace(" ", "").replace("-", "").replace("_", "")
            if any(n.endswith(x) or x in n for x in words) and not (w == "700" and "semi" in n) \
                    and "italic" not in n:
                out[w] = str(p)
                break
    if len(out) < 3:
        out.update({k: v for k, v in fetch_font(family, cache).items() if k not in out})
    return out


def fetch_font(family, cache):
    cache.mkdir(parents=True, exist_ok=True)
    got = {}
    urls = [f"https://api.fontshare.com/v2/css?f[]={family.lower().replace(' ', '-')}@500,600,700&display=swap",
            f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@500;600;700&display=swap"]
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120"})
            css = urllib.request.urlopen(req, timeout=20).read().decode()
        except Exception:
            continue
        for block in re.findall(r"@font-face\s*{(.*?)}", css, re.S):
            w = re.search(r"font-weight:\s*(\d+)", block)
            src = re.search(r"url\(['\"]?([^'\")]+\.woff2)", block)
            if not (w and src) or w.group(1) not in WEIGHTS or "italic" in block:
                continue
            url = ("https:" + src.group(1)) if src.group(1).startswith("//") else src.group(1)
            dst = cache / f"{family.replace(' ', '')}-{w.group(1)}.woff2"
            if not dst.exists():
                urllib.request.urlretrieve(url, dst)
            got[w.group(1)] = str(dst)
        if len(got) >= 3:
            break
    return got


def sfx_list(sd):
    p = sd / "sfx" / "sfx.json"
    if not p.exists():
        return []
    out = []
    for s in jload(p):
        if not s.get("picked"):
            continue
        parts = Path(s["file"]).stem.split("-")
        role = parts[1] if len(parts) > 1 and parts[0].isdigit() else parts[0]
        out.append({"file": s["file"], "path": str(sd / "sfx" / s["file"]), "need": s.get("need"),
                    "name": s.get("name", ""), "role": role, "mix_db": s.get("mix_db", -14),
                    "hit_s": s.get("hit_s", 0.0)})
    return out


def resolve(sd):
    md = (sd / "STYLE.md").read_text()
    lock = lambda n: jload(sd / "locked" / f"{n}.json") if (sd / "locked" / f"{n}.json").exists() else None  # noqa: E731
    fam, given = font_family(sd, md)
    shadow = lock("shadow") or {}
    motion = json.loads(json.dumps(MOTION))
    for k, v in (lock("motion") or {}).items():
        motion.setdefault(k, {}).update(v) if isinstance(v, dict) else None
    zoom = json.loads(json.dumps(ZOOM))
    z = lock("zoom")
    if z:  # the Zoom Lab's lock replaces the main face zoom's curve and timing
        zoom["main"].update({k: z[k] for k in ("from", "to", "origin") if k in z})
        if "dur" in z:
            zoom["main"]["dur_ms"] = z["dur"]
        if "ease" in z:
            zoom["main"]["ease"] = z["ease"]
    scale = 1080 / float(shadow.get("frame_width", 1080))
    return {
        "style_dir": str(sd),
        "colors": colours(sd, md),
        "font": {"family": fam, "files": find_font_files(sd, fam, given)},
        "caption": {"size": int(shadow.get("size", 85) * scale), "weight": 600,
                    "shadow": shadow.get("text_shadow", "0 4px 24px rgba(0,0,0,.5)"), **motion["caption"]},
        "shine": lock("shine"),
        "zoom": zoom,
        "motion": motion,
        "sfx": sfx_list(sd),
        "safe": SAFE,
        "taste": TASTE,
        "music": "the user picks it per edit (never choose music for them)",
    }


# ---------------------------------------------------------------- writing it into a project
def project(sd, hf, tokens=None):
    tok = tokens or resolve(sd)
    hf = Path(hf)
    (hf / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    faces = []
    fam = tok["font"]["family"]
    for w, src in sorted(tok["font"]["files"].items()):
        ext = Path(src).suffix
        dst = hf / "assets" / "fonts" / f"{fam.replace(' ', '')}-{w}{ext}"
        shutil.copy2(src, dst)
        fmt = {".woff2": "woff2", ".woff": "woff", ".otf": "opentype", ".ttf": "truetype"}[ext.lower()]
        faces.append(f'@font-face {{ font-family: "{fam}"; src: url("fonts/{dst.name}") format("{fmt}"); '
                     f'font-weight: {w}; font-display: block; }}')
    c = tok["colors"]
    cap = tok["caption"]
    css = "\n".join(faces) + f"""
:root {{
  --bg: {c['bg']}; --accent: {c['accent']}; --wash: {c['wash']}; --deep: {c['deep']}; --text: {c['text']};
  --font: "{fam}", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --cap-size: {cap['size']}px; --cap-shadow: {cap['shadow']};
  --frost: color-mix(in srgb, {c['accent']} 62%, transparent);
}}
"""
    (hf / "assets" / "style.css").write_text(css)
    (hf / "assets" / "style.js").write_text("window.STYLE = " + json.dumps(tok, indent=1) + ";\n")
    shutil.copy2(ENGINE / "kit.css", hf / "assets" / "kit.css")
    shutil.copy2(ENGINE / "kit.js", hf / "assets" / "kit.js")
    return tok


# ---------------------------------------------------------------- check + serve
def check(sd):
    ok = True

    def say(good, msg, fix=""):
        nonlocal ok
        print(("  OK       " if good else "  MISSING  ") + msg + ("" if good else f"\n           -> {fix}"))
        ok = ok and good
    print(f"Style folder: {sd}\n")
    say((sd / "STYLE.md").exists(), "STYLE.md (the rules)", "Run build-my-style first.")
    tok = resolve(sd)
    say(bool(tok["colors"]["named"]), f"Colours ({', '.join(tok['colors']['named']) or 'none found'})",
        "Add a '**Colours:**' line to STYLE.md or a locked/brand.json.")
    say(len(tok["font"]["files"]) >= 2, f"Font {tok['font']['family']} ({', '.join(sorted(tok['font']['files'])) or 'no files'})",
        "Put the font files in the style folder (any fonts/ subfolder) or name a free Fontshare/Google font.")
    for n in ("shine", "shadow", "zoom"):
        p = sd / "locked" / f"{n}.json"
        print(("  OK       " if p.exists() else "  default  ") + f"locked/{n}.json" + ("" if p.exists() else " (not locked, using the default)"))
    missing = [s["file"] for s in tok["sfx"] if not Path(s["path"]).exists()]
    say(bool(tok["sfx"]) and not missing, f"Sound effects ({len(tok['sfx'])} picked)",
        "Pick sounds in build-my-style, or missing files: " + ", ".join(missing))
    say((sd / "page").is_dir(), "page/ (where the storyboard page goes)", "Run build-my-style to make it.")
    print("\nREADY" if ok else "\nNOT READY")
    return ok


def server_script(sd):
    for p in (sd / "serve.py", sd / "page" / "serve.py"):
        if p.exists():
            return p
    return None


def port_of(sd):
    s = server_script(sd)
    if s:
        m = re.search(r"^PORT\s*=\s*(\d+)", s.read_text(), re.M)
        if m:
            return int(m.group(1))
    return 4870


def listening(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def serve(sd):
    # build-my-style's server.py knows which port THIS style folder's server is on, never mistakes another
    # program on port 4870 for it, and moves to the next free port if 4870 is busy. Use it when it's installed.
    bms = SK.parent / "build-my-style" / "scripts" / "server.py"
    if bms.exists():
        for cmd in ("status", "start"):
            r = subprocess.run([sys.executable, "-I", str(bms), cmd, str(sd)], capture_output=True, text=True)
            m = re.search(r"RUNNING http://localhost:(\d+)", r.stdout)
            if m:
                print(f"{'Already running' if cmd == 'status' else 'Started'}: http://localhost:{m.group(1)}")
                return int(m.group(1))
        print("Could not start the style page server:\n" + (r.stdout + r.stderr).strip())
        return None
    port = port_of(sd)
    if listening(port):
        print(f"Already running: http://localhost:{port}")
        return port
    (sd / "reviews").mkdir(exist_ok=True)
    log = open(sd / "reviews" / "server.log", "a")
    s = server_script(sd)
    cmd = ["python3", str(s)] if s else ["python3", str(ENGINE / "serve.py"), "--root", str(sd), "--port", str(port)]
    subprocess.Popen(cmd, cwd=str(sd), stdout=log, stderr=log, start_new_session=True)
    for _ in range(30):
        if listening(port):
            break
        __import__("time").sleep(0.2)
    print(f"Started: http://localhost:{port}" if listening(port) else f"Could not start the server on port {port}")
    return port


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd, rest = a[0], a[1:]
    out = rest[rest.index("--out") + 1] if "--out" in rest else None
    rest = [x for i, x in enumerate(rest) if x != "--out" and (i == 0 or rest[i - 1] != "--out")]
    if cmd == "project":
        sd = style_dir(rest[0] if len(rest) > 1 else None)
        project(sd, rest[-1], jload(Path(rest[-1]).parent / "style.json") if (Path(rest[-1]).parent / "style.json").exists() else None)
        print("wrote style.css, style.js, kit.css, kit.js and fonts into", Path(rest[-1]) / "assets")
    else:
        sd = style_dir(rest[0] if rest else None)
        if cmd == "check":
            sys.exit(0 if check(sd) else 1)
        elif cmd == "resolve":
            tok = resolve(sd)
            jdump(tok, out) if out else print(json.dumps(tok, indent=1))
            if out:
                print("wrote", out, "| font", tok["font"]["family"], sorted(tok["font"]["files"]), "| accent", tok["colors"]["accent"])
        elif cmd == "serve":
            serve(sd)
        else:
            sys.exit(__doc__)
