#!/usr/bin/env python3
"""Serve reviewer.html from a local HTTP server so its "Export mapping.json"
button can write mapping.json in place (keeping the previous file as
mapping.backup.json).

Opened directly as a file:// page a browser cannot write to disk, so
ReviewSprites.bat launches this instead. Ctrl+C in the console stops it.
"""
import json
import shutil
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEWER = HERE / "reviewer.html"
MAPPING = HERE / "mapping.json"
BACKUP = HERE / "mapping.backup.json"
SUGGESTIONS = HERE / "suggestions.json"
HOST = "127.0.0.1"
PORTS = list(range(8765, 8776))


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
        if self.path in ("/", "/reviewer.html", "/index.html"):
            if not REVIEWER.exists():
                self._send(500, "reviewer.html is missing - run make_reviewer.py first.")
                return
            self._send(200, REVIEWER.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, "not found")

    def do_POST(self):
        if self.path == "/api/suggestions":
            # The page persists approve/dismiss status and comments here, so
            # they survive a reload and the agent can read them back.
            try:
                length = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                self._send(400, "bad json: " + str(exc))
                return
            if not isinstance(data, dict) or not isinstance(data.get("suggestions"), list):
                self._send(400, "refusing to save: missing 'suggestions' list")
                return
            try:
                tmp = SUGGESTIONS.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
                tmp.replace(SUGGESTIONS)  # atomic swap
            except OSError as exc:
                self._send(500, "write failed: " + str(exc))
                return
            print("saved suggestions.json")
            self._send(200, "ok")
            return
        if self.path != "/api/save":
            self._send(404, "not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - report any parse failure to the page
            self._send(400, "bad json: " + str(exc))
            return
        if not isinstance(data, dict) or not isinstance(data.get("animations"), dict):
            self._send(400, "refusing to save: missing 'animations' object")
            return

        try:
            if MAPPING.exists():
                shutil.copyfile(MAPPING, BACKUP)
            tmp = MAPPING.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
            tmp.replace(MAPPING)  # atomic swap
        except OSError as exc:
            self._send(500, "write failed: " + str(exc))
            return
        print(f"saved {MAPPING.name} (backup: {BACKUP.name})")
        self._send(200, "ok")

    def log_message(self, *args):  # keep the console quiet
        pass


def serve(open_browser=True):
    for port in PORTS:
        try:
            httpd = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:
            continue
    else:
        print("Could not bind a local port (8765-8775).")
        return 1

    url = f"http://{HOST}:{port}/reviewer.html"
    print("Guybrush sprite mapper running at " + url)
    print("Export now saves mapping.json in place (backup: mapping.backup.json).")
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
