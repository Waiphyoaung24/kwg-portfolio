"""Dual M5 migration preserves risk/history and refuses unsafe activation."""
import json
from pathlib import Path
import runpy
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import hashlib

import demo_pilot as pilot
from test_switch_m5 import NOW, PREVIOUS, record, dump

module = runpy.run_path(str(Path(__file__).with_name('upgrade-dual-m5.py')))


class UpgradeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.gold = pilot.open_state(self.home / 'gold-pilot.sqlite3', 123)
        self.btc = pilot.open_state(self.home / 'btc-pilot.sqlite3', 123, pilot.BTC)
        for db, strategy in ((self.gold, pilot.M5_JEV_STRATEGY), (self.btc, pilot.BTC_SCALP_STRATEGY)):
            with db:
                db.execute('INSERT INTO pilot VALUES (1, ?)', (json.dumps(record(strategy=strategy, jev_mode='veto')),))
                db.execute("INSERT INTO attempts (id, side, armed_at, expires_at, state, phase, realized_net_usd) "
                           "VALUES ('old', 'buy', ?, ?, 'closed', 'close', 1.25)", (NOW-900, NOW))
        with self.gold:
            self.gold.execute('CREATE TABLE account_limits (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
            self.gold.execute('INSERT INTO account_limits VALUES (1, ?)', (json.dumps(record(strategy=None)),))
        self.reviewed = pilot.identity()

    def tearDown(self):
        self.gold.close()
        self.btc.close()
        self.temp.cleanup()

    def upgrade(self, **kwargs):
        return module['switch'](self.gold, self.btc, self.home, NOW, self.reviewed, PREVIOUS,
                                self.home / ('report-backup' if kwargs.get('reporting') else 'backup'), **kwargs)

    def test_preserves_risk_history_gold_and_backs_up_owner_pause(self):
        gold = pilot.state(self.gold)
        pilot.save(self.btc, {**pilot.state(self.btc), 'pause': 'Paused by owner'})
        btc = pilot.state(self.btc)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        (self.home / 'btc-pilot.pause').write_text('owner requested')
        before = [dump(db, skip_pilot=True) for db in (self.gold, self.btc)]
        with patch.object(module['shutil'], 'copy2', side_effect=RuntimeError('Wine CopyFile2 unavailable')):
            self.upgrade(owner_approved=True)
        self.assertEqual(pilot.state(self.gold), {**gold, 'code': self.reviewed})
        updated = pilot.state(self.btc)
        for k, v in btc.items():
            if k not in ('code', 'strategy', 'last_bar', 'pause', 'reason'):
                self.assertEqual(updated[k], v)
        self.assertEqual(updated['strategy'], module['BTC_M5'])
        self.assertIsNone(updated['last_bar'])
        self.assertIsNone(updated['pause'])
        self.assertEqual(json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0]), {**risk, 'code': self.reviewed})
        self.assertEqual(dump(self.btc, skip_pilot=True), before[1])
        self.assertEqual((self.home / 'backup/btc-pilot.pause').read_text(), 'owner requested')
        self.assertFalse((self.home / 'btc-pilot.pause').exists())
        for name in ('gold', 'btc'):
            with sqlite3.connect(self.home / 'backup' / (name + '.sqlite3')) as db:
                self.assertEqual(pilot.state(db)['code'], PREVIOUS)
                self.assertEqual(db.execute('SELECT realized_net_usd FROM attempts').fetchone()[0], 1.25)

    def test_refuses_wrong_hash_pause_pending_or_unresolved_without_mutation(self):
        cases = [('gold', {'code': 'b'*64}), ('btc', {'code': 'b'*64}),
                 ('gold', {'pause': 'loss'}), ('btc', {'pause': 'loss'}),
                 ('btc', {'pause': 'Paused by owner'}), ('gold', {'pending_entry': {'bar_time': 12}})]
        for name, changes in cases:
            with self.subTest(name=name, changes=changes):
                db = getattr(self, name)
                old = pilot.state(db)
                pilot.save(db, {**old, **changes})
                snapshots = [dump(d) for d in (self.gold, self.btc)]
                with self.assertRaises(ValueError):
                    self.upgrade()
                self.assertEqual([dump(d) for d in (self.gold, self.btc)], snapshots)
                pilot.save(db, old)
        for db in (self.gold, self.btc):
            with db:
                db.execute("UPDATE attempts SET state='submitting'")
            with self.assertRaisesRegex(ValueError, 'unresolved'):
                self.upgrade(owner_approved=True)
            with db:
                db.execute("UPDATE attempts SET state='closed'")
        self.reviewed = '0'*64
        with self.assertRaisesRegex(ValueError, 'reviewed source'):
            self.upgrade()

    def test_reporting_is_separate_single_window_without_risk_reset(self):
        self.upgrade()
        before = [pilot.state(db) for db in (self.gold, self.btc)]
        risk = self.gold.execute('SELECT data FROM account_limits').fetchone()[0]
        self.upgrade(reporting=True)
        for db, old in zip((self.gold, self.btc), before):
            self.assertEqual(pilot.state(db), {**old, 'reporting_start': NOW, 'reporting_end': NOW+172800})
        self.assertEqual(self.gold.execute('SELECT data FROM account_limits').fetchone()[0], risk)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.upgrade(reporting=True)

    def test_attached_failure_rolls_back_both_and_preserves_pause(self):
        (self.home / 'btc-pilot.pause').touch()
        with self.btc:
            self.btc.execute("CREATE TRIGGER refuse BEFORE UPDATE ON pilot BEGIN SELECT RAISE(ABORT, 'forced'); END")
        before = [dump(db) for db in (self.gold, self.btc)]
        with self.assertRaises(sqlite3.IntegrityError):
            self.upgrade(owner_approved=True)
        self.assertEqual([dump(db) for db in (self.gold, self.btc)], before)
        self.assertTrue((self.home / 'btc-pilot.pause').exists())

    def test_shared_risk_pause_cannot_be_cleared_by_owner_approval(self):
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        for changes in ({'pause': 'Drawdown limit'}, {'code': 'c'*64}):
            with self.gold:
                self.gold.execute('UPDATE account_limits SET data=?', (json.dumps({**risk, **changes}),))
            with self.assertRaisesRegex(ValueError, 'risk'):
                self.upgrade(owner_approved=True)


