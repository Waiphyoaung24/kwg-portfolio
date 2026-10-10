"""The web bridge must never arm without a fresh, reviewed preview."""
import json
import os
import shlex
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import control_server as control


class ControlTest(unittest.TestCase):
    def test_btc_pause_is_scoped_and_unknown_symbols_are_rejected(self):
        with patch.dict(os.environ, {'MT5_RUN_MODE': 'pilot', 'MT5_PILOT_SYMBOLS': 'XAUUSD-VIP,BTCUSD'}):
            self.assertEqual(control.run_action('pilot-pause', {'symbol': 'BTCUSD'})[0], 202)
            self.assertTrue((control.STATE.parent/'btc-pilot.pause').exists())
            self.assertFalse((control.STATE.parent/'gold-pilot.pause').exists())
            self.assertEqual(control.run_action('pilot-pause', {'symbol': '../gold'})[0], 409)

    def test_pilot_pause_persists_and_manual_entry_is_refused(self):
        with patch.dict(os.environ, {'MT5_RUN_MODE': 'pilot'}), \
                patch.object(control.subprocess, 'Popen') as launch:
            self.assertEqual(control.run_action('preview', {})[0], 409)
            self.assertEqual(control.run_action('arm', {})[0], 409)
            self.assertEqual(control.run_action('pilot-pause', {})[0], 202)
            self.assertTrue((control.STATE.parent/'gold-pilot.pause').exists())
            self.assertEqual(control.run_action('pilot-pause', {'enable': True})[0], 409)
            launch.assert_not_called()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        state = patch.object(control, "STATE", Path(self.temp.name) / "gold-one-shot.sqlite3")
        state.start()
        self.addCleanup(state.stop)
        control.pending = None
        control.runner = None

    def test_unresolved_journal_blocks_preview_and_arm(self):
        db = sqlite3.connect(control.STATE)
        try:
            db.execute("CREATE TABLE attempts (state TEXT)")
            db.execute("INSERT INTO attempts VALUES ('needs_attention')")
            db.commit()
        finally:
            db.close()
        with patch.object(control.subprocess, "run") as preview, patch.object(control.subprocess, "Popen") as arm:
            self.assertEqual(control.run_action("preview", {"side": "buy"})[0], 409)
            self.assertEqual(control.run_action("arm", {"token": "anything"})[0], 409)
        preview.assert_not_called()
        arm.assert_not_called()

    def test_preview_token_is_single_use_and_launches_only_reviewed_side(self):
        preview = {"mode": "private-demo-preview", "side": "sell", "symbol": "XAUUSD-VIP",
                   "order_sent": False, "volume": .01, "sl": 2, "tp": 1}
        with patch.object(control.subprocess, "run", return_value=SimpleNamespace(stdout=json.dumps(preview))) as no_order, \
             patch.object(control.subprocess, "Popen", return_value=Mock(poll=lambda: None)) as arm:
            self.assertEqual(control.run_action("arm", {"token": "missing"})[0], 409)
            levels = {"entry": 100, "sl": 102, "tp": 98}
            status, result = control.run_action("preview", {"side": "sell", **levels})
            self.assertEqual(status, 200)
            token = result["token"]
            self.assertIn("--entry", no_order.call_args.args[0])
            self.assertEqual(control.run_action("arm", {"token": token})[0], 202)
            launch = arm.call_args.args[0]
            self.assertEqual(launch[:4], ["script", "-q", "-e", "-c"])
            self.assertEqual(launch[5], "/dev/null")
            self.assertEqual(shlex.split(launch[4]), control.COMMAND +
                             ["arm", "--side", "sell", "--state", control.WINDOWS_STATE,
                              "--enable-demo-execution", "--entry", "100", "--sl", "102", "--tp", "98"])
            self.assertEqual(control.run_action("arm", {"token": token})[0], 409)
            self.assertEqual(arm.call_count, 1)

    def test_expired_preview_does_not_launch(self):
        control.pending = ("token", "buy", {"entry": 99, "sl": 95, "tp": 105}, 10)
        with patch.object(control.subprocess, "Popen") as arm:
            self.assertEqual(control.run_action("arm", {"token": "token"})[0], 409)
            arm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
