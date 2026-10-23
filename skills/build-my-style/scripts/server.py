#!/usr/bin/env python3
"""Start, stop or check the style page server, and never leave a stale one running.

Usage:
  python3 -I server.py start "<style folder>" [--port 4870] [--open]
  python3 -I server.py stop "<style folder>"
  python3 -I server.py status "<style folder>"

Why this exists: in the session that built this skill, an old page server kept answering after a
restart, so the person's "Lock" clicks went to a server that didn't know about locks. start therefore
stops whatever this folder started before, refuses to share a port with a different folder's server,
starts a fresh one, and only reports success once /api/ping answers from THIS folder.
Writes <style>/.server.json (pid, port) and logs saves to <style>/.server.log.
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def ping(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1.5) as r:
            return json.loads(r.read())
    except Exception:
        return None


def port_free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def stop(style):
    info_f = style / ".server.json"
    if not info_f.exists():
        return False
    info = json.loads(info_f.read_text())
    try:
        os.kill(info["pid"], signal.SIGTERM)
        for _ in range(30):
            time.sleep(0.1)
            os.kill(info["pid"], 0)
    except (ProcessLookupError, PermissionError):
        pass
    info_f.unlink()
    return True


def start(style, port, open_it):
    stop(style)
    while True:
        p = ping(port)
        if p and Path(p["style"]).resolve() == style:   # our own orphan from an earlier session
            os.kill(p["pid"], signal.SIGTERM)
            time.sleep(0.5)
            continue
        if port_free(port):
            break
        port += 1
    log = open(style / ".server.log", "a")
    proc = subprocess.Popen([sys.executable, "-I", str(style / "serve.py"), "--port", str(port)], cwd=style,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(50):
        time.sleep(0.1)
        p = ping(port)
        if p and Path(p["style"]).resolve() == style:
            (style / ".server.json").write_text(json.dumps({"pid": proc.pid, "port": port}))
            url = f"http://localhost:{port}"
            print(f"RUNNING {url}")
            if open_it:
                subprocess.run(["open", url])
            return 0
    print("FAILED: the page server didn't start. See .server.log in the style folder.")
    return 1


def status(style):
    info_f = style / ".server.json"
    if info_f.exists():
        info = json.loads(info_f.read_text())
        p = ping(info["port"])
        if p and Path(p["style"]).resolve() == style:
            print(f"RUNNING http://localhost:{info['port']}")
            return 0
    print("STOPPED")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cmd, style = sys.argv[1], Path(os.path.expanduser(sys.argv[2])).resolve()
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 4870
    if cmd == "start":
        sys.exit(start(style, port, "--open" in sys.argv))
    if cmd == "stop":
        print("STOPPED" if stop(style) else "was not running")
    elif cmd == "status":
        sys.exit(status(style))
