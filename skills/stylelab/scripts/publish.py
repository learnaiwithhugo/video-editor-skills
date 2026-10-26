#!/usr/bin/env python3
"""Get the style page ready to publish as a Claude artifact, and say exactly what to send.
Standard library only (ffmpeg is used only when something is too big). Safe to run again any time.

Usage (STYLE = the style folder):
  python3 -I publish.py "STYLE" [--all]
      1. Brings the bundle in STYLE/page/ up to date: copies (hard link when it can, else a plain copy)
         sfx/ (sfx.json + the sounds it lists), images/ (candidates, picks.json, index.json, liked/, disliked/,
         recreate sheets), creators.json + its poster pictures, locked/ (brand and the locks), profile.json,
         and writes assets/has.json (which optional files exist). The originals are only read.
      2. Works out which files of the bundle changed since the last publish and prints ONE JSON object:
           file_path   the page to publish (STYLE/page/index.html)
           root        STYLE/page
           files       {"<published path>": "<path under root>", ...} only what changed; null = removed
           url         the saved artifact link (artifact.json) or null
           batches     only when more than 240 files (or 60 MB) changed: the same paths in groups to publish one
                       call after another, all with the same file_path and url
           total_mb    size of the whole bundle (changed_mb = what changed)
           page_changed, first_publish, shrunk, warnings
         --all ignores what was published before and lists every file.
  python3 -I publish.py "STYLE" --mark-published
      Run it AFTER the Artifact call worked: it records what that listing contained, so the next listing only
      shows what changed since. (Not run = the next listing repeats the same files.)
  python3 -I publish.py "STYLE" --url "<artifact link>" [--mark-published]
      Saves the link in STYLE/artifact.json ({"url", "saved_at"}); later publishes pass it as `url`.

What is published, and nothing else: index.html app.js boot.js style.css library.js custom.js round.json
profile.json locked/ assets/ sfx/ images/ creators.json creators/. Never storyboards/, references, rounds/ or any
other html page: another skill keeps its own files in page/ and they stay private.
Size rules: a file over 14 MB is shrunk with ffmpeg into page/_publish/ (video to 720x1280 H.264 CRF 28 with
faststart and its sound; the see-through face cut-out keeps its see-through; pictures to a 1600 px JPEG of
about q85; a picture in images/ over 1 MB gets the same treatment). The original is never touched. A text file over
15 MB is an error. Keeps STYLE/publish-manifest.json (path -> sha1 + size of what was last published).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOP_FILES = ["index.html", "app.js", "boot.js", "style.css", "library.js", "custom.js", "round.json", "profile.json", "creators.json"]
TOP_DIRS = ["locked", "assets", "sfx", "images", "creators"]
LOCKS = ["brand", "text_fade", "shine", "zoom", "shadow"]            # locked/<name>.json files the page may read
HAS = ["assets/face-cutout.webm", "assets/face-cutout-hevc.mp4", "assets/folder.png", "assets/site.png", "assets/repo.png", "assets/bright.png",
       "assets/face-loop.mp4", "assets/pfp.jpg", "assets/site.json", "assets/repo.json",
       # the page's optional data files: listing them false keeps the console clean (no 404s)
       "round.json", "locked/brand.json", "locked/shine.json", "locked/zoom.json", "locked/shadow.json",
       "locked/text_fade.json", "profile.json", "sfx/sfx.json", "creators.json", "images/candidates/index.json",
       "images/index.json", "images/picks.json", "assets/icons/icons.json", "assets/photos/photos.json"]
MIRRORS = ["sfx", "images", "locked", "creators"]                   # folders in page/ that this script owns (copies of the style folder's)
SHRUNK = "_publish"                                                 # where shrunk copies live (inside page/, never published as itself)
BIG = 14 * 1024 * 1024
TEXT_BIG = 15 * 1024 * 1024
IMAGE_BIG = 1024 * 1024                                             # pictures in images/
BATCH_FILES, BATCH_BYTES = 240, 60 * 1024 * 1024
VIDEO = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
PHOTO = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO = {".wav", ".mp3", ".m4a", ".aif", ".aiff", ".flac", ".ogg"}
TEXT = {".json", ".js", ".css", ".html", ".txt", ".svg", ".md", ".csv", ".map"}
POSTER_KEYS = {"poster", "image", "img", "thumb", "thumbnail", "pfp", "avatar", "photo"}


class Stop(Exception):
    pass


# ---------------------------------------------------------------- small helpers
def jload(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def jdump_if_changed(obj, dest):
    """Write JSON as a fresh file (never into a hard link of someone's original). Untouched when it's already the same."""
    dest = Path(dest)
    text = json.dumps(obj, indent=1, ensure_ascii=False)
    try:
        if dest.read_text() == text:
            return
    except OSError:
        pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    dest.write_text(text)


def link_or_copy(src, dest):
    """Make dest a copy of src without ever writing into src: a hard link when possible, else a plain copy."""
    src, dest = Path(src), Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        try:
            if os.path.samefile(src, dest):
                return
            a, b = src.stat(), dest.stat()
            if a.st_size == b.st_size and a.st_mtime_ns == b.st_mtime_ns:   # a copy that is still current
                return
        except OSError:
            pass
        dest.unlink()
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def posix(p):
    return Path(p).as_posix()


def run(cmd, what):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise Stop(f"ffmpeg couldn't {what}: {r.stderr.strip()[-300:]}")
    return r


def outside_cwd_warning(style):
    cwd = Path.cwd().resolve()
    try:
        Path(style).resolve().relative_to(cwd)
        return ""
    except ValueError:
        return (f"{style} is not inside the folder Claude Code was opened in ({cwd}). The Artifact tool can only publish files "
                f"from the folder Claude Code was opened in, so this publish will be refused. Open Claude Code in a folder that "
                f"contains the style folder (suggested: ./my-style).")


# ---------------------------------------------------------------- step 1: bring the bundle up to date
class Bundle:
    def __init__(self, style):
        self.style = style
        self.page = style / "page"
        self.owned = set()          # files (relative to page/, posix) this run made or checked in the mirror folders
        self.warnings = []

    def mirror_file(self, src, rel):
        link_or_copy(src, self.page / rel)
        self.owned.add(rel)

    def mirror_json(self, obj, rel):
        jdump_if_changed(obj, self.page / rel)
        self.owned.add(rel)

    # ---- sfx
    def sfx(self):
        src = self.style / "sfx"
        data = jload(src / "sfx.json")
        if data is None:
            return
        self.mirror_json(data, "sfx/sfx.json")
        items = data if isinstance(data, list) else data.get("sounds", [])
        for d in items:
            f = d.get("file") if isinstance(d, dict) else None
            if not f:
                continue
            if (src / f).is_file():
                self.mirror_file(src / f, f"sfx/{f}")
            else:
                self.warnings.append(f"sfx/sfx.json lists {f} but the file isn't in sfx/")

    # ---- images
    def images(self):
        src = self.style / "images"
        if not src.is_dir():
            return
        for name in ("picks.json", "index.json"):
            if (src / name).is_file():
                self.mirror_json(jload(src / name, {}), f"images/{name}")
        cand = src / "candidates"
        if (cand / "index.json").is_file():
            self.mirror_json(jload(cand / "index.json", {}), "images/candidates/index.json")
        for f in sorted(cand.glob("*/*.jpg")) if cand.is_dir() else []:
            if re.fullmatch(r"[pc]\d+\.jpg", f.name, re.I):
                self.mirror_file(f, f"images/candidates/{f.parent.name}/{f.name}")
        for folder in ("liked", "disliked"):
            for f in sorted((src / folder).glob("*")) if (src / folder).is_dir() else []:
                if f.suffix.lower() in PHOTO and f.is_file():
                    self.mirror_file(f, f"images/{folder}/{f.name}")
        for f in sorted((src / "recreate").glob("sheet-*.jpg")) if (src / "recreate").is_dir() else []:
            self.mirror_file(f, f"images/recreate/{f.name}")

    # ---- creators + their pictures
    def find_picture(self, value):
        v = str(value).strip()
        if not v or re.match(r"^(https?:|data:|//)", v):
            return None
        v = v.lstrip("/")
        for base in (self.style, self.style / "references", self.page, self.style / "creators"):
            p = base / v
            if p.is_file() and p.suffix.lower() in PHOTO:
                return p
        return None

    def poster_for(self, reel_file):
        """A still from a reference reel (page/creators/<name>.jpg) so the page has something to show: the reels
        themselves (references/) are never published."""
        video = self.style / "references" / reel_file
        if not video.is_file() or video.suffix.lower() not in VIDEO:
            return None
        rel = "creators/" + re.sub(r"[^a-z0-9]+", "-", video.stem.lower()).strip("-") + ".jpg"
        dest = self.page / rel
        if dest.is_file() and dest.stat().st_mtime_ns >= video.stat().st_mtime_ns:
            self.owned.add(rel)
            return rel
        if not shutil.which("ffmpeg"):
            self.warnings.append(f"creators: can't make a still for {reel_file} (ffmpeg missing)")
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.6", "-i", str(video), "-frames:v", "1",
                            "-vf", "scale=480:-2", "-q:v", "4", str(dest)], capture_output=True, text=True)
        if r.returncode or not dest.is_file():
            self.warnings.append(f"creators: couldn't take a still from {reel_file}")
            return None
        self.owned.add(rel)
        return rel

    def creators(self):
        data = jload(self.style / "creators.json")
        if data is None:
            return
        taken = {}

        def bring(obj):
            if isinstance(obj, dict):
                for k, v in list(obj.items()):
                    if k in POSTER_KEYS and isinstance(v, str):
                        p = self.find_picture(v)
                        if p:
                            try:
                                p.resolve().relative_to((self.page / "creators").resolve())
                                inside = True      # already sits in page/creators/: keep it as it is
                            except ValueError:
                                inside = False
                            if inside:
                                rel = "creators/" + p.name
                                self.owned.add(rel)
                            else:
                                name = p.name
                                while name in taken and taken[name] != p:
                                    name = "x-" + name
                                taken[name] = p
                                rel = "creators/" + name
                                self.mirror_file(p, rel)
                            obj[k] = rel
                    else:
                        bring(v)
                if "file" in obj and "poster" not in obj and isinstance(obj.get("file"), str):
                    rel = self.poster_for(obj["file"])
                    if rel:
                        obj["poster"] = rel
            elif isinstance(obj, list):
                for x in obj:
                    bring(x)
        bring(data)
        self.mirror_json(data, "creators.json")
        self.owned.add("creators.json")

    # ---- locks, profile, has.json
    def locks(self):
        for name in LOCKS:
            f = self.style / "locked" / f"{name}.json"
            if f.is_file():
                self.mirror_json(jload(f, {}), f"locked/{name}.json")

    def profile(self):
        f = self.style / "profile.json"
        if f.is_file():
            self.mirror_json(jload(f, {}), "profile.json")

    def has(self):
        has = {k: (self.page / k).is_file() for k in HAS}
        jdump_if_changed(has, self.page / "assets" / "has.json")

    def prune(self):
        """Mirror folders hold copies only: take out copies whose original is gone (sounds dropped, picks cleared)."""
        for top in MIRRORS:
            base = self.page / top
            if not base.is_dir():
                continue
            for f in sorted(base.rglob("*"), reverse=True):
                rel = posix(f.relative_to(self.page))
                if f.is_file() and rel not in self.owned:
                    f.unlink()
                elif f.is_dir() and not any(f.iterdir()):
                    f.rmdir()

    def cutout(self):
        """Artifacts don't serve .mov. A style folder made before the cut-out moved to .mp4 still has
        assets/face-cutout.mov: repackage it (no re-encode, the see-through part survives) as face-cutout-hevc.mp4."""
        mov, mp4 = self.page / "assets" / "face-cutout.mov", self.page / "assets" / "face-cutout-hevc.mp4"
        if mov.is_file() and not mp4.is_file():
            run(["ffmpeg", "-v", "error", "-y", "-i", str(mov), "-c", "copy", "-tag:v", "hvc1", "-movflags", "+faststart", str(mp4)],
                "repackage the Safari cut-out as .mp4")

    def run(self):
        self.cutout()
        self.sfx()
        self.images()
        self.creators()
        self.locks()
        self.profile()
        self.prune()
        self.has()


# ---------------------------------------------------------------- step 2: what is in the bundle, shrunk where needed
def walk_bundle(page):
    """Every file that gets published, as posix paths relative to page/. Nothing outside the StyleLab bundle."""
    out = []
    for name in TOP_FILES:
        if (page / name).is_file():
            out.append(name)
    for top in TOP_DIRS:
        base = page / top
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in ("old", "__MACOSX"))
            for f in sorted(files):
                if f.startswith(".") or f.endswith(".tmp") or ".tmp." in f or f == "Thumbs.db" or f.lower().endswith(".mov"):
                    continue
                out.append(posix((Path(root) / f).relative_to(page)))
    return out


def scale_filter(w, h):
    return f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2"


def shrink(src, out, rel, ladder_step=0):
    """Write a smaller copy of src to out (a new file, never src). Returns nothing; raises Stop when it can't."""
    if not shutil.which("ffmpeg"):
        raise Stop(f"{rel} is too big to publish and ffmpeg isn't installed to shrink it. Install it (brew install ffmpeg) and run this again.")
    ext = Path(rel).suffix.lower()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name("tmp-" + out.name)
    if tmp.exists():
        tmp.unlink()
    if ext in VIDEO:
        w, h, crf = [(720, 1280, 28), (540, 960, 32), (360, 640, 36)][min(ladder_step, 2)]
        name = Path(rel).name
        if name.startswith("face-cutout") and ext == ".webm":     # see-through video: keep the see-through
            cmd = ["ffmpeg", "-v", "error", "-y", "-c:v", "libvpx-vp9", "-i", str(src), "-vf", scale_filter(w, h) + ",format=yuva420p",
                   "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", str(crf + 10), "-row-mt", "1", "-auto-alt-ref", "0",
                   "-an", "-metadata:s:v:0", "alpha_mode=1", str(tmp)]
        elif name.startswith("face-cutout") and ext == ".mov":
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", scale_filter(w, h), "-c:v", "hevc_videotoolbox", "-alpha_quality", "0.6",
                   "-b:v", str(max(1, 4 - ladder_step)) + "M", "-tag:v", "hvc1", "-an", str(tmp)]
        elif ext == ".webm":
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", scale_filter(w, h), "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf + 8),
                   "-row-mt", "1", "-map", "0:v:0", "-map", "0:a:0?", "-c:a", "libopus", "-b:a", "64k", str(tmp)]
        else:
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", scale_filter(w, h), "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map", "0:v:0", "-map", "0:a:0?", "-c:a", "aac", "-b:a", "96k", str(tmp)]
        run(cmd, f"shrink {rel}")
    elif ext in PHOTO:
        vf = "scale=w='min(1600,iw)':h='min(1600,ih)':force_original_aspect_ratio=decrease"
        if ext in (".jpg", ".jpeg"):
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf, "-frames:v", "1", "-q:v", "3", "-update", "1", str(tmp)]
        elif ext == ".png":
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf, "-frames:v", "1", "-compression_level", "9", "-update", "1", str(tmp)]
        else:
            cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", vf, "-frames:v", "1", "-c:v", "libwebp", "-quality", "85", "-update", "1", str(tmp)]
        run(cmd, f"shrink {rel}")
    elif ext in AUDIO:
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le" if ext in (".wav", ".aif", ".aiff") else "copy", str(tmp)], f"shrink {rel}")
    else:
        raise Stop(f"{rel} is {src.stat().st_size / 1e6:.1f} MB and I don't know how to shrink that kind of file. Leave it out of page/ or make it smaller.")
    if not tmp.is_file() or tmp.stat().st_size == 0:
        raise Stop(f"ffmpeg gave back nothing for {rel}")
    if out.exists():
        out.unlink()
    tmp.rename(out)
    if ext in VIDEO and out.stat().st_size > BIG and ladder_step < 2:   # still too big: smaller picture, stronger squeeze
        shrink(src, out, rel, ladder_step + 1)


