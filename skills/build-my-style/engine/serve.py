#!/usr/bin/env python3
"""The local page server for one style folder. Standard library only.

Run (Claude normally does this through the skill's scripts/server.py):
  python3 -I serve.py [--port 4870]

Serves page/ at http://localhost:<port>, plus the style folder's locked/, sfx/ and reviews/ so the
pages read the same files Claude writes. Two things can be saved from the browser:
  POST /api/review       -> reviews/<kind>-<round>-<time>.json, newest also copied to reviews/latest.json
                            (or reviews/latest-<kind>.json for anything that isn't a style round)
  POST /api/lock/<name>  -> locked/<name>.json, the previous one moved to locked/old/
GET /api/ping answers with this folder's path, so Claude can tell a stale server from the right one.
"""
import json
import os
import shutil
import sys
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "page")
SHARED = ("locked", "sfx", "reviews")
LOCKABLE = {"shine", "zoom", "shadow", "brand"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PAGE, **kwargs)

    def translate_path(self, path):
        parts = unquote(urlparse(path).path).lstrip("/").split("/")
        if parts and parts[0] in SHARED:
            safe = os.path.normpath(os.path.join(ROOT, *parts))
            if safe.startswith(os.path.join(ROOT, parts[0])):
                return safe
        return super().translate_path(path)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

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
        # Labs that aren't locked yet: answer "null" instead of a 404, so the browser console stays clean.
        if self.path.startswith("/locked/") and self.path.endswith(".json") and not os.path.exists(self.translate_path(self.path)):
            return self.reply(None)
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
        self.send_error(404)

    def log_message(self, fmt, *args):
        # Only saves are logged, so it's easy to see whether a click in the browser reached the server.
        if self.command == "POST":
            print(f"{datetime.now():%H:%M:%S} {self.path} -> {args[1] if len(args) > 1 else ''}", flush=True)


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 4870
    print(f"Style page: http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
