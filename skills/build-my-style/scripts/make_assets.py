#!/usr/bin/env python3
"""Make the preview assets the style page needs, all from the person's own stuff.

Usage:
  python3 -I make_assets.py "<style folder>" face "<their clip>" [--start 3] [--seconds 8]
      A short silent loop of their talking-head footage (page/assets/face-loop.mp4) plus 4 stills
      for the tree diagram (thumb-1..4.jpg). Their original file is only read, never changed.
      When this Mac can, it also makes the head cut-out at the end (see cutout), so nobody has to ask for it.
  python3 -I make_assets.py "<style folder>" cutout
      The person cut out of the face clip, frame for frame, on a see-through background:
      page/assets/face-cutout.webm (plays in Chrome) and face-cutout.mov (plays in Safari). This is what
      lets words sit BEHIND their head: footage at the back, the words in the middle, this on top.
      Mac only (uses Apple's built-in person detection, free, nothing leaves the Mac). It lines up with
      face-loop.mp4 exactly (same size, speed and length). Runs by itself at the end of "face".
  python3 -I make_assets.py "<style folder>" folder
      The real Mac folder icon as page/assets/folder.png (1024 px), for the "files in a folder" options.
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
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
FOLDER_ICONS = Path("/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources")
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
    archive(assets, ["face-loop.mp4"])   # a re-run keeps the previous clip in assets/old/
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(seconds), "-i", str(clip), "-vf", vf, "-an",
         "-c:v", "libx264", "-crf", "24", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(assets / "face-loop.mp4")])
    for k in range(4):
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{0.5 + k * seconds / 4:.2f}", "-i", str(assets / "face-loop.mp4"),
             "-frames:v", "1", "-vf", "scale=360:640", "-q:v", "4", str(assets / f"thumb-{k + 1}.jpg")])
    print(f"saved face-loop.mp4 ({seconds}s from {start}s) and 4 thumbnails")
    # A new clip makes any old cut-out wrong (different footage), so it is replaced now, or put aside.
    ok, why = cutout_tools()
    if ok:
        print("Now cutting you out of the footage, so words can sit behind your head (about a minute) ...", flush=True)
        cutout(style)
    else:
        archive(assets, CUTOUT_FILES)
        print(f"Skipped the head cut-out ({why}).\n  Everything else works without it. Only 'text behind your head' needs it.")


# ---- head cut-out (person on a see-through background) ------------------------------------------------
CUTOUT_FILES = ["face-cutout.webm", "face-cutout.mov"]


class Skip(Exception):
    """Something the person can't fix by themselves; the message is already plain English."""


def archive(assets, names):
    """Move earlier versions into assets/old/ (never delete the person's files)."""
    for n in names:
        f = assets / n
        if f.exists():
            (assets / "old").mkdir(exist_ok=True)
            shutil.move(str(f), str(assets / "old" / f"{f.stem}-{time.strftime('%Y%m%d-%H%M%S')}{f.suffix}"))


def sh(cmd, what):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        tail = "\n".join((r.stderr or r.stdout).strip().splitlines()[-6:])
        raise Skip(f"{what} didn't work.\n  {tail}")
    return r.stdout


def cutout_tools():
    """(True, "") when this Mac can make the cut-out, else (False, the reason in plain English)."""
    if platform.system() != "Darwin":
        return False, "it uses Apple's built-in person detection, which only exists on a Mac"
    v = subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True).stdout.strip() or "0"
    parts = [int(x) if x.isdigit() else 0 for x in v.split(".")] + [0, 0]
    major = 11 if (parts[0], parts[1]) == (10, 16) else parts[0]
    if major < 12:
        return False, f"it needs macOS 12 or newer, and this Mac has {v}"
    # `swift` on a Mac without Apple's free developer tools opens an install pop-up, so ask first.
    if subprocess.run(["xcode-select", "-p"], capture_output=True).returncode:
        return False, "Apple's free developer tools aren't installed. To add them, open Terminal and paste: xcode-select --install"
    if not (shutil.which("swiftc") or shutil.which("swift")):
        return False, "the Swift tool that comes with Apple's developer tools wasn't found"
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return False, "ffmpeg isn't installed"
    enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    if "libvpx-vp9" not in enc:
        return False, "this ffmpeg can't make see-through video (it lacks the VP9 encoder). In Terminal: brew reinstall ffmpeg"
    return True, ""


def cutout(style):
    assets = style / "page" / "assets"
    loop = assets / "face-loop.mp4"
    if not loop.exists():
        raise SystemExit("There's no face clip yet. Make it first: make_assets.py \"<style folder>\" face \"<their clip>\"")
    ok, why = cutout_tools()
    if not ok:
        print(f"Can't make the head cut-out on this computer: {why}.\n  Everything else in Style Studio works without it.")
        return False
    tmp = Path(tempfile.mkdtemp(prefix="style-cutout-"))
    try:
        make_cutout(assets, loop, tmp)
        return True
    except Skip as e:
        print(f"The head cut-out didn't finish. {e}\n  Your face clip and everything else are fine.")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # temp frames only; nothing of theirs


