#!/usr/bin/env python3
"""Bring the reference reels into the project: download links (logged out) or copy local files.

Usage:
  python3 -I scripts/fetch.py <style-name> <ROOT> <link or file> [<link or file> ...]

Saves them as ROOT/references/<style-name>/<style-name>-1.mp4, -2.mp4, ... Links are downloaded with
yt-dlp with NO browser cookies (never logged in to anything). Local files are copied, never moved.
"""
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    name, root, items = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
    out = root / "references" / name
    out.mkdir(parents=True, exist_ok=True)
    have = len(list(out.glob(f"{name}-*.mp4")))
    for k, it in enumerate(items, have + 1):
        dst = out / f"{name}-{k}.mp4"
        if Path(it).expanduser().exists():
            shutil.copy2(Path(it).expanduser(), dst)
        else:
            if not shutil.which("yt-dlp"):
                raise SystemExit("yt-dlp is missing. Install it with: brew install yt-dlp  (then run this again)")
            r = subprocess.run(["yt-dlp", "--no-cookies", "-q", "--no-playlist", "-f", "mp4/bv*+ba/b",
                                "--merge-output-format", "mp4", "-o", str(dst), it])
            if r.returncode or not dst.exists():
                print(f"Couldn't download {it}. If it's private or blocked, save the video and pass the file instead.")
                continue
        print(f"saved {dst}")


if __name__ == "__main__":
    main()
