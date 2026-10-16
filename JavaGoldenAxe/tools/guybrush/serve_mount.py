#!/usr/bin/env python3
"""Serve mount_editor.html so its "Save placements" button can write
mount_placements.json in place (previous file kept as
mount_placements.backup.json).

The page is self-contained; the server exists only so Save can reach the disk.
A browser opened with file:// falls back to a copy/paste prompt.

  python serve_mount.py            regenerates the page, serves, opens browser
  python serve_mount.py --no-open  same, without opening a browser
"""
import json
import shutil
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE / "mount_editor.html"
PLACEMENTS = HERE / "mount_placements.json"
BACKUP = HERE / "mount_placements.backup.json"
HOST = "127.0.0.1"
PORTS = list(range(8780, 8791))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/mount_editor.html", "/index.html"):
            if not PAGE.exists():
                self._send(500, "mount_editor.html missing - run make_mount_editor.py")
                return
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path != "/api/mount":
            self._send(404, "not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - report any parse failure
            self._send(400, "bad json: " + str(exc))
            return
        placements = data.get("placements") if isinstance(data, dict) else None
        if not isinstance(placements, dict) or not placements:
            self._send(400, "refusing to save: missing 'placements' object")
            return
        payload = {"placements": placements}
        try:
            if PLACEMENTS.exists():
                shutil.copyfile(PLACEMENTS, BACKUP)
            tmp = PLACEMENTS.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, indent=1), encoding="utf-8")
            tmp.replace(PLACEMENTS)  # atomic swap
        except OSError as exc:
            self._send(500, "write failed: " + str(exc))
            return
        print(f"saved {PLACEMENTS.name} (backup: {BACKUP.name})")
        self._send(200, "ok")

    def log_message(self, *args):  # keep the console quiet
        pass


def serve(open_browser=True):
    rc = subprocess.run([sys.executable, str(HERE / "make_mount_editor.py")])
    if rc.returncode != 0:
        print("make_mount_editor.py failed; serving the previous page anyway")

    for port in PORTS:
        try:
            httpd = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:
            continue
    else:
        print("Could not bind a local port (8780-8790).")
        return 1

    url = f"http://{HOST}:{port}/mount_editor.html"
    print("Guybrush mount editor running at " + url)
    print("Save writes mount_placements.json in place.")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(serve(open_browser="--no-open" not in sys.argv))
