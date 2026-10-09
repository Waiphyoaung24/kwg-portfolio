"""Serve the observer's sanitized snapshot on the private Docker network."""
import json
import math
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SNAPSHOT = Path("/status/latest.json")
EXECUTION = Path("/status/execution.json")
TRADING_PAGE = Path("/app/trading.html")
TRADING_BOT_PAGE = Path("/app/trading-bot.html")


def sanitize_health(value):
    if value is None:
        return None  # Older observers have no explicit health evidence.
    if not isinstance(value, dict):
        raise ValueError("invalid health")
    if (value.get("terminal") not in ("unknown", "connected", "disconnected", "guard_failed")
            or value.get("quote") not in ("unknown", "fresh", "stale", "future", "missing", "invalid")):
        raise ValueError("invalid health state")
    result = {key: value[key] for key in ("terminal", "quote")}
    for key in ("sampled_at", "tick_time", "tick_time_msc", "quote_age_seconds",
                "history_bar_time", "history_count", "bid", "ask"):
        number = value.get(key)
        if number is not None and (type(number) not in (int, float) or not math.isfinite(number)
                                   or abs(number) > 1e15):
            raise ValueError("invalid health number")
        if key in ("history_bar_time", "history_count") and number is not None and (type(number) is not int or number < 0):
            raise ValueError("invalid history number")
        result[key] = number
    if ((result["bid"] is not None and not 0 < result["bid"] <= 1e6)
            or (result["ask"] is not None and not 0 < result["ask"] <= 1e6)
            or (result["bid"] is not None and result["ask"] is not None
                and result["ask"] < result["bid"])):
        # Keep the observer's invalid-quote reason and execution report available.
        result["bid"] = result["ask"] = None
    return result


def sanitize_execution(value, now: float):
    if not isinstance(value, dict) or value.get("mode") != "one-shot-demo":
        raise ValueError("invalid execution snapshot")
    status = value.get("status")
    if status not in ("disarmed", "armed", "submitting", "pending", "open", "closing",
                      "closed", "needs_attention"):
        raise ValueError("invalid execution state")
    updated_at = value.get("updated_at")
    if (type(updated_at) not in (int, float) or not math.isfinite(updated_at)
            or updated_at <= 0 or updated_at > now):
        raise ValueError("invalid execution heartbeat")
    side = value.get("side")
    if side is not None and side not in ("buy", "sell"):
        raise ValueError("invalid execution side")
    result = {"mode": "one-shot-demo", "status": status,
              "updated_at": updated_at, "side": side}
    for key in ("volume", "opened_at", "closed_at", "realized_net_usd", "entry_price", "sl", "tp"):
        number = value.get(key)
        if number is not None and (type(number) not in (int, float)
                                   or not math.isfinite(number) or abs(number) > 1e12):
            raise ValueError("invalid execution number")
        if key != "realized_net_usd" and number is not None and number <= 0:
            raise ValueError("invalid execution number")
        result[key] = number
    reason = value.get("close_reason")
    if reason is not None and (not isinstance(reason, str) or len(reason) > 160):
        raise ValueError("invalid execution reason")
    result["close_reason"] = reason
    if status == "closed" and (result["closed_at"] is None or result["realized_net_usd"] is None):
        raise ValueError("closed result lacks broker evidence")
    if status not in ("closed", "disarmed") and now - updated_at > 30:
        return None
    return result


