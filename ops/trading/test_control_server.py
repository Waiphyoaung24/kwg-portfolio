"""The web bridge must never arm without a fresh, reviewed preview."""
import json
import os
import shlex
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import control_server as control
import jev_m5


class ControlTest(unittest.TestCase):
    def test_jev_receipt_requires_pilot_and_stores_once(self):
        receipt = dict(bar_time=600, input_sha256='a' * 64, model='jev-1.13.0',
                       question_sha256=jev_m5.QUESTION_SHA256, status='timeout',
                       choice=None, confidence=None, probabilities=None, completed_at=1030)
        with patch.dict(os.environ, {'MT5_RUN_MODE': 'observer'}):
            self.assertEqual(control.run_action('jev-receipt', receipt)[0], 409)
        with patch.dict(os.environ, {'MT5_RUN_MODE': 'pilot'}), \
                patch.object(control, 'RECEIPTS', self.folder / 'jev-m5-receipts.sqlite3'):
            self.assertEqual(control.run_action('jev-receipt', receipt), (202, {'status': 'stored'}))
            self.assertEqual(control.run_action('jev-receipt', receipt), (200, {'status': 'duplicate'}))
            self.assertEqual(control.run_action('jev-receipt', {**receipt, 'model': 'x'})[0], 400)

    def test_pause_survives_missing_jev_module_and_receipt_is_unavailable(self):
        with patch.dict(os.environ, {'MT5_RUN_MODE': 'pilot'}), patch.dict(sys.modules, {'jev_m5': None}), \
                patch.object(control, 'RECEIPTS', self.folder / 'jev-m5-receipts.sqlite3'):
            self.assertEqual(control.run_action('pilot-pause', {})[0], 202)
            self.assertEqual(control.run_action('jev-receipt', {}),
                             (503, {'error': 'Jev receipts are unavailable.'}))
        self.assertFalse((self.folder / 'jev-m5-receipts.sqlite3').exists())

    def test_jev_receipt_http_requires_secret_and_object_body(self):
        receipts = self.folder / 'jev-m5-receipts.sqlite3'
        server = ThreadingHTTPServer(('127.0.0.1', 0), control.Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with patch.object(control, 'SECRET', 's' * 32), patch.object(control, 'RECEIPTS', receipts), \
                    patch.dict(os.environ, {'MT5_RUN_MODE': 'pilot'}):
                def post(body, secret=None):
                    headers = {'Content-Type': 'application/json'}
                    if secret is not None:
                        headers['X-KWG-Control-Secret'] = secret
                    request = Request(f'http://127.0.0.1:{server.server_port}/jev-receipt',
                                      json.dumps(body).encode(), method='POST', headers=headers)
                    try:
                        with urlopen(request, timeout=2) as response:
                            return response.status
                    except HTTPError as error:
                        return error.code
                receipt = dict(bar_time=600, input_sha256='a' * 64, model='jev-1.13.0',
                               question_sha256=jev_m5.QUESTION_SHA256, status='timeout',
                               choice=None, confidence=None, probabilities=None, completed_at=1030)
                self.assertEqual(post(receipt), 403)
                self.assertEqual(post(receipt, 'w' * 32), 403)
                self.assertFalse(receipts.exists())
                self.assertEqual(post([receipt], 's' * 32), 400)
                self.assertFalse(receipts.exists())
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_jev_receipt_body_limit_is_scoped_to_its_path(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), control.Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with patch.object(control, 'SECRET', 's' * 32), \
                    patch.object(control, 'run_action', return_value=(200, {'status': 'duplicate'})) as action:
                def post(path, size):
                    body = json.dumps({'pad': 'x' * (size - 11)}).encode()
                    self.assertEqual(len(body), size)
                    request = Request(f'http://127.0.0.1:{server.server_port}{path}', body, method='POST',
                                      headers={'Content-Type': 'application/json', 'X-KWG-Control-Secret': 's' * 32})
                    try:
                        with urlopen(request, timeout=2) as response:
                            return response.status
                    except HTTPError as error:
                        return error.code
                self.assertEqual(post('/jev-receipt', 1024), 200)
                self.assertEqual(post('/jev-receipt', 1025), 400)
                self.assertEqual(post('/pilot-pause', 257), 400)
                self.assertEqual(action.call_count, 1)
        finally:
            server.shutdown(); server.server_close(); thread.join()

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
        self.folder = Path(self.temp.name)
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