def limit_for(rel):
    ext = Path(rel).suffix.lower()
    return IMAGE_BIG if (rel.startswith("images/") and ext in PHOTO) else BIG


def prepare(page, rels, shrunk_log):
    """-> {published path: {"src": path under page/ to send, "sha1", "size"}}. Shrunk copies go in page/_publish/."""
    cache_file = page / SHRUNK / ".cache.json"
    cache = jload(cache_file, {})
    new_cache, used, info = {}, set(), {}
    for rel in rels:
        src = page / rel
        st = src.stat()
        ext = Path(rel).suffix.lower()
        if ext in TEXT or ext == "":
            if st.st_size > TEXT_BIG:
                raise Stop(f"{rel} is a text file of {st.st_size / 1e6:.1f} MB; the limit is 15 MB. Make it smaller.")
            send = rel
        elif st.st_size > limit_for(rel):
            sig = [st.st_size, st.st_mtime_ns]
            out_rel = f"{SHRUNK}/{rel}"
            hit = cache.get(rel)
            if hit and hit.get("sig") == sig and (page / out_rel).is_file():
                new_cache[rel] = hit
            else:
                shrink(src, page / out_rel, rel)
                new_cache[rel] = {"sig": sig}
                shrunk_log.append({"file": rel, "from_mb": round(st.st_size / 1e6, 1), "to_mb": round((page / out_rel).stat().st_size / 1e6, 1)})
            send = out_rel
            used.add(out_rel)
            final = (page / out_rel).stat().st_size
            if final > BIG + 1024 * 1024 and not rel.startswith("images/"):
                raise Stop(f"{rel} is still {final / 1e6:.1f} MB after shrinking (the limit is 15 MB). Use a shorter or smaller file.")
        else:
            send = rel
        p = page / send
        info[rel] = {"src": send, "sha1": sha1_of(p), "size": p.stat().st_size}
    # tidy: shrunk copies whose original is gone or now small enough
    base = page / SHRUNK
    if base.is_dir():
        for f in sorted(base.rglob("*"), reverse=True):
            if f.is_file() and f.name != ".cache.json" and posix(f.relative_to(page)) not in used:
                f.unlink()
            elif f.is_dir() and not any(f.iterdir()):
                f.rmdir()
    if new_cache:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(new_cache, indent=1))
    elif cache_file.exists():
        cache_file.unlink()
        try:
            base.rmdir()
        except OSError:
            pass
    return info