def sanitize_pilot(value, now):
    if (not isinstance(value, dict) or value.get('strategy') not in ('gold-ema-v1-slope-3', 'gold-ema-v1-m1-slope-3', 'gold-ema-v1-m1-trend-3')
            or value.get('qualification') != 'unqualified'
            or value.get('status') not in ('standby', 'active', 'paused', 'needs_attention', 'expired')):
        raise ValueError('Invalid pilot state')
    result = {k: value[k] for k in ('strategy', 'qualification', 'status')}
    for k in ('updated_at', 'started_at', 'ends_at', 'realized_net_usd', 'floating_usd', 'completed_trades'):
        number = value.get(k)
        if number is not None and (type(number) not in (int, float) or not math.isfinite(number) or abs(number) > 1e12):
            raise ValueError('Invalid pilot number')
        result[k] = number
    if (result['updated_at'] is None or not 0 <= now - result['updated_at'] <= 30):
        return None
    if type(result['completed_trades']) is not int or result['completed_trades'] < 0:
        raise ValueError('Invalid pilot count')
    start, end = result['started_at'], result['ends_at']
    if ((value['status'] == 'standby' and (start is not None or end is not None))
            or (value['status'] != 'standby' and
                (start is None or end is None or not 0 < start <= now or not 0 < end - start <= 604800))):
        raise ValueError('Invalid pilot window')
    if not isinstance(value.get('reason'), str) or len(value['reason']) > 160:
        raise ValueError('Invalid pilot reason')
    result['reason'] = value['reason']
    trades = value.get('recent_trades')
    if not isinstance(trades, list) or len(trades) > 10:
        raise ValueError('Invalid pilot trades')
    result['recent_trades'] = []
    for trade in trades:
        if not isinstance(trade, dict) or trade.get('side') not in ('buy', 'sell'):
            raise ValueError('Invalid pilot trade')
        clean = {'side': trade['side']}
        for k in ('opened_at', 'closed_at', 'realized_net_usd'):
            number = trade.get(k)
            if type(number) not in (int, float) or not math.isfinite(number) or abs(number) > 1e12:
                raise ValueError('Invalid pilot trade number')
            clean[k] = number
        if not 0 < clean['opened_at'] <= clean['closed_at'] <= now:
            raise ValueError('Invalid pilot trade times')
        result['recent_trades'].append(clean)
    return result


def read_status(path: Path, now: float, *, execution_path: Path = EXECUTION) -> tuple[int, dict]:
    try:
        if path.stat().st_size > 16384:
            raise ValueError("oversized snapshot")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid snapshot")
        data["health"] = sanitize_health(data.get("health"))
        if (data["mode"] not in ("signal-only", "autonomous-demo") or data["symbol"] != "XAUUSD-VIP"
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
    payload = {key: data.get(key) for key in
               ("mode", "symbol", "status", "signal", "reason", "checked_at", "bar_time", "health")}
    if data['mode'] == 'autonomous-demo':
        try:
            payload['pilot'] = sanitize_pilot(data.get('pilot'), now)
            payload['execution'] = sanitize_execution(data.get('execution'), now)
            if payload['pilot'] is None and payload['status'] != 'offline':
                payload.update(status='blocked', signal='none', reason='Pilot heartbeat unavailable')
        except (ValueError, TypeError, KeyError):
            payload.update(pilot=None, execution=None, status='blocked', signal='none', reason='Pilot report invalid')
    elif execution_path.exists():
        try:
            if execution_path.stat().st_size > 2048:
                raise ValueError("oversized execution snapshot")
            payload["execution"] = sanitize_execution(
                json.loads(execution_path.read_text(encoding="utf-8")), now)
        except (OSError, ValueError, TypeError, UnicodeError):
            payload["execution"] = None
    return 200, payload


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path not in ("/control/preview", "/control/arm", "/control/pilot-pause"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 256 or self.headers.get("Content-Type") != "application/json":
                raise ValueError
            body = self.rfile.read(length)
            request = Request("http://desktop:8001/" + self.path.rsplit("/", 1)[-1], body,
                              {"Content-Type": "application/json",
                               "X-KWG-Control-Secret": self.headers.get("X-KWG-Control-Secret", "")},
                              method="POST")
            try:
                with urlopen(request, timeout=50) as response:
                    status, result = response.status, response.read(2048)
            except HTTPError as error:
                status, result = error.code, error.read(2048)
        except (ValueError, URLError, TimeoutError, OSError):
            status, result = 503, b'{"error":"Private demo control is unavailable."}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(result)))
        self.end_headers()
        self.wfile.write(result)

    def do_GET(self):
        if self.path in ("/vault/trading", "/vault/trading-bot"):
            try:
                body = (TRADING_BOT_PAGE if self.path == "/vault/trading-bot" else TRADING_PAGE).read_bytes()
            except OSError:
                self.send_error(503)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Robots-Tag", "noindex")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
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
