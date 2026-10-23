#!/usr/bin/env python3
"""Fallback page server, used only when a style folder has no serve.py of its own.

Serves <root>/page at http://localhost:<port> and saves what the user submits:
  POST /api/review       -> <root>/reviews/round-<round>-<time>.json (+ latest.json)
  POST /api/lock/<name>  -> <root>/locked/<name>.json (the old one moves to locked/old/)
Usage: python3 serve.py --root <style_dir> [--port 4870]
"""
import json
import shutil
import sys
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

a = sys.argv[1:]
ROOT = Path(a[a.index("--root") + 1] if "--root" in a else ".").resolve()
PORT = int(a[a.index("--port") + 1]) if "--port" in a else 4870


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kw):
        super().__init__(*args, directory=str(ROOT / "page"), **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def body(self):
        try:
            return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except json.JSONDecodeError:
            self.send_error(400, "bad json")
            return None

    def reply(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        if self.path == "/api/review":
            data = self.body()
            if data is None:
                return
            d = ROOT / "reviews"
            d.mkdir(exist_ok=True)
            p = d / f"round-{data.get('round', 'x')}-{stamp}.json"
            p.write_text(json.dumps(data, indent=2))
            shutil.copyfile(p, d / "latest.json")
            print(f"{stamp} saved {p.name}", flush=True)
            return self.reply({"saved": p.name})
        if self.path.startswith("/api/lock/"):
            name = self.path.rsplit("/", 1)[-1]
            data = self.body()
            if data is None or not name.isidentifier():
                return self.send_error(400, "bad lock")
            d = ROOT / "locked"
            (d / "old").mkdir(parents=True, exist_ok=True)
            p = d / f"{name}.json"
            if p.exists():
                shutil.move(str(p), str(d / "old" / f"{name}-{stamp}.json"))
            data["locked_at"] = datetime.now().isoformat(timespec="seconds")
            p.write_text(json.dumps(data, indent=2))
            return self.reply({"saved": f"locked/{name}.json"})
        self.send_error(404)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"Pages: http://localhost:{PORT}  (serving {ROOT / 'page'})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