# ---------------------------------------------------------------- the listing
def make_batches(files):
    """Split a big change into publishes of at most BATCH_FILES files / BATCH_BYTES, core files first."""
    def order(p):
        top = p.split("/")[0]
        return (0 if "/" not in p else 1 if top in ("locked", "sfx") else 2, p)
    groups, cur, size = [], [], 0
    for path in sorted(files, key=order):
        n = files[path]["size"] if isinstance(files[path], dict) else 0
        if cur and (len(cur) >= BATCH_FILES or size + n > BATCH_BYTES):
            groups.append(cur)
            cur, size = [], 0
        cur.append(path)
        size += n
    if cur:
        groups.append(cur)
    return groups


def listing(style, use_all):
    page = style / "page"
    warnings = []
    warn = outside_cwd_warning(style)
    if warn:
        warnings.append(warn)
        print("WARNING: " + warn, file=sys.stderr)
    if not (page / "index.html").is_file():
        raise Stop(f"There is no page yet ({page / 'index.html'}). Run setup.py --init on the style folder first.")
    b = Bundle(style)
    b.run()
    warnings += b.warnings
    shrunk = []
    info = prepare(page, walk_bundle(page), shrunk)
    manifest = jload(style / "publish-manifest.json", {}) or {}
    prev = manifest.get("files", {})
    changed = {p for p, v in info.items() if use_all or prev.get(p, {}).get("sha1") != v["sha1"]}
    removed = [] if use_all else sorted(p for p in prev if p not in info)
    files = {p: info[p]["src"] for p in sorted(changed) if p != "index.html"}
    sizes = {p: {"size": info[p]["size"]} for p in files}
    nulls = {p: None for p in removed}
    saved = jload(style / "artifact.json", {}) or {}
    out = {"file_path": str(page / "index.html"), "root": str(page), "files": {**files, **nulls}, "url": saved.get("url"),
           "page_changed": "index.html" in changed, "first_publish": not prev,
           "changed": len(files), "removed": len(removed), "unchanged": len(info) - len(changed),
           "total_mb": round(sum(v["size"] for v in info.values()) / 1e6, 1),
           "changed_mb": round(sum(info[p]["size"] for p in changed) / 1e6, 1)}
    if len(files) + len(nulls) > BATCH_FILES or sum(v["size"] for v in sizes.values()) > BATCH_BYTES:
        groups = make_batches({**sizes, **{p: {"size": 0} for p in nulls}})
        out["batches"] = groups
    if shrunk:
        out["shrunk"] = shrunk
    if warnings:
        out["warnings"] = warnings
    # what --mark-published will record: the whole bundle exactly as listed now
    (style / ".publish-pending.json").write_text(json.dumps({"made_at": datetime.now().isoformat(timespec="seconds"),
                                                              "files": {p: {"sha1": v["sha1"], "size": v["size"]} for p, v in info.items()}}))
    print(f"{len(files)} file(s) to send ({out['changed_mb']} MB), {len(removed)} to remove, {out['unchanged']} unchanged; "
          f"bundle {out['total_mb']} MB." + (" Page itself changed." if out["page_changed"] else ""), file=sys.stderr)
    return out