class DeployTest(unittest.TestCase):
    def test_journal_refuses_missing_or_single_symbol_before_broker_access(self):
        for value in ('', 'XAUUSD-VIP', 'BTCUSD', 'BTCUSD,XAUUSD-VIP'):
            with self.subTest(symbols=value), patch.dict(module['os'].environ,
                    MT5_RUN_MODE='pilot', MT5_PILOT_SYMBOLS=value):
                with self.assertRaisesRegex(ValueError, 'exactly XAUUSD-VIP,BTCUSD'):
                    module['journal'](None)

    def test_reviewed_build_precedes_stop_and_receipt_precedes_recreate(self):
        for receipt_ok in (True, False):
            with self.subTest(receipt_ok=receipt_ok), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                stage = root / 'dual-m5-review-test'
                stage.mkdir()
                names = (*pilot.SOURCES, 'control_server.py', 'status_server.py',
                         'upgrade-dual-m5.py', 'cutover-m1-pilot.py')
                for name in names:
                    (stage / name).write_bytes(Path(__file__).with_name(name).read_bytes())
                files = {n: hashlib.sha256((stage / n).read_bytes()).hexdigest() for n in names}
                sources = {n: files[n] for n in pilot.SOURCES}
                reviewed = pilot.digest(sources)
                (stage / 'manifest.json').write_text(json.dumps(dict(code_sha256=reviewed,
                    previous_code_sha256=reviewed, previous_image='old', files=files, sources=sources)))
                for name in ('compose.yml', 'status_server.py'):
                    (root / name).write_text('old')
                calls = []

                def run(args, **kwargs):
                    calls.append(args)
                    if args[:2] == ['docker', 'inspect']:
                        return json.dumps([{'Image': 'old', 'Config': {'Env': ['MT5_RUN_MODE=pilot', 'MT5_PILOT_SYMBOLS=XAUUSD-VIP,BTCUSD']}}])
                    if args[:3] == ['docker', 'image', 'inspect']:
                        return 'old'
                    if 'config' in args:
                        return json.dumps({'services': {'desktop': {'image': 'kwg-mt5-desktop:qualification',
                            'environment': {'MT5_RUN_MODE': 'pilot', 'MT5_PILOT_SYMBOLS': 'XAUUSD-VIP,BTCUSD'}}}})
                    if args[:2] == ['docker', 'run'] or ('-c' in args and 'hashlib' in args[args.index('-c')+1]):
                        return json.dumps({n: files[n] for n in json.loads(args[-1])})
                    if 'script' in args:
                        if '--apply' not in args[-2]:
                            return 'DUAL_M5_REVIEW_PASSED'
                        self.assertIn(['stop_runner'], calls)
                        if '--start-reporting' in args[-2]:
                            return 'DUAL_M5_REPORTING_STARTED ' + json.dumps(dict(code=reviewed, order_sent=False,
                                reporting_start=NOW, reporting_end=NOW+172800))
                        return ('DUAL_M5_JOURNAL_SWITCHED ' + json.dumps(dict(
                            gold_strategy=pilot.M5_JEV_STRATEGY, btc_strategy=module['BTC_M5'],
                            jev_mode='veto', code=reviewed, order_sent=False))) if receipt_ok else 'missing'
                    return ''

                def stop():
                    calls.append(['stop_runner'])
                    return '{}'

                deploy = module['deploy']
                with patch.dict(deploy.__globals__, ROOT=root, run=run), \
                     patch.object(module['runpy'], 'run_path', return_value={'stop_runner': stop}), \
                     patch('builtins.print'):
                    if receipt_ok:
                        deploy(stage, reviewed, reviewed, True)
                        module['start_reporting'](stage, reviewed)
                    else:
                        with self.assertRaisesRegex(ValueError, 'receipt missing'):
                            deploy(stage, reviewed, reviewed, True)
                self.assertLess(next(i for i, c in enumerate(calls) if 'build' in c), calls.index(['stop_runner']))
                self.assertEqual(any('--force-recreate' in c for c in calls), receipt_ok)
                self.assertEqual(['docker', 'restart', 'kwg-mt5-desktop'] in calls, receipt_ok)
                self.assertTrue(any(c[:2] == ['docker', 'cp'] for c in calls))


if __name__ == '__main__':
    unittest.main()
