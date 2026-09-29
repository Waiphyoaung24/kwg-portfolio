"""Private, one-at-a-time bridge from a reviewed preview to the demo CLI."""
import json
import os
import secrets
import sqlite3
import subprocess
import threading
import time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATE = Path("/home/mt5/.wine/drive_c/users/mt5/gold-one-shot.sqlite3")
WINDOWS_STATE = r"C:\users\mt5\gold-one-shot.sqlite3"
COMMAND = ["wine", "/opt/python/python.exe", "/opt/trading/demo_one_shot.py"]
SECRET = os.environ.get("TRADING_CONTROL_SECRET", "")
LOCK = threading.Lock()
pending = None
runner = None


def available():
    if not STATE.exists():
        return True
    with closing(sqlite3.connect(f"file:{STATE}?mode=ro", uri=True)) as db:
        row = db.execute("SELECT state FROM attempts ORDER BY rowid DESC LIMIT 1").fetchone()
    return row is None or row[0] in ("closed", "disarmed")


def run_action(action, payload):
    global pending, runner
    if runner is not None and runner.poll() is None:
        return 409, {"error": "A demo attempt is already running."}
    if not available():
        return 409, {"error": "Resolve the current demo attempt before starting another."}
    if action == "preview":
        side = payload.get("side")
        if side not in ("buy", "sell") or set(payload) != {"side"}:
            return 400, {"error": "Choose buy or sell."}
        pending = None
        try:
            result = subprocess.run(COMMAND + ["preview", "--side", side, "--state", WINDOWS_STATE],
                                    capture_output=True, text=True, timeout=45, check=True)
            preview = json.loads(result.stdout.strip().splitlines()[-1])
            if (preview.get("mode") != "private-demo-preview" or preview.get("side") != side
                    or preview.get("symbol") != "XAUUSD-VIP" or preview.get("order_sent") is not False):
                raise ValueError("Invalid preview")
        except (subprocess.SubprocessError, IndexError, json.JSONDecodeError, ValueError):
            return 409, {"error": "Preview failed. Check the demo connection, quote and Algo Trading setting in MT5."}
        token = secrets.token_urlsafe(24)
        pending = (token, side, time.time() + 600)
        return 200, {"preview": preview, "token": token}
    if action == "arm":
        token = payload.get("token")
        if set(payload) != {"token"} or not isinstance(token, str):
            return 400, {"error": "Prepare and review a demo preview first."}
        if pending is None or not secrets.compare_digest(token, pending[0]) or time.time() > pending[2]:
            return 409, {"error": "Preview expired. Prepare a new preview."}
        side = pending[1]
        pending = None
        log = (STATE.parent / "gold-one-shot-control.log").open("ab")
        try:
            runner = subprocess.Popen(COMMAND + ["arm", "--side", side, "--state", WINDOWS_STATE,
                                                 "--enable-demo-execution"],
                                      stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        except OSError:
            return 503, {"error": "Could not start the private demo runner."}
        finally:
            log.close()
        return 202, {"status": "starting"}
    return 404, {"error": "Unknown action."}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ("/preview", "/arm"):
            self.send_error(404)
            return
        if not SECRET or not secrets.compare_digest(self.headers.get("X-KWG-Control-Secret", ""), SECRET):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 256 or self.headers.get("Content-Type") != "application/json":
                raise ValueError
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            status, body = 400, {"error": "Invalid request."}
        else:
            if not LOCK.acquire(blocking=False):
                status, body = 409, {"error": "A demo check is already running."}
            else:
                try:
                    status, body = run_action(self.path[1:], payload)
                except (OSError, sqlite3.Error):
                    status, body = 503, {"error": "Private demo state is unavailable."}
                finally:
                    LOCK.release()
        data = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    os.umask(0o077)
    if not SECRET or len(SECRET) < 32:
        raise SystemExit("TRADING_CONTROL_SECRET must be at least 32 characters")
    ThreadingHTTPServer(("0.0.0.0", 8001), Handler).serve_forever()
