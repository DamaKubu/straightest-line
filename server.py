#!/usr/bin/env python3
"""
Straightest-line leaderboard server (zero dependencies, Python 3 stdlib).

Run it on the computer you leave on:

    python server.py

It serves the web page (index.html) AND stores the shared leaderboard in
scores.json, so every phone that opens the page sees the same live ranking.

- Same WiFi as this computer:  phones open  http://<this-pc-ip>:8000
  (the address is printed when the server starts).
- Uploading from anywhere (people at home): put a tunnel in front of it, e.g.
      cloudflared tunnel --url http://localhost:8000
  and share the https URL it prints.

Scores are kept per paddler (best/lowest run wins). Data lives in scores.json.
"""

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))
SCORES = os.path.join(HERE, "scores.json")
LOCK = threading.Lock()


def load():
    try:
        with open(SCORES, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save(rows):
    with open(SCORES, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def upsert(rec):
    """Keep each paddler's best (lowest avg) run."""
    with LOCK:
        rows = load()
        name = str(rec.get("name", "")).strip()
        if not name:
            return rows
        full = rec.get("full") or []
        if not isinstance(full, list):
            full = []
        full = full[:400]
        clean = {
            "name": name,
            "avg": float(rec["avg"]),
            "rms": float(rec.get("rms", 0)),
            "max": float(rec.get("max", 0)),
            "coverage": float(rec.get("coverage", 0)),
            "stats": rec.get("stats") or {},
            "full": full,
        }
        if isinstance(rec.get("track"), list):   # legacy field, kept if sent
            clean["track"] = rec["track"][:400]
        i = next((k for k, r in enumerate(rows)
                  if r["name"].lower() == name.lower()), None)
        if i is None:
            rows.append(clean)
        elif clean["avg"] < rows[i]["avg"]:
            rows[i] = clean
        save(rows)
        return rows


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        path = self.path.split("?")[0].strip("/")
        if path in ("scores", "scores/"):
            return self._json(200, load())
        # serve static files (index.html by default)
        rel = path or "index.html"
        fp = os.path.join(HERE, rel)
        if os.path.isfile(fp) and os.path.commonpath([HERE, os.path.abspath(fp)]) == HERE:
            ctype = "text/html" if fp.endswith(".html") else "application/octet-stream"
            with open(fp, "rb") as f:
                return self._send(200, f.read(), ctype)
        return self._send(404, b"not found", "text/plain")

    def do_POST(self):
        path = self.path.split("?")[0].strip("/")
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except Exception:
            return self._json(400, {"error": "bad json"})
        if path == "scores":
            return self._json(200, upsert(data))
        if path == "delete":
            name = str(data.get("name", "")).strip().lower()
            with LOCK:
                rows = [r for r in load() if r["name"].lower() != name]
                save(rows)
            return self._json(200, rows)
        if path == "clear":
            with LOCK:
                save([])
            return self._json(200, [])
        return self._json(404, {"error": "unknown endpoint"})

    def log_message(self, *a):
        pass  # quiet


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = lan_ip()
    print("Straightest-line leaderboard server running.")
    print(f"  On this PC:        http://localhost:{PORT}")
    print(f"  Same-WiFi phones:  http://{ip}:{PORT}")
    print(f"  Data file:         {SCORES}")
    print("  Ctrl+C to stop.")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
