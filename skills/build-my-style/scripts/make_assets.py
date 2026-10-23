#!/usr/bin/env python3
"""Make the preview assets the style page needs, all from the person's own stuff.

Usage:
  python3 -I make_assets.py "<style folder>" face "<their clip>" [--start 3] [--seconds 8]
      A short silent loop of their talking-head footage (page/assets/face-loop.mp4) plus 4 stills
      for the tree diagram (thumb-1..4.jpg). Their original file is only read, never changed.
  python3 -I make_assets.py "<style folder>" icons [App names ...]
      Real app icons from /Applications (e.g. "Claude" "ChatGPT" "Notion"), saved as PNGs with
      page/assets/icons/icons.json. No names = the first 4 it finds from a common list.
  python3 -I make_assets.py "<style folder>" site <url> [--find "text"]
      A full-length phone-width screenshot of a real site (page/assets/site.png + site.json) taken
      after it fully loads, with the box around --find text for the ring. Also bright.png (the top of it),
      the busy background the shadow tests use.
  python3 -I make_assets.py "<style folder>" repo <url> [--find "text"]
      A desktop-width screenshot (page/assets/repo.png + repo.json) for the card / push-in options.
"""
import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
COMMON = ["Claude", "ChatGPT", "Notion", "Slack", "Figma", "Google Chrome", "Safari", "Mail", "Calendar", "Notes",
          "Visual Studio Code", "Spotify", "Final Cut Pro", "CapCut", "Canva", "Obsidian", "Arc"]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"Failed: {' '.join(map(str, cmd[:3]))} ...\n{r.stderr[-600:]}")
    return r.stdout


def face(style, clip, start, seconds):
    assets = style / "page" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    clip = Path(os.path.expanduser(clip))
    if not clip.exists():
        raise SystemExit(f"Can't find {clip}")
    # 9:16 crop from the centre, 720x1280 is plenty for previews, no sound, small file.
    vf = "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=720:1280,fps=30"
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(seconds), "-i", str(clip), "-vf", vf, "-an",
         "-c:v", "libx264", "-crf", "24", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(assets / "face-loop.mp4")])
    for k in range(4):
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{0.5 + k * seconds / 4:.2f}", "-i", str(assets / "face-loop.mp4"),
             "-frames:v", "1", "-vf", "scale=360:640", "-q:v", "4", str(assets / f"thumb-{k + 1}.jpg")])
    print(f"saved face-loop.mp4 ({seconds}s from {start}s) and 4 thumbnails")


def find_app(name):
    for base in ["/Applications", "/System/Applications", "/System/Applications/Utilities", str(Path.home() / "Applications")]:
        for cand in Path(base).glob("*.app"):
            if cand.stem.lower() == name.lower():
                return cand
    for base in ["/Applications"]:   # "Claude" also matches "Claude (work).app"
        for cand in sorted(Path(base).glob(f"{name}*.app")):
            return cand
    return None


def icon_file(app):
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    res = app / "Contents" / "Resources"
    name = info.get("CFBundleIconFile") or ""
    for cand in [res / name, res / f"{name}.icns"] + sorted(res.glob("*.icns")):
        if cand.is_file() and cand.suffix == ".icns":
            return cand
    return None


def icons(style, names):
    out = style / "page" / "assets" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    found = []
    for name in names or COMMON:
        app = find_app(name)
        src = app and icon_file(app)
        if not src:
            if names:
                print(f"  not installed (or no icon): {name}")
            continue
        slug = name.lower().replace(" ", "-")
        dst = out / f"{slug}.png"
        run(["sips", "-s", "format", "png", "-Z", "512", str(src), "--out", str(dst)])
        found.append({"name": name, "file": f"assets/icons/{slug}.png", "app": str(app)})
        if not names and len(found) >= 4:
            break
    (out / "icons.json").write_text(json.dumps(found, indent=1))
    print("icons: " + (", ".join(i["name"] for i in found) or "none found"))
    if len(found) < 3:
        print("  fewer than 3 icons: name some apps they use that are installed, so the logo options look right")


def shot(style, kind, url, find):
    assets = style / "page" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is needed for screenshots.")
    if kind == "site":   # phone width at 2.5x = a 1080-pixel-wide image
        args = ["--width", "432", "--height", "900", "--scale", "2.5", "--mobile", "--full", "--max", "1700"]
    else:
        args = ["--width", "1440", "--height", "1200", "--scale", "1.25"]
    cmd = [node, str(SK / "scripts" / "shot.mjs"), "--url", url, "--out", str(assets / f"{kind}.png"), "--wait", "2500",
           "--json", str(assets / f"{kind}.json")] + args + (["--find", find] if find else [])
    meta = json.loads(run(cmd).strip().splitlines()[-1])
    j = json.loads((assets / f"{kind}.json").read_text())
    j["name"] = url.split("//")[-1].split("/")[0].replace("www.", "") if kind == "site" else url.rstrip("/").split("/")[-1]
    if not j.get("target"):   # no text to ring: use a sensible box near the top
        j["target"] = [int(j["w"] * .06), int(min(j["h"], 1500) * .2), int(j["w"] * .5), int(min(j["h"], 1500) * .1)]
    (assets / f"{kind}.json").write_text(json.dumps(j, indent=1))
    # bright.png = the busy, bright background the shadow tests use. A repo or docs page (white, lots of
    # text) is the hardest case for white captions, so a repo shot replaces whatever was there.
    if kind == "repo" or not (assets / "bright.png").exists():
        run(["ffmpeg", "-v", "error", "-y", "-i", str(assets / f"{kind}.png"), "-vf", ("crop=min(iw\\,1300):ih:0:0," if kind == "repo" else "") + "scale=1080:-2,crop=iw:min(ih\\,2200):0:0", str(assets / "bright.png")])
    print(f"saved {kind}.png {meta['width']}x{meta['height']}, target {j['target']}" + (f", {len(meta['errors'])} page errors (normal for some sites)" if meta["errors"] else ""))


def main():
    a = sys.argv[1:]
    if len(a) < 2:
        raise SystemExit(__doc__)
    style, cmd, rest = Path(os.path.expanduser(a[0])).resolve(), a[1], a[2:]
    opt = lambda k, d=None: rest[rest.index(k) + 1] if k in rest else d
    if cmd == "face":
        face(style, rest[0], float(opt("--start", 0)), float(opt("--seconds", 8)))
    elif cmd == "icons":
        icons(style, [r for r in rest])
    elif cmd in ("site", "repo"):
        shot(style, cmd, rest[0], opt("--find"))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
