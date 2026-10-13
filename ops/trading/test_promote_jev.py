"""Owner-gated Jev veto promotion and demotion: refusals, audit row, untouched state."""
import hashlib
import json
from pathlib import Path
import re
import runpy
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

import demo_pilot as pilot

module = runpy.run_path(str(Path(__file__).with_name('promote-jev-veto.py')))
NOW = 1_800_000_000
PASSING = dict(status='ready', closed=60, gate=dict(passes=True, reasons=[]))


def dump(db):
    return list(db.iterdump())


class PromoteJevTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.path = self.home / 'gold-pilot.sqlite3'
        self.db = pilot.open_state(self.path, 123)
        self.record = dict(start=NOW - 3600, end=None, run_policy='continuous', strategy=pilot.M5_JEV_STRATEGY,
                           jev_mode='shadow', code=pilot.identity(), offset=10800, initial_equity=1000.0,
                           initial_balance=1000.0, peak=1000.0, day=NOW // 86400, day_equity=1000.0,
                           last_poll=NOW, last_bar=None, pause=None, reason='Waiting')
        with self.db:
            self.db.execute('INSERT INTO pilot VALUES (1, ?)', (json.dumps(self.record),))
            self.db.execute('CREATE TABLE account_limits (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
            self.db.execute('INSERT INTO account_limits VALUES (1, ?)', (json.dumps(self.record),))

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def change(self, value=PASSING, *, approved=True, demote=False):
        backup = self.home / ('backup-' + str(time.time_ns()) + '.sqlite3')
        return module['change'](self.db, NOW, value, owner_approved=approved, demote=demote, backup=backup)

    def backups(self):
        return sorted(self.home.glob('backup-*.sqlite3'))

    def audit(self):
        return [tuple(r) for r in self.db.execute('SELECT * FROM jev_mode_changes')]

    def test_promotion_flips_only_jev_mode_and_writes_audit_row(self):
        limits = self.db.execute('SELECT data FROM account_limits').fetchone()[0]
        result = self.change()
        self.assertEqual(pilot.state(self.db), {**self.record, 'jev_mode': 'veto'})
        self.assertEqual(self.db.execute('SELECT data FROM account_limits').fetchone()[0], limits)
        digest = hashlib.sha256(json.dumps(PASSING, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(self.audit(), [(NOW, 'shadow', 'veto', digest)])
        self.assertEqual(result['order_sent'], False)
        self.assertEqual((result['from_mode'], result['to_mode'], result['scorecard_sha256']), ('shadow', 'veto', digest))
        # The journal is copied with the backup API before the flip and passes an integrity check.
        [backup] = self.backups()
        self.assertEqual(result['backup'], str(backup))
        with sqlite3.connect(backup) as saved:
            self.assertEqual(saved.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual(json.loads(saved.execute('SELECT data FROM pilot').fetchone()[0])['jev_mode'], 'shadow')

    def test_demotion_is_allowed_any_time_and_audited(self):
        self.change()
        failing = dict(PASSING, gate=dict(passes=False, reasons=['Need 50']))
        self.change(failing, demote=True)
        self.assertEqual(pilot.state(self.db)['jev_mode'], 'shadow')
        # Demotion without any scorecard (export failed) is still recorded.
        self.change()
        self.change(None, demote=True)
        rows = self.audit()
        self.assertEqual([(r[1], r[2]) for r in rows], [('shadow', 'veto'), ('veto', 'shadow')] * 2)
        self.assertIsNone(rows[-1][3])
        self.assertIsNone(module['card'](self.home / 'missing.sqlite3', self.home / 'r.sqlite3', NOW, demote=True))

    def test_refusals_leave_journal_unchanged(self):
        failing = dict(PASSING, gate=dict(passes=False, reasons=['Need 50']))
        cases = {
            'missing flag': (dict(approved=False), None, 'owner approval'),
            'failing gate': (dict(value=failing), None, 'gate does not pass'),
            'no scorecard': (dict(value=None), None, 'gate does not pass'),
            'wrong strategy': ({}, dict(strategy=pilot.TREND_STRATEGY), 'requires the Gold'),
            'already veto': ({}, dict(jev_mode='veto'), 'expected shadow'),
            'demote shadow': (dict(demote=True), None, 'expected veto'),
            'code mismatch': ({}, dict(code='0' * 64), 'staged code'),
        }
        for name, (kwargs, changes, message) in cases.items():
            with self.subTest(name):
                self.tearDown()
                self.setUp()
                if changes:
                    pilot.save(self.db, {**self.record, **changes})
                before = dump(self.db)
                with self.assertRaisesRegex(ValueError, message):
                    self.change(**kwargs)
                self.assertEqual(dump(self.db), before)
                self.assertEqual(self.backups(), [])

    def test_real_scorecard_gate_refuses_an_empty_shadow_journal(self):
        with self.assertRaisesRegex(ValueError, 'Need 50 closed shadow trades'):
            module['card'](self.path, self.home / 'jev-m5-receipts.sqlite3', NOW, demote=False)
        self.assertFalse((self.home / 'jev-m5-receipts.sqlite3').exists())

    def test_cli_requires_owner_flag(self):
        before = dump(self.db)
        with patch('sys.argv', ['promote-jev-veto.py', '--journal']), patch('sys.stderr'), \
                self.assertRaises(SystemExit):
            module['main']()
        self.assertEqual(dump(self.db), before)

    def test_runner_never_changes_jev_mode_by_itself(self):
        source = Path(__file__).with_name('demo_pilot.py').read_text()
        self.assertIsNone(re.search(r"\['jev_mode'\]\s*=(?!=)", source))
        for pattern in ('update(jev_mode', "'jev_mode': 'veto'", "'jev_mode': 'shadow'"):
            self.assertNotIn(pattern, source)
        self.assertNotIn('MetaTrader5', Path(__file__).with_name('promote-jev-veto.py').read_text())


class PromoteDeployTest(unittest.TestCase):
    def deploy(self, *, gate=True, receipt_ok=True, demote=False, journal=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / 'm5-jev-review-test'
            stage.mkdir()
            (stage / 'promote-jev-veto.py').write_text('x')
            (stage / 'manifest.json').write_text(json.dumps(dict(code_sha256=pilot.identity(), files={
                'promote-jev-veto.py': hashlib.sha256(b'x').hexdigest()})))
            volume = root / 'volume'
            volume.mkdir()
            db = pilot.open_state(volume / 'gold-pilot.sqlite3', 123)
            record = dict(strategy=pilot.M5_JEV_STRATEGY, jev_mode='veto' if demote else 'shadow', code=pilot.identity())
            with db:
                db.execute('INSERT INTO pilot VALUES (1, ?)', (json.dumps({**record, **(journal or {})}),))
            db.close()
            calls = []

            def run(args, **kwargs):
                calls.append(args)
                if 'script' in args:
                    self.assertIn('--owner-approved', args[-2])
                    self.assertEqual('--demote' in args[-2], demote)
                    target = 'shadow' if demote else 'veto'
                    return 'JEV_MODE_CHANGED ' + json.dumps(dict(to_mode=target)) if receipt_ok else 'missing'
                if 'kwg-trading-status' in args:
                    return json.dumps(dict(checked_at=time.time(), pilot=dict(jev_mode='shadow' if demote else 'veto')))
                return ''

            def export(journal, receipts, now):
                calls.append(['export'])
                return dict(PASSING, gate=dict(passes=gate, reasons=[] if gate else ['Need 50']))

            def stop():
                calls.append(['stop_runner'])
                return '{}'
            deploy = module['deploy']
            with patch.dict(deploy.__globals__, ROOT=root, run=run, VOLUME=volume), \
                    patch.object(module['scorecard'], 'export', export), \
                    patch('runpy.run_path', return_value={'stop_runner': stop}), patch('builtins.print') as output:
                try:
                    deploy(stage, demote=demote)
                    error = None
                except ValueError as exc:
                    error = str(exc)
            return error, calls, output

    def test_failing_gate_refuses_before_stopping_the_runner(self):
        error, calls, _ = self.deploy(gate=False)
        self.assertIn('gate does not pass', error)
        self.assertEqual(calls, [['export']])

    def test_host_journal_refusals_never_stop_the_runner(self):
        cases = (({'strategy': pilot.TREND_STRATEGY}, False, 'requires the Gold'),
                 ({'jev_mode': 'veto'}, False, 'expected shadow'),
                 ({'jev_mode': 'shadow'}, True, 'expected veto'),
                 ({'code': '0' * 64}, False, 'staged code'))
        for journal, demote, message in cases:
            with self.subTest(journal=journal, demote=demote):
                error, calls, _ = self.deploy(journal=journal, demote=demote)
                self.assertIn(message, error)
                self.assertEqual(calls, [])

    def test_promotion_order_and_receipt_before_restart(self):
        error, calls, output = self.deploy()
        self.assertIsNone(error)
        order = [c[0] if len(c) == 1 else 'script' if 'script' in c else 'up' if 'up' in c else None for c in calls]
        order = [x for x in order if x]
        self.assertEqual(order[:4], ['export', 'stop_runner', 'script', 'up'])
        self.assertTrue(any(c.args and c.args[0] == 'JEV_VETO_PROMOTED' for c in output.call_args_list))
        error, calls, _ = self.deploy(receipt_ok=False)
        self.assertIn('receipt missing', error)
        self.assertFalse(any('up' in c for c in calls))

    def test_demotion_skips_the_gate(self):
        error, calls, output = self.deploy(gate=False, demote=True)
        self.assertIsNone(error)
        self.assertNotIn(['export'], calls)
        self.assertTrue(any(c.args and c.args[0] == 'JEV_SHADOW_DEMOTED' for c in output.call_args_list))


if __name__ == '__main__':
    unittest.main()