def make_cutout(assets, loop, tmp):
    info = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", loop], "Reading the face clip"))["streams"][0]
    w, h, fps, n = info["width"], info["height"], info["r_frame_rate"], int(info["nb_read_frames"])
    if shutil.disk_usage(tmp).free < 1.5e9:
        raise Skip("There isn't enough free disk space (about 1.5 GB for a minute). Free some up and run it again.")
    frames, masks = tmp / "frames", tmp / "masks"
    frames.mkdir()
    print(f"  1/4 pulling out the {n} frames of the clip", flush=True)
    sh(["ffmpeg", "-v", "error", "-y", "-i", loop, "-fps_mode", "passthrough", "-q:v", "2", frames / "%05d.jpg"], "Pulling out the frames")
    print("  2/4 getting Apple's person finder ready (the first time takes about 30 seconds)", flush=True)
    tool = tmp / "personmask"
    if shutil.which("swiftc"):
        sh(["swiftc", "-O", SK / "scripts" / "personmask.swift", "-o", tool], "Getting the person finder ready")
        run_tool = [tool]
    else:
        run_tool = ["swift", SK / "scripts" / "personmask.swift"]
    print("  3/4 finding you in every frame (the slow part, usually under a minute)", flush=True)
    p = subprocess.Popen([str(c) for c in run_tool + [frames, masks]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    last = ""
    for line in p.stdout:
        last = line.strip() or last
        if "/" in line and "done" not in line:
            print(f"      {line.strip()}", flush=True)
    if p.wait():
        raise Skip(f"Apple's person finder stopped early. {last}")
    got = len(list(masks.glob("*.png")))
    if got != n:
        raise Skip(f"Found you in {got} of {n} frames, so the cut-out would drift out of step.")
    print("  4/4 making the see-through videos", flush=True)
    graph = (f"[1:v]scale={w}:{h}:flags=bicubic,format=gray,boxblur=1:1[m];[0:v][m]alphamerge[v]")   # soft 1 px edge
    src = ["ffmpeg", "-v", "error", "-y", "-i", loop, "-framerate", fps, "-start_number", "1", "-i", masks / "%05d.png",
           "-filter_complex", graph, "-map", "[v]", "-frames:v", str(n), "-an"]
    sh(src + ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28", "-row-mt", "1", "-auto-alt-ref", "0",
              "-metadata:s:v:0", "alpha_mode=1", tmp / "face-cutout.webm"], "Making the Chrome version")
    mov_ok = True
    try:
        sh(src + ["-c:v", "hevc_videotoolbox", "-alpha_quality", "0.8", "-b:v", "8M", "-tag:v", "hvc1", tmp / "face-cutout.mov"],
           "Making the Safari version")
    except Skip as e:
        mov_ok = False
        print(f"  (Safari version skipped. Chrome is the one used for edits. {str(e).splitlines()[0]})")
    names = ["face-cutout.webm"] + (["face-cutout.mov"] if mov_ok else [])
    # Same size, speed and length as the clip, or it would drift against the person's face.
    for nm in names:
        c = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                           "stream=width,height,r_frame_rate,nb_read_frames", "-of", "json", tmp / nm], f"Checking {nm}"))["streams"][0]
        if (c["width"], c["height"], int(c["nb_read_frames"])) != (w, h, n):
            raise Skip(f"{nm} came out {c['width']}x{c['height']} with {c['nb_read_frames']} frames, not {w}x{h} with {n}.")
    archive(assets, CUTOUT_FILES)
    for nm in names:
        shutil.move(str(tmp / nm), str(assets / nm))
    mb = lambda nm: (assets / nm).stat().st_size / 1e6
    print(f"saved face-cutout.webm ({mb('face-cutout.webm'):.1f} MB)" + (f" and face-cutout.mov ({mb('face-cutout.mov'):.1f} MB)" if mov_ok else "")
          + f": {w}x{h}, {n} frames at {fps.replace('/1', '')} fps, the same as face-loop.mp4")


def folder(style):
    assets = style / "page" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    src = next((p for p in [FOLDER_ICONS / "GenericFolderIcon.icns", FOLDER_ICONS / "GenericFolder.icns", FOLDER_ICONS / "FolderIcon.icns"] if p.is_file()), None)
    if not src and FOLDER_ICONS.is_dir():
        src = next(iter(sorted(FOLDER_ICONS.glob("Generic*Folder*.icns"))), None)
    if not src or not shutil.which("sips"):
        print("Couldn't find the Mac's folder icon (this works on a Mac only). Skipping folder.png; the options will draw a plain folder instead.")
        return
    tmp = assets / ".folder-new.png"
    try:
        run(["sips", "-s", "format", "png", "-Z", "1024", str(src), "--out", str(tmp)])
        archive(assets, ["folder.png"])
        shutil.move(str(tmp), str(assets / "folder.png"))
    finally:
        tmp.unlink(missing_ok=True)   # our own half-made file, never theirs
    size = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(assets / "folder.png")]).split()
    print(f"saved folder.png ({size[-3]}x{size[-1]}), the real Mac folder icon from {src.name}")


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
    elif cmd == "cutout":
        sys.exit(0 if cutout(style) or not cutout_tools()[0] else 1)
    elif cmd == "folder":
        folder(style)
    elif cmd == "icons":
        icons(style, [r for r in rest])
    elif cmd in ("site", "repo"):
        shot(style, cmd, rest[0], opt("--find"))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
