import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("export_gold", Path(__file__).with_name("export-gold.py"))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ExportTest(unittest.TestCase):
    def data(self):
        rows = [dict(time=(i + 1) * 900, open=100, high=102, low=99, close=101,
                     tick_volume=4, spread=20, real_volume=0) for i in range(251)]
        return rows, SimpleNamespace(point=.01, currency_profit="USD", password="never export", login=123)

    def test_frozen_unqualified_dataset_excludes_account_and_is_reproducible(self):
        rows, info = self.data()
        data = exporter.snapshot(rows, info, 10000, 300000, "test", {"quote": "stale"})
        self.assertTrue(data["coverage"]["partial_request"])
        self.assertEqual(data["qualification"]["status"], "unqualified")
        self.assertIsNone(data["cost_assumptions"]["commission"])
        self.assertNotIn("password", json.dumps(data))
        self.assertNotIn("login", json.dumps(data))
        with tempfile.TemporaryDirectory() as root:
            a, b = Path(root) / "a.json", Path(root) / "b.json"
            digest = exporter.save_snapshot(a, data)
            self.assertEqual(digest, exporter.save_snapshot(b, data))
            self.assertEqual(digest, hashlib.sha256(a.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                exporter.save_snapshot(a, data)

    def test_invalid_history_is_rejected_and_gaps_are_visible(self):
        rows, info = self.data()
        for key, value in (("close", float("nan")), ("time", 900), ("spread", -1), ("high", 98)):
            bad = [dict(row) for row in rows]
            bad[-1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                exporter.snapshot(bad, info, 251, 300000, "test", {})
        rows[-1]["time"] += 900
        result = exporter.snapshot(rows, info, 251, 1000, "test", {})
        self.assertEqual(result["coverage"]["gaps"][-1]["seconds"], 1800)
        self.assertGreater(result["coverage"]["bars_not_completed_by_host_clock"], 0)
        with self.assertRaises(ValueError):
            exporter.snapshot(rows[:250], info, 251, 300000, "test", {})


if __name__ == "__main__":
    unittest.main()
