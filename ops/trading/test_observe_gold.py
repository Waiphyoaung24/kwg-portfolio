import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from gold_signal import evaluate

spec = importlib.util.spec_from_file_location("observe_gold", Path(__file__).with_name("observe-gold.py"))
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


def history(end=250):
    return [dict(time=(i + 1) * 900, open=100, high=101, low=99, close=100) for i in range(end - 250, end)]


def fake_sdk(end=250):
    sdk = Mock(TIMEFRAME_M15=15)
    sdk.account_info.return_value = SimpleNamespace(trade_mode=0, login=123, server="VTMarkets-Demo")
    sdk.terminal_info.return_value = SimpleNamespace(connected=True, trade_allowed=False)
    sdk.symbol_select.return_value = True
    sdk.symbol_info_tick.return_value = SimpleNamespace(bid=100, ask=100.1, time=(end + 1) * 900, time_msc=0)
    sdk.copy_rates_from_pos.return_value = history(end)
    sdk.order_send.side_effect = AssertionError("orders forbidden")
    return sdk


class ObserverTest(unittest.TestCase):
    def test_baseline_duplicate_next_missed_and_restart(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.sqlite3"
            db = observer.open_state(path, 123)
            self.addCleanup(db.close)
            sdk = fake_sdk()
            first = observer.poll_once(sdk, db, 123, 251 * 900, bootstrap=True)
            self.assertEqual((first["status"], first["mode"]), ("baseline", "signal-only"))
            self.assertNotIn("login", json.dumps(first))
            self.assertEqual(observer.poll_once(sdk, db, 123, 251 * 900, bootstrap=False)["status"], "duplicate")
            sdk = fake_sdk(251)
            self.assertEqual(observer.poll_once(sdk, db, 123, 252 * 900, bootstrap=False)["status"], "observed")
            db.close()
            db = observer.open_state(path, 123)
            self.assertEqual(observer.poll_once(sdk, db, 123, 252 * 900, bootstrap=True)["status"], "duplicate")
            sdk = fake_sdk(254)
            self.assertEqual(observer.poll_once(sdk, db, 123, 255 * 900, bootstrap=False)["status"], "baseline")
            self.assertEqual(db.execute("SELECT count(*) FROM observations").fetchone()[0], 3)
            sdk.order_send.assert_not_called()
            db.close()

    def test_bad_data_does_not_write_and_identity_fails(self):
        with tempfile.TemporaryDirectory() as root:
            db = observer.open_state(Path(root) / "state.sqlite3", 123)
            sdk = fake_sdk()
            sdk.symbol_info_tick.return_value.time -= 100
            self.assertEqual(observer.poll_once(sdk, db, 123, 251 * 900, True)["status"], "blocked")
            self.assertEqual(db.execute("SELECT count(*) FROM observations").fetchone()[0], 0)
            sdk = fake_sdk()
            sdk.copy_rates_from_pos.return_value[-1]["high"] = 98
            self.assertEqual(observer.poll_once(sdk, db, 123, 251 * 900, True)["status"], "blocked")
            sdk.account_info.return_value.trade_mode = 2
            with self.assertRaises(ValueError):
                observer.poll_once(sdk, db, 123, 251 * 900, True)
            db.close()

    def test_state_mismatch_and_corruption_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "state.sqlite3"
            observer.open_state(path, 123).close()
            with self.assertRaises(ValueError):
                observer.open_state(path, 456)
            path.write_bytes(b"not sqlite")
            with self.assertRaises(sqlite3.DatabaseError):
                observer.open_state(path, 123)


if __name__ == "__main__":
    unittest.main()
