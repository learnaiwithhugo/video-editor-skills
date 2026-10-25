#!/usr/bin/env python3
"""The local page server for one style folder. Standard library only.

Run (Claude normally does this through the skill's scripts/server.py):
  python3 -I serve.py [--port 4870]

Serves page/ at http://localhost:<port>, plus these read-only parts of the style folder, so the pages read
the same files Claude writes (a path that tries to climb out of them is refused):
  /locked/ /sfx/ /reviews/ /images/   the folders of the same name
  /refs/...                           the folder references/ (their reels, frames, breakdowns), for example
                                      /refs/analysis/<name>-frames/index.html and /refs/<reel>.mp4
  /creators.json                      creators.json at the style folder's root
A .json file that doesn't exist yet under /locked/, /images/, /assets/ or at /creators.json is answered with an
empty value and a 200 (see EMPTY) instead of a 404, so a fresh style folder opens every page with a clean
console. Real files always win.
Audio and video stream properly: Range requests are answered, so <video> can seek.
Things that can be saved from the browser:
  POST /api/review       -> reviews/<kind>-<round>-<time>.json, newest also copied to reviews/latest.json
                            (or reviews/latest-<kind>.json for anything that isn't a style round)
  POST /api/lock/<name>  -> locked/<name>.json, the previous one moved to locked/old/
  POST /api/images       -> {slug, id, verdict: "like"|"dislike"|null, reason?}: the Images page's buttons.
                            Does exactly what `images.py pick` does (files in images/liked and images/disliked,
                            marks in images/picks.json, list in images/index.json). Keep the two in step.
GET /api/has?f=assets/<file> says whether an optional page file exists yet.
GET /api/ping answers with this folder's path, so Claude can tell a stale server from the right one.
"""
import json
import os
import re
import shutil
import sys
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "page")
SHARED = {"locked": "locked", "sfx": "sfx", "reviews": "reviews", "images": "images", "refs": "references"}  # URL start -> folder
FILES = ("creators.json",)   # single files at the style folder's root
# What a page gets for a .json file that isn't there yet. Anything not listed here gets null (what the pages
# already treat as "not made yet"): the locks, assets/site.json, assets/repo.json.
EMPTY = {
    "/creators.json": {"creators": []},
    "/images/index.json": {"liked": [], "disliked": [], "recreate": []},
    "/images/candidates/index.json": {"queries": []},
    "/images/picks.json": {"picks": []},
    "/assets/icons/icons.json": [],
    "/assets/photos/photos.json": [],
}
LOCKABLE = {"shine", "zoom", "shadow", "brand", "text_fade"}
IMAGES = Path(ROOT) / "images"
IMAGES_LOCK = threading.Lock()


class Slice:
    """The next `left` bytes of an open file, so copying stops where a Range request stops."""

    def __init__(self, f, left):
        self.f, self.left = f, left

    def read(self, n=-1):
        n = self.left if n is None or n < 0 else min(n, self.left)
        data = self.f.read(n)
        self.left -= len(data)
        return data

    def close(self):
        self.f.close()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PAGE, **kwargs)

    def translate_path(self, path):
        parts = unquote(urlparse(path).path).lstrip("/").split("/")
        if parts and parts[0] in SHARED:
            base = os.path.join(ROOT, SHARED[parts[0]])
            safe = os.path.normpath(os.path.join(base, *parts[1:]))
            if safe == base or safe.startswith(base + os.sep):
                return safe
        if len(parts) == 1 and parts[0] in FILES:
            return os.path.join(ROOT, parts[0])
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        # Python's own handler ignores Range, so a <video> can't seek. Answer one byte range properly.
        path = self.translate_path(self.path)
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
        if not m or not (m.group(1) or m.group(2)) or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        if m.group(1):
            start, end = int(m.group(1)), min(int(m.group(2) or size - 1), size - 1)
        else:   # "the last N bytes"
            start, end = max(size - int(m.group(2)), 0), size - 1
        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        return Slice(f, end - start + 1)

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):   # the browser stopped asking (every video seek does this)
            pass

    def reply(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/ping"):
            return self.reply({"style": ROOT, "pid": os.getpid()})
        if self.path.startswith("/api/has"):   # does an optional page file exist yet? (asking for it directly would log a 404)
            f = parse_qs(urlparse(self.path).query).get("f", [""])[0]
            return self.reply({"exists": bool(f) and os.path.isfile(self.translate_path("/" + f.lstrip("/")))})
        # Files that aren't there yet (labs not locked, no icons, images or creators yet): answer with an empty
        # value instead of a 404, so the browser console stays clean.
        url = urlparse(self.path).path
        known = url.startswith(("/locked/", "/images/", "/assets/")) or url.lstrip("/") in FILES
        if known and url.endswith(".json") and not os.path.exists(self.translate_path(self.path)):
            return self.reply(EMPTY.get(url))
        return super().do_GET()

    def body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except (ValueError, json.JSONDecodeError):
            return None

    def do_POST(self):
        data = self.body()
        if not isinstance(data, dict):
            return self.send_error(400, "bad json")
        stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        if self.path == "/api/review":
            kind = str(data.get("kind", "round"))
            if not kind.isidentifier():
                return self.send_error(400, "bad kind")
            folder = os.path.join(ROOT, "reviews")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, f"{kind}-{data.get('round', 'x')}-{stamp}.json")
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            shutil.copyfile(path, os.path.join(folder, "latest.json" if kind == "round" else f"latest-{kind}.json"))
            return self.reply({"saved": "reviews/" + os.path.basename(path)})
        if self.path.startswith("/api/lock/"):
            name = self.path.rsplit("/", 1)[-1]
            if name not in LOCKABLE:
                return self.send_error(400, "bad name")
            locked = os.path.join(ROOT, "locked")
            os.makedirs(os.path.join(locked, "old"), exist_ok=True)
            path = os.path.join(locked, f"{name}.json")
            if os.path.exists(path):
                shutil.move(path, os.path.join(locked, "old", f"{name}-{stamp}.json"))
            data["locked_at"] = datetime.now().isoformat(timespec="seconds")
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            return self.reply({"saved": f"locked/{name}.json"})
        if self.path == "/api/images":
            result, code = image_pick(data)
            return self.reply(result, code)
        self.send_error(404)

    def log_message(self, fmt, *args):
        # Only saves are logged, so it's easy to see whether a click in the browser reached the server.
        if self.command == "POST":
            print(f"{datetime.now():%H:%M:%S} {self.path} -> {args[1] if len(args) > 1 else ''}", flush=True)


