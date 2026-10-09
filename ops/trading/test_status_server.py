import json
import tempfile
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import urlopen
from urllib.error import HTTPError
from unittest.mock import patch

from status_server import Handler, read_status, sanitize_health, sanitize_pilot


class StatusServerTest(unittest.TestCase):
    def test_m1_strategy_survives_status_boundary(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'pilot-status.json').read_bytes())
        fixture['pilot']['strategy'] = 'gold-ema-v1-m1-slope-3'
        self.assertEqual(sanitize_pilot(fixture['pilot'], fixture['checked_at']), fixture['pilot'])
        fixture['pilot']['strategy'] = 'unknown'
        with self.assertRaises(ValueError):
            sanitize_pilot(fixture['pilot'], fixture['checked_at'])

    def test_pilot_contract_and_expiry_do_not_mix_manual_execution(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'pilot-status.json').read_bytes())
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'latest.json'
            path.write_text(json.dumps(fixture))
            status, value = read_status(path, fixture['checked_at'], execution_path=Path(root)/'missing')
            self.assertEqual(status, 200)
            self.assertEqual(value, fixture)
            _, stale = read_status(path, fixture['checked_at'] + 31, execution_path=Path(root)/'missing')
            self.assertIsNone(stale['pilot'])
            self.assertIsNone(stale['execution'])
            self.assertEqual(stale['status'], 'offline')

    def test_shared_status_contract(self):
        contract = json.loads((Path(__file__).parent / "fixtures" / "status-contract.json").read_text())
        for case in contract["cases"]:
            with self.subTest(case["name"]), tempfile.TemporaryDirectory() as root:
                observer = Path(root) / "latest.json"
                observer.write_text(json.dumps(case["observer"]))
                execution = Path(root) / "execution.json"
                if case["execution"] is not None:
                    execution.write_text(json.dumps(case["execution"]))
                status, payload = read_status(observer, contract["now"], execution_path=execution)
                self.assertEqual(status, 200)
                self.assertEqual(payload, case["payload"])

    def test_operations_page_uses_fixed_file_and_rejects_unknown_path(self):
        with tempfile.TemporaryDirectory() as root:
            page = Path(root) / "trading-bot.html"
            page.write_text("<h1>Gold operations</h1>")
            with patch("status_server.TRADING_BOT_PAGE", page, create=True):
                server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    origin = f"http://127.0.0.1:{server.server_port}"
                    with urlopen(origin + "/vault/trading-bot", timeout=2) as response:
                        self.assertEqual(response.read(), b"<h1>Gold operations</h1>")
                        self.assertEqual(response.headers["Cache-Control"], "no-store")
                    with self.assertRaises(HTTPError) as error:
                        urlopen(origin + "/vault/trading-bot/unknown", timeout=2)
                    self.assertEqual(error.exception.code, 404)
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join()

    def test_execution_snapshot_is_allowlisted_and_expires_except_closed(self):
        with tempfile.TemporaryDirectory() as root:
            observer = Path(root) / "latest.json"
            execution = Path(root) / "execution.json"
            observer.write_text(json.dumps({"mode": "signal-only", "symbol": "XAUUSD-VIP",
                "status": "blocked", "signal": "none", "reason": "Algo Trading enabled",
                "checked_at": 100, "bar_time": 90}))
            entry = {"mode": "one-shot-demo", "status": "open", "updated_at": 100,
                     "side": "buy", "volume": .01, "opened_at": 99, "closed_at": None,
                     "close_reason": None, "realized_net_usd": None,
                     "login": 123, "ticket": 456, "password": "secret"}
            execution.write_text(json.dumps(entry))
            code, payload = read_status(observer, 105, execution_path=execution)
            self.assertEqual(code, 200)
            self.assertEqual(payload["execution"]["status"], "open")
            self.assertNotIn("login", payload["execution"])
            self.assertNotIn("ticket", payload["execution"])
            self.assertNotIn("password", payload["execution"])
            execution.write_text(json.dumps(entry | {"status": "pending", "entry_price": 99,
                                                     "sl": 95, "tp": 105}))
            pending = read_status(observer, 105, execution_path=execution)[1]["execution"]
            self.assertEqual((pending["status"], pending["entry_price"], pending["sl"], pending["tp"]),
                             ("pending", 99, 95, 105))
            self.assertIsNone(read_status(observer, 131, execution_path=execution)[1]["execution"])
            execution.write_text(json.dumps(entry | {"status": "closed", "closed_at": 101,
                                                    "realized_net_usd": .8}))
            closed = read_status(observer, 500, execution_path=execution)[1]["execution"]
            self.assertEqual((closed["status"], closed["closed_at"], closed["realized_net_usd"]),
                             ("closed", 101, .8))
            execution.write_text(json.dumps(entry | {"status": "filled", "ticket": 456}))
            self.assertIsNone(read_status(observer, 105, execution_path=execution)[1]["execution"])

    def test_health_boundary_rejects_invalid_numbers_and_drops_secrets(self):
        health = dict(terminal="connected", quote="stale", sampled_at=100,
                      quote_age_seconds=99, login=123, password="must not leave origin")
        cleaned = sanitize_health(health)
        self.assertNotIn("login", cleaned)
        self.assertNotIn("password", cleaned)
        self.assertEqual(cleaned["quote"], "stale")
        prices = sanitize_health(health | {"bid": 4100.25, "ask": 4100.5})
        self.assertEqual((prices["bid"], prices["ask"]), (4100.25, 4100.5))
        for prices in ({"bid": 0}, {"ask": -1}, {"bid": 10, "ask": 9}):
            cleaned = sanitize_health(health | prices | {"quote": "invalid"})
            self.assertEqual((cleaned["bid"], cleaned["ask"], cleaned["quote"]), (None, None, "invalid"))
        for prices in ({"bid": True}, {"ask": float("nan")}):
            with self.assertRaises(ValueError):
                sanitize_health(health | prices)
        for value in (float("nan"), float("inf"), "99", True):
            with self.assertRaises(ValueError):
                sanitize_health(health | {"quote_age_seconds": value})

    def test_fresh_stale_and_missing_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "latest.json"
            self.assertEqual(read_status(path, 100)[0], 503)
            path.write_text(json.dumps({"mode": "signal-only", "symbol": "XAUUSD-VIP",
                                        "status": "observed", "signal": "long", "reason": "Crossover",
                                        "checked_at": 100, "bar_time": 90, "login": 123}))
            status, payload = read_status(path, 105)
            self.assertEqual((status, payload["signal"]), (200, "long"))
            self.assertNotIn("login", payload)
            self.assertEqual(read_status(path, 131)[1]["status"], "offline")


if __name__ == "__main__":
    unittest.main()