def mark_published(style):
    pending = jload(style / ".publish-pending.json")
    if not pending:
        raise Stop('Nothing to mark: run publish.py "STYLE" first, publish what it lists, then run this.')
    (style / "publish-manifest.json").write_text(json.dumps({"published_at": datetime.now().isoformat(timespec="seconds"), "files": pending["files"]}, indent=1))
    (style / ".publish-pending.json").unlink()
    return {"marked": len(pending["files"])}


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("--"):
        raise SystemExit(__doc__)
    style = Path(os.path.expanduser(a[0])).resolve()
    flags = a[1:]
    if not style.is_dir():
        raise SystemExit(f"I can't find the style folder: {style}")
    url = None
    if "--url" in flags:
        i = flags.index("--url")
        url = flags[i + 1] if i + 1 < len(flags) else ""
        if not url.startswith("http"):
            raise SystemExit('--url needs the artifact link, for example --url "https://claude.ai/artifact/..."')
    try:
        result = {}
        if url:
            (style / "artifact.json").write_text(json.dumps({"url": url, "saved_at": datetime.now().isoformat(timespec="seconds")}, indent=1))
            result["url"] = url
            result["saved"] = str(style / "artifact.json")
        if "--mark-published" in flags:
            result.update(mark_published(style))
        elif not url:
            result = listing(style, "--all" in flags)
    except Stop as e:
        print(f"STOPPED: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
