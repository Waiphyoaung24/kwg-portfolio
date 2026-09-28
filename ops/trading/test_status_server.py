import json
import tempfile
import unittest
from pathlib import Path

from status_server import read_status, sanitize_health


class StatusServerTest(unittest.TestCase):
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
