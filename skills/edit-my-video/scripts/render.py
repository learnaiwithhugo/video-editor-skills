#!/usr/bin/env python3
"""The HyperFrames side: make the project, check it, look at frames, render the reel or short variation slices.

Usage:
  python3 render.py new    <WORK> --title "GitHub repos v1" [--force]
        WORK/hf/: pinned HyperFrames project, style.css/style.js/kit from the style folder, and index.html from the
        engine template (duration = the cut's length). Won't overwrite an index.html you've written unless --force.
  python3 render.py check  <WORK>                       HyperFrames lint + runtime check (fix every error)
  python3 render.py snap   <WORK> 1.2,4.5,9 [--zoom x,y,w,h] [--name hook]
        real rendered frames at those seconds -> WORK/progress/NN-snap-<name>.png (one sheet)
  python3 render.py render <WORK> --out "<file.mp4>" [--draft]
  python3 render.py slice  <WORK> <name> <start> <end> [--index <variant.html>]
        renders only start..end (a 2-4 s moment) of index.html, or of a variant copy of it, to
        WORK/variations/<name>.mp4 at draft quality. Cheap: this is how A/B/C variations get made.
"""
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ENGINE, PIN, jdump, jload, npx_hf, style_dir  # noqa: E402
from progress import progress_path  # noqa: E402


def arg(a, k, d=None):
    return a[a.index(k) + 1] if k in a else d


def new(work, title, force):
    hf = work / "hf"
    (hf / "assets").mkdir(parents=True, exist_ok=True)
    jdump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
           "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
           "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
           "media": {"autoProxy": True}, "authoringSkill": "hyperframes"}, hf / "hyperframes.json")
    jdump({"name": "hf", "private": True, "type": "module",
           "scripts": {k: f"npx --yes hyperframes@{PIN} {k if k != 'dev' else 'preview'}" for k in ("dev", "check", "render")}},
          hf / "package.json")
    jdump({"id": work.name, "name": title}, hf / "meta.json")
    tok = jload(work / "style.json")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import style
    style.project(Path(tok["style_dir"]), hf, tok)
    segs = jload(work / "segments.json") if (work / "segments.json").exists() else []
    dur = round(sum(s["dur"] for s in segs), 4) if segs else 10
    idx = hf / "index.html"
    if idx.exists() and not force:
        print(f"kept your {idx} (pass --force to start over); refreshed style + kit")
    else:
        idx.write_text((ENGINE / "index.html").read_text().replace("__TITLE__", title).replace("__DURATION__", str(dur)))
        print(f"wrote {idx} ({dur}s)")


def check(work):
    import json
    r = npx_hf("check", "--json", cwd=work / "hf", check=False, capture=True)
    out = r.stdout.strip()
    try:
        j = json.loads(out[out.index("{"):])
    except ValueError:
        print(out[-3000:], r.stderr[-2000:])
        return False
    (work / "qa").mkdir(exist_ok=True)
    (work / "qa" / "hf-check.json").write_text(json.dumps(j, indent=1))
    finds = [f | {"area": k} for k, v in j.items() if isinstance(v, dict) for f in v.get("findings", []) or []]
    errs = [f for f in finds if f.get("severity") == "error"]
    warns = [f for f in finds if f.get("severity") == "warning" and f.get("code") not in
             ("timeline_track_too_dense", "nested_structure_needs_subcomposition")]  # fine for a single-file reel
    print(f"check: {len(errs)} error(s), {len(warns)} warning(s) worth a look")
    for f in errs + warns:
        print(f"  {f['severity'].upper():7} {f['area']}/{f['code']}: {f.get('message', '')[:200]}\n          fix: {f.get('fixHint', '')[:200]}")
    return not errs