# ---- the Images page's Like / Nope buttons (mirrors scripts/images.py: pick + index) ----
def img_slug(text, limit=60):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:limit].strip("-")


def img_archive(path):
    """Replaced files go to images/old/, never away."""
    old = IMAGES / "old"
    old.mkdir(exist_ok=True)
    stamp, n = datetime.now().strftime("%Y-%m-%d-%H%M%S"), 1
    dest = old / f"{path.stem}-{stamp}{path.suffix}"
    while dest.exists():
        n += 1
        dest = old / f"{path.stem}-{stamp}-{n}{path.suffix}"
    shutil.move(str(path), str(dest))


def img_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def img_index():
    picks = {p["file"]: p for p in img_json(IMAGES / "picks.json", {"picks": []}).get("picks", [])}
    out = {"liked": [], "disliked": [], "recreate": []}
    for folder in ("liked", "disliked"):
        files = sorted((IMAGES / folder).glob("*")) if (IMAGES / folder).is_dir() else []
        for f in files:
            if f.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            rel = f"{folder}/{f.name}"
            p = picks.get(rel)
            m = re.fullmatch(r"(.+)-([pc]\d+)(?:-(.+))?", f.stem)
            item = {"file": rel, "slug": p["slug"] if p else (m.group(1) if m else None),
                    "id": p["id"] if p else (m.group(2) if m else None)}
            if p:
                reason = p.get("reason", "")
            else:
                reason = (m.group(3) or "").replace("-", " ") if m else ""
            if folder == "disliked" or reason:
                item["reason"] = reason
            out[folder].append(item)
    rec = IMAGES / "recreate"
    for f in sorted(rec.glob("sheet-*.jpg")) if rec.is_dir() else []:
        out["recreate"].append({"name": f.stem[len("sheet-"):].replace("-", " "), "file": f"recreate/{f.name}"})
    (IMAGES / "index.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    return out


def image_pick(data):
    slug, verdict = str(data.get("slug", "")), data.get("verdict")
    m = re.fullmatch(r"([pc])0*(\d{1,3})", str(data.get("id", "")).strip().lower())
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) or not m or verdict not in ("like", "dislike", None):
        return {"error": "bad request"}, 400
    cid = f"{m.group(1)}{int(m.group(2))}"
    src = IMAGES / "candidates" / slug / f"{m.group(1)}{int(m.group(2)):02d}.jpg"
    if not src.is_file():
        return {"error": f"no picture {cid} in {slug}"}, 404
    reason = str(data.get("reason") or "").strip()[:200]
    with IMAGES_LOCK:
        picks = img_json(IMAGES / "picks.json", {"picks": []})
        mine = [p for p in picks["picks"] if p["slug"] == slug and p["id"] == cid]
        for p in mine:
            if p.get("file") and (IMAGES / p["file"]).is_file():
                img_archive(IMAGES / p["file"])
        picks["picks"] = [p for p in picks["picks"] if p not in mine]
        if verdict:
            folder = "liked" if verdict == "like" else "disliked"
            rs = img_slug(reason, 40) if verdict == "dislike" else ""
            name = f"{slug}-{cid}" + (f"-{rs}" if rs else "") + ".jpg"
            dest = IMAGES / folder / name
            dest.parent.mkdir(exist_ok=True)
            if dest.exists():
                img_archive(dest)
            shutil.copy2(src, dest)
            picks["picks"].append({"slug": slug, "id": cid, "verdict": verdict, "reason": reason,
                                   "file": f"{folder}/{name}", "at": datetime.now().isoformat(timespec="seconds")})
        (IMAGES / "picks.json").write_text(json.dumps(picks, indent=2, ensure_ascii=False))
        idx = img_index()
    return {"saved": True, "verdict": verdict, "liked": len(idx["liked"]), "disliked": len(idx["disliked"])}, 200


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 4870
    print(f"Style page: http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
