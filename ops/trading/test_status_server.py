import json
import tempfile
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

from status_server import Handler, read_status, sanitize_health, sanitize_pilot


class StatusServerTest(unittest.TestCase):
    def test_jev_m5_feed_refuses_stale_failed_or_oversized_exports(self):
        with tempfile.TemporaryDirectory() as root, patch('status_server.time.time', return_value=1000):
            path = Path(root) / 'jev-m5.json'
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                with patch('status_server.SNAPSHOT', Path(root) / 'latest.json'):
                    url = f'http://127.0.0.1:{server.server_port}/jev-m5'
                    for value in ({'status': 'ready', 'checked_at': 984}, {'status': 'blocked', 'checked_at': 1000},
                                  {'status': 'ready', 'checked_at': 1000, 'pad': 'x' * 100000}):
                        path.write_text(json.dumps(value))
                        with self.assertRaises(HTTPError) as error:
                            urlopen(url, timeout=2)
                        self.assertEqual(error.exception.code, 503)
                    path.write_text(json.dumps({'status': 'ready', 'checked_at': 985}))
                    with urlopen(url, timeout=2) as response:
                        self.assertEqual(response.read(), path.read_bytes())
                        self.assertEqual(response.headers['Cache-Control'], 'no-store')
            finally:
                server.shutdown(); server.server_close(); thread.join()

    def test_jev_m5_receipt_is_forwarded_with_secret_and_its_own_body_limit(self):
        class Reply:
            status = 202
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b'{"status":"stored"}'
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with patch('status_server.urlopen', return_value=Reply()) as forward:
                def post(path, size):
                    body = json.dumps({'pad': 'x' * (size - 11)}).encode()
                    request = Request(f'http://127.0.0.1:{server.server_port}{path}', body, method='POST',
                                      headers={'Content-Type': 'application/json', 'X-KWG-Control-Secret': 'secret'})
                    try:
                        with urlopen(request, timeout=2) as response:
                            return response.status, body
                    except HTTPError as error:
                        return error.code, body
                status, body = post('/control/jev-receipt', 1024)
                self.assertEqual(status, 202)
                sent = forward.call_args.args[0]
                self.assertEqual(sent.full_url, 'http://desktop:8001/jev-receipt')
                self.assertEqual(sent.data, body)
                self.assertEqual(sent.get_header('X-kwg-control-secret'), 'secret')
                self.assertEqual(post('/control/jev-receipt', 1025)[0], 503)
                self.assertEqual(post('/control/pilot-pause', 257)[0], 503)
                self.assertEqual(forward.call_count, 1)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_scorecard_route_refuses_stale_or_failed_exports(self):
        with tempfile.TemporaryDirectory() as root, patch('status_server.time.time', return_value=1000):
            path = Path(root) / 'jev-scorecard.json'
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                with patch('status_server.SNAPSHOT', Path(root) / 'latest.json'):
                    url = f'http://127.0.0.1:{server.server_port}/jev-scorecard'
                    for value in ({'status': 'ready', 'generated_at': 879}, {'status': 'unavailable', 'generated_at': 1000}):
                        path.write_text(json.dumps(value))
                        with self.assertRaises(HTTPError) as error:
                            urlopen(url, timeout=2)
                        self.assertEqual(error.exception.code, 503)
                    path.write_text(json.dumps({'status': 'ready', 'generated_at': 1000}))
                    with urlopen(url, timeout=2) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers['Cache-Control'], 'no-store')
            finally:
                server.shutdown(); server.server_close(); thread.join()

    def test_continuous_policy_requires_explicit_consistent_window(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'pilot-status.json').read_bytes())
        value = dict(fixture['pilot'], run_policy='continuous', ends_at=None)
        self.assertEqual(sanitize_pilot(value, fixture['checked_at']), value)
        for changes in ({'run_policy': None}, {'run_policy': 'forever'},
                        {'ends_at': fixture['checked_at'] + 60}, {'status': 'expired'}, {'status': 'standby'}):
            with self.assertRaises(ValueError):
                sanitize_pilot(dict(value, **changes), fixture['checked_at'])

    def test_btc_status_never_falls_back_to_gold_snapshot_or_manual_execution(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'pilot-status.json').read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'btc.json'
            path.write_text(json.dumps(fixture))
            self.assertEqual(read_status(path, fixture['checked_at'], symbol='BTCUSD')[0], 503)
            fixture['symbol'] = 'BTCUSD'
            fixture['pilot']['strategy'] = 'btc-ema-v1-m15-trend-3'
            path.write_text(json.dumps(fixture))
            code, report = read_status(path, fixture['checked_at'], symbol='BTCUSD')
            self.assertEqual(code, 200)
            self.assertEqual(report['pilot']['strategy'], 'btc-ema-v1-m15-trend-3')
            self.assertEqual(read_status(path, fixture['checked_at'])[0], 503)
            fixture['pilot']['strategy'] = 'btc-ema-v1-m1-scalp-60'
            path.write_text(json.dumps(fixture))
            self.assertEqual(read_status(path, fixture['checked_at'], symbol='BTCUSD')[1]['pilot']['strategy'],
                             'btc-ema-v1-m1-scalp-60')
            fixture['pilot']['strategy'] = 'gold-ema-v1-m1-trend-3'
            path.write_text(json.dumps(fixture))
            self.assertIsNone(read_status(path, fixture['checked_at'], symbol='BTCUSD')[1]['pilot'])

    def test_m1_strategy_survives_status_boundary(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'pilot-status.json').read_bytes())
        fixture['pilot']['strategy'] = 'gold-ema-v1-m1-slope-3'
        self.assertEqual(sanitize_pilot(fixture['pilot'], fixture['checked_at']), fixture['pilot'])
        fixture['pilot']['strategy'] = 'gold-ema-v1-m1-trend-3'
        self.assertEqual(sanitize_pilot(fixture['pilot'], fixture['checked_at']), fixture['pilot'])
        fixture['pilot']['strategy'] = 'unknown'
        with self.assertRaises(ValueError):
            sanitize_pilot(fixture['pilot'], fixture['checked_at'])

    def test_m5_jev_strategy_survives_status_boundary_with_known_mode_only(self):
        fixture = json.loads((Path(__file__).parent / 'fixtures' / 'pilot-status.json').read_bytes())
        now = fixture['checked_at']
        for mode in ('shadow', 'veto'):
            value = dict(fixture['pilot'], strategy='gold-ema-v1-m5-trend-jev', jev_mode=mode)
            self.assertEqual(sanitize_pilot(value, now), value)
        for mode in ('live', None, 1):
            value = dict(fixture['pilot'], strategy='gold-ema-v1-m5-trend-jev', jev_mode=mode)
            self.assertNotIn('jev_mode', sanitize_pilot(value, now))
        self.assertNotIn('jev_mode', sanitize_pilot(dict(fixture['pilot'], jev_mode='veto'), now))
        with self.assertRaises(ValueError):
            sanitize_pilot(dict(fixture['pilot'], strategy='gold-ema-v1-m5-trend-jev'), now, 'BTCUSD')

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
