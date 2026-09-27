"""Serve the observer's sanitized snapshot on the private Docker network."""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SNAPSHOT = Path("/status/latest.json")


def read_status(path: Path, now: float) -> tuple[int, dict]:
    try:
        if path.stat().st_size > 4096:
            raise ValueError("oversized snapshot")
        data = json.loads(path.read_text(encoding="utf-8"))
        if (data["mode"] != "signal-only" or data["symbol"] != "XAUUSD-VIP"
                or data["status"] not in ("baseline", "observed", "duplicate", "blocked")
                or data["signal"] not in ("long", "short", "none")
                or type(data["checked_at"]) is not int
                or (data.get("bar_time") is not None and type(data["bar_time"]) is not int)
                or not isinstance(data.get("reason"), str)):
            raise ValueError("invalid snapshot")
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        return 503, {"mode": "signal-only", "symbol": "XAUUSD-VIP",
                     "status": "offline", "signal": "none",
                     "reason": "Observer status unavailable", "checked_at": None,
                     "bar_time": None}
    if not 0 <= now - data["checked_at"] <= 30:
        data.update(status="offline", signal="none", reason="Observer heartbeat missing")
    if data["status"] in ("offline", "blocked"):
        data["signal"] = "none"
    return 200, {key: data.get(key) for key in
                 ("mode", "symbol", "status", "signal", "reason", "checked_at", "bar_time")}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/status":
            self.send_error(404)
            return
        status, payload = read_status(SNAPSHOT, time.time())
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