def snap(work, times, zoom, name):
    tmp = work / "qa" / "snap"
    if tmp.exists():
        shutil.rmtree(tmp)
    extra = ["--zoom", zoom] if zoom else []
    npx_hf("snapshot", "--at", times, "--no-end", "--describe", "false", "-o", str(tmp), *extra, cwd=work / "hf")
    pngs = sorted(tmp.glob("*.png"), key=lambda p: float(re.findall(r"[0-9.]+", p.stem)[-1] or 0) if re.findall(r"[0-9.]+", p.stem) else 0)
    pngs = [p for p in pngs if "sheet" not in p.name]
    if not pngs:
        sys.exit("snapshot made no frames")
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in pngs]
    h = 960
    ims = [im.resize((round(im.width * h / im.height), h)) for im in ims]
    sheet = Image.new("RGB", (sum(i.width for i in ims) + 12 * (len(ims) - 1), h + 50), "white")
    x = 0
    d = ImageDraw.Draw(sheet)
    for p, im in zip(pngs, ims):
        sheet.paste(im, (x, 50))
        d.text((x + 8, 14), p.stem, fill=(16, 32, 58))
        x += im.width + 12
    out = progress_path(work, f"snap-{name or 'frames'}.png")
    sheet.save(out)
    print("sheet:", out, "| frames:", tmp)


def render(work, out, draft, hf=None):
    hf = hf or work / "hf"
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    r = npx_hf("render", "-o", str(out), "-q", "draft" if draft else "delivery", "--quiet", cwd=hf, check=False, capture=True)
    log = work / "qa" / "render.log"
    log.parent.mkdir(exist_ok=True)
    log.write_text(r.stdout + "\n" + r.stderr)
    if r.returncode != 0 or not out.exists():
        sys.exit(f"render failed, see {log}\n" + (r.stderr or r.stdout)[-1500:])
    print(f"rendered {out} in {time.time() - t:.0f}s")


def slice_(work, name, a, b, index):
    """Copy the project with every timed element shifted by -a, root length b-a, media trimmed to match."""
    src = work / "hf"
    dst = work / "variations" / f"_{name}"
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for p in src.iterdir():
        if p.name not in ("index.html", "renders", ".hyperframes", "node_modules") and not p.name.startswith("index-"):
            (dst / p.name).symlink_to(p.resolve())
    html = Path(index).read_text() if index else (src / "index.html").read_text()
    L = round(b - a, 4)

    def shift(m):
        tag = m.group(0)
        if 'data-composition-id="main"' in tag:
            return re.sub(r'data-duration="[^"]*"', f'data-duration="{L}"', tag)
        s = float(re.search(r'data-start="([-0-9.]+)"', tag).group(1))
        dm = re.search(r'data-duration="([-0-9.]+)"', tag)
        d = float(dm.group(1)) if dm else 1e6
        ns, ne = s - a, s + d - a
        if ne <= 0 or ns >= L:
            ns, ne = L + 5, L + 5.1
        media_off = 0.0
        if ns < 0:
            media_off, ns = -ns, 0.0
        tag = re.sub(r'data-start="[^"]*"', f'data-start="{ns:.4f}"', tag)
        if dm:
            tag = re.sub(r'data-duration="[^"]*"', f'data-duration="{ne - ns:.4f}"', tag)
        if media_off and re.match(r"<(video|audio)\b", tag):
            mm = re.search(r'data-media-start="([-0-9.]+)"', tag)
            base = float(mm.group(1)) if mm else 0.0
            tag = re.sub(r'\s*data-media-start="[^"]*"', "", tag)
            tag = tag[:-1].rstrip("/").rstrip() + f' data-media-start="{base + media_off:.4f}">'
        return tag
    html = re.sub(r"<[a-zA-Z][^<>]*\bdata-start=\"[^\"]*\"[^<>]*>", shift, html)
    html = html.replace('<script src="assets/kit.js"></script>', f'<script>window.KIT_T0 = {a};</script>\n    <script src="assets/kit.js"></script>')
    (dst / "index.html").write_text(html)
    out = work / "variations" / f"{name}.mp4"
    render(work, out, True, hf=dst)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2:
        sys.exit(__doc__)
    cmd, work = a[0], Path(a[1]).resolve()
    if cmd == "new":
        new(work, arg(a, "--title", work.name), "--force" in a)
    elif cmd == "check":
        sys.exit(0 if check(work) else 1)
    elif cmd == "snap":
        snap(work, a[2], arg(a, "--zoom"), arg(a, "--name"))
    elif cmd == "render":
        render(work, arg(a, "--out", str(work / f"{work.name}.mp4")), "--draft" in a)
    elif cmd == "slice":
        slice_(work, a[2], float(a[3]), float(a[4]), arg(a, "--index"))
    else:
        sys.exit(__doc__)
