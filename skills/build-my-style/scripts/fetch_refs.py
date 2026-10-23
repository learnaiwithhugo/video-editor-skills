#!/usr/bin/env python3
"""Bring reference reels into the style folder: download links (logged out) or copy local files.

Usage:
  python3 -I fetch_refs.py <STYLE_DIR> <link or file> [<link or file> ...] [--section 0-30]

Saves ref-1.mp4, ref-2.mp4 ... into STYLE_DIR/references/ (numbering carries on from what's there).
Links are downloaded with yt-dlp and NO browser cookies, so nothing is ever logged in. Local files
are copied, never moved. --section 0-30 keeps only those seconds (handy for long YouTube videos).
Writes STYLE_DIR/references/sources.json so every reel keeps its original link.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    args = sys.argv[1:]
    section = None
    if "--section" in args:
        i = args.index("--section")
        section = args[i + 1]
        del args[i:i + 2]
    if len(args) < 2:
        raise SystemExit(__doc__)
    style, items = Path(args[0]).expanduser(), args[1:]
    out = style / "references"
    out.mkdir(parents=True, exist_ok=True)
    src_file = out / "sources.json"
    sources = json.loads(src_file.read_text()) if src_file.exists() else {}
    have = len(list(out.glob("ref-*.mp4")))
    k = have
    failed = []
    for it in items:
        k += 1
        dst = out / f"ref-{k}.mp4"
        local = Path(it).expanduser()
        if local.exists():
            if section:
                a, b = section.split("-")
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", a, "-to", b, "-i", str(local),
                                "-c:v", "libx264", "-crf", "18", "-c:a", "aac", str(dst)], check=True)
            else:
                shutil.copy2(local, dst)
        else:
            if not shutil.which("yt-dlp"):
                raise SystemExit("yt-dlp is missing. Install it with: brew install yt-dlp  (then run this again)")
            cmd = ["yt-dlp", "--no-cookies", "-q", "--no-warnings", "--no-playlist",
                   "-f", "bv*[height<=1920][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
                   "--merge-output-format", "mp4", "-o", str(dst)]
            if section:
                cmd += ["--download-sections", f"*{section}", "--force-keyframes-at-cuts"]
            r = subprocess.run(cmd + [it])
            if r.returncode or not dst.exists():
                print(f"COULDN'T DOWNLOAD {it}  (private, blocked or needs a login). "
                      "Ask for the video file instead and pass its path.")
                failed.append(it)
                k -= 1
                continue
        sources[dst.name] = it
        print(f"saved {dst}")
    src_file.write_text(json.dumps(sources, indent=1))
    sys.exit(1 if failed and k == have else 0)


if __name__ == "__main__":
    main()
