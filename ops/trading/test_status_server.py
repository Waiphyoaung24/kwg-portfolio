import json
import tempfile
import unittest
from pathlib import Path

from status_server import read_status


class StatusServerTest(unittest.TestCase):
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
