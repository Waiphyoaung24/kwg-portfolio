"""Gold M5 Jev shadow cutover: refusals, preserved state and an untouched BTC journal."""
import hashlib
import json
from pathlib import Path
import runpy
import sqlite3
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import demo_pilot as pilot
from instruments import BTC

module = runpy.run_path(str(Path(__file__).with_name('switch-pilot-m5.py')))
NOW = 1_800_000_000
PREVIOUS = 'a' * 64


def record(**changes):
    value = dict(start=NOW - 3600, end=None, run_policy='continuous', strategy=pilot.TREND_STRATEGY,
                 code=PREVIOUS, offset=10800, initial_equity=1000.0, initial_balance=1000.0, peak=1010.0,
                 day=NOW // 86400, day_equity=1005.0, last_poll=NOW - 5, last_bar=NOW - 120,
                 pause=None, reason='Waiting')
    value.update(changes)
    return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(db, skip_pilot=False):
    return [line for line in db.iterdump() if not (skip_pilot and line.startswith('INSERT INTO "pilot"'))]


class SwitchM5Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.gold = pilot.open_state(self.home / 'gold-pilot.sqlite3', 123)
        self.btc = pilot.open_state(self.home / 'btc-pilot.sqlite3', 123, BTC)
        with self.gold:
            self.gold.execute('INSERT INTO pilot VALUES (1, ?)', (json.dumps(record()),))
            self.gold.execute('CREATE TABLE account_limits (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
            self.gold.execute('INSERT INTO account_limits VALUES (1, ?)', (json.dumps(record(strategy=None)),))
            # A closed trade receipt must survive the switch unchanged.
            self.gold.execute("INSERT INTO attempts (id, side, armed_at, expires_at, state, phase, realized_net_usd) "
                              "VALUES ('t1', 'buy', ?, ?, 'closed', 'close', 1.25)", (NOW - 900, NOW))
        self.reviewed = pilot.identity()

    def tearDown(self):
        self.gold.close()
        self.btc.close()
        self.temp.cleanup()

    def activate_btc(self, **changes):
        with self.btc:
            self.btc.execute('INSERT INTO pilot VALUES (1, ?)', (json.dumps(record(strategy='btc-ema-v1-m1-scalp-60', **changes)),))

    def switch(self, reviewed=None):
        return module['switch'](self.gold, self.btc, self.home, NOW, reviewed or self.reviewed, PREVIOUS,
                                self.home / 'backup')

    def test_switch_sets_m5_shadow_and_preserves_window_limits_and_receipts(self):
        p = pilot.state(self.gold)
        p['pending_entry'] = {'bar_time': 1, 'side': 'long', 'input_sha256': 'x'}
        pilot.save(self.gold, p)
        risk_before = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        attempts = [tuple(r) for r in self.gold.execute('SELECT * FROM attempts')]
        btc_before = digest(self.home / 'btc-pilot.sqlite3')
        result = self.switch()
        after = pilot.state(self.gold)
        self.assertEqual(after['strategy'], pilot.M5_JEV_STRATEGY)
        self.assertEqual(after['jev_mode'], 'shadow')
        self.assertEqual(after['code'], self.reviewed)
        self.assertIsNone(after['last_bar'])
        self.assertNotIn('pending_entry', after)
        for key in ('start', 'end', 'run_policy', 'offset', 'peak', 'day', 'day_equity', 'initial_balance', 'pause'):
            self.assertEqual(after[key], p[key])
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertEqual(risk, {**risk_before, 'code': self.reviewed})
        self.assertEqual([tuple(r) for r in self.gold.execute('SELECT * FROM attempts')], attempts)
        # Standby BTC (no activation) is byte-identical.
        self.assertEqual(digest(self.home / 'btc-pilot.sqlite3'), btc_before)
        self.assertFalse(result['btc_code_updated'])
        self.assertIs(result['order_sent'], False)
        for name in ('gold', 'btc'):
            with sqlite3.connect(self.home / 'backup' / (name + '.sqlite3')) as backup:
                self.assertEqual(backup.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
        with sqlite3.connect(self.home / 'backup' / 'gold.sqlite3') as backup:
            self.assertEqual(json.loads(backup.execute('SELECT data FROM pilot').fetchone()[0])['strategy'], pilot.TREND_STRATEGY)

    def test_activated_btc_keeps_everything_except_the_shared_code_field(self):
        self.activate_btc(pause='Paused by owner')
        before, rows = pilot.state(self.btc), dump(self.btc, skip_pilot=True)
        result = self.switch()
        self.assertTrue(result['btc_code_updated'])
        self.assertEqual(pilot.state(self.btc), {**before, 'code': self.reviewed})
        self.assertEqual(dump(self.btc, skip_pilot=True), rows)
        # The runner's shared identity check now accepts both journals under the loaded code.
        for db in (self.gold, self.btc):
            self.assertEqual(pilot.state(db)['code'], pilot.identity())

    def test_failed_btc_update_rolls_back_both_journals(self):
        self.activate_btc()
        with self.btc:
            # Fail the attached BTC write after the Gold rows were updated in the same transaction.
            self.btc.execute("CREATE TRIGGER refuse BEFORE UPDATE ON pilot BEGIN SELECT RAISE(ABORT, 'forced'); END")
        gold_before, btc_before = dump(self.gold), dump(self.btc)
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'forced'):
            self.switch()
        self.assertEqual(dump(self.gold), gold_before)
        self.assertEqual(dump(self.btc), btc_before)
        self.assertNotIn('btc_switch', [row[1] for row in self.gold.execute('PRAGMA database_list')])

    def test_refusals_leave_both_journals_unchanged(self):
        cases = {
            'open': lambda: self.attempt('open'),
            'pending': lambda: self.attempt('pending'),
            'needs_attention': lambda: self.attempt('needs_attention'),
            'submitting': lambda: self.attempt('submitting'),
            'closing': lambda: self.attempt('closing'),
            'paused': lambda: self.change(pause='Daily equity loss limit reached'),
            'pause file': lambda: (self.home / 'gold-pilot.pause').write_text(''),
            'shared pause': lambda: self.limits(pause='Pilot drawdown limit reached'),
            'expired': lambda: self.change(end=NOW, run_policy=None),
            'wrong strategy': lambda: self.change(strategy=pilot.M1_STRATEGY),
            'already m5': lambda: self.change(strategy=pilot.M5_JEV_STRATEGY, jev_mode='shadow'),
            'journal code': lambda: self.change(code='b' * 64),
            'btc code': lambda: self.activate_btc(code='b' * 64),
        }
        messages = {'open': 'unresolved', 'paused': 'paused', 'pause file': 'Owner pause', 'shared pause': 'latched',
                    'expired': 'ended', 'wrong strategy': 'requires', 'already m5': 'requires',
                    'journal code': 'deployed source', 'btc code': 'BTC journal code'}
        for name, prepare in cases.items():
            with self.subTest(name):
                self.tearDown()
                self.setUp()
                prepare()
                gold_before, btc_before = dump(self.gold), dump(self.btc)
                with self.assertRaisesRegex(ValueError, messages.get(name, 'unresolved')):
                    self.switch()
                self.assertEqual(dump(self.gold), gold_before)
                self.assertEqual(dump(self.btc), btc_before)
                self.assertFalse((self.home / 'backup').exists())

    def test_reviewed_hash_mismatch_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'reviewed staging code'):
            self.switch('0' * 64)
        self.assertEqual(pilot.state(self.gold)['strategy'], pilot.TREND_STRATEGY)

    def test_journal_step_never_imports_the_broker_sdk(self):
        source = Path(__file__).with_name('switch-pilot-m5.py').read_text()
        self.assertNotIn('MetaTrader5', source)
        self.assertNotIn('order_send', source)

    def attempt(self, state):
        with self.gold:
            self.gold.execute("INSERT INTO attempts (id, side, armed_at, expires_at, state, phase) "
                              "VALUES ('t2', 'buy', ?, ?, ?, 'entry')", (NOW, NOW + 900, state))

    def change(self, **values):
        pilot.save(self.gold, {**pilot.state(self.gold), **values})

    def limits(self, **values):
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps({**risk, **values}),))


class DeployM5Test(unittest.TestCase):
    def make_stage(self, root, *, tamper=False, drop_jev=False):
        stage = root / 'm5-jev-review-test'
        stage.mkdir()
        source = Path(__file__).parent
        names = (*pilot.SOURCES, 'control_server.py', 'status_server.py', 'cutover-m1-pilot.py', 'switch-pilot-m5.py')
        for name in names:
            (stage / name).write_bytes((source / name).read_bytes())
        files = {n: digest(stage / n) for n in names}
        sources = {n: files[n] for n in pilot.SOURCES if not (drop_jev and n == 'jev_m5.py')}
        (stage / 'manifest.json').write_text(json.dumps(dict(code_sha256=pilot.digest(sources), sources=sources,
                                                             previous_image='old', files=files)))
        if tamper:
            (stage / 'jev_m5.py').write_text('changed')
        (root / 'status_server.py').write_text('old status')
        return stage, pilot.digest(sources)

    def deploy(self, *, tamper=False, drop_jev=False, receipt_ok=True, review_ok=True, pilot_status='active'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage, reviewed = self.make_stage(root, tamper=tamper, drop_jev=drop_jev)
            calls = []

            def run(args, **kwargs):
                calls.append(args)
                if args[:2] == ['docker', 'inspect']:
                    return '[{"Image":"old"}]'
                if args[:3] == ['docker', 'image', 'inspect']:
                    return 'old'
                if 'config' in args:
                    return json.dumps({'services': {'desktop': {'image': 'kwg-mt5-desktop:qualification',
                                                                'environment': {'MT5_RUN_MODE': 'pilot'}}}})
                if args[:2] == ['docker', 'run']:
                    names = json.loads(args[-1])
                    self.assertIn('jev_m5.py', names)
                    return json.dumps({n: digest(stage / n) for n in names})
                if 'script' in args:
                    self.assertIn('--journal', args[-2])
                    if '--apply' not in args[-2]:
                        if not review_ok:
                            raise subprocess.CalledProcessError(1, args, b'Gold attempt is open or unresolved')
                        return 'M5_JEV_REVIEW_PASSED {}'
                    self.assertIn(['stop_runner'], calls)
                    result = dict(strategy=pilot.M5_JEV_STRATEGY, jev_mode='shadow', code=reviewed, ends_at=None, order_sent=False)
                    return 'M5_JEV_JOURNAL_SWITCHED ' + json.dumps(result) if receipt_ok else 'missing'
                if 'kwg-trading-status' in args:
                    return json.dumps(dict(checked_at=time.time(), pilot=dict(strategy=pilot.M5_JEV_STRATEGY,
                                                                                jev_mode='shadow', ends_at=None,
                                                                                status=pilot_status)))
                return ''

            def stop():
                calls.append(['stop_runner'])
                return '{}'
            deploy = module['deploy']
            with patch.dict(deploy.__globals__, ROOT=root, run=run), \
                    patch.object(module['runpy'], 'run_path', return_value={'stop_runner': stop}), \
                    patch('builtins.print') as output:
                try:
                    deploy(stage, reviewed)
                    error = None
                except (ValueError, RuntimeError) as exc:
                    error = str(exc)
            dockerfile = (stage / 'Dockerfile').read_text() if (stage / 'Dockerfile').exists() else ''
            return error, calls, output, (root / 'status_server.py').read_text(), dockerfile

    def test_success_builds_before_stopping_and_requires_receipt_before_recreate(self):
        error, calls, output, status, dockerfile = self.deploy()
        self.assertIsNone(error)
        self.assertIn(' jev_m5.py ', dockerfile)
        self.assertLess(next(i for i, c in enumerate(calls) if 'build' in c), calls.index(['stop_runner']))
        script = next(i for i, c in enumerate(calls) if 'script' in c)
        self.assertLess(script, next(i for i, c in enumerate(calls) if '--force-recreate' in c))
        self.assertNotEqual(status, 'old status')
        self.assertTrue(any(c.args and c.args[0] == 'M5_JEV_SHADOW_DEPLOYED' for c in output.call_args_list))

    def test_missing_receipt_leaves_runner_stopped_and_files_unchanged(self):
        error, calls, _, status, _ = self.deploy(receipt_ok=False)
        self.assertIn('receipt missing', error)
        self.assertEqual(status, 'old status')
        self.assertFalse(any('--force-recreate' in c for c in calls))

    def test_container_review_refusal_never_stops_the_runner_or_builds(self):
        error, calls, _, status, _ = self.deploy(review_ok=False)
        self.assertIn('runner untouched', error)
        self.assertNotIn(['stop_runner'], calls)
        self.assertFalse(any('build' in c or 'tag' in c for c in calls))
        self.assertFalse(any('--apply' in c[-2] for c in calls if 'script' in c))
        self.assertEqual(status, 'old status')

    def test_review_runs_before_stopping_the_runner(self):
        _, calls, _, _, _ = self.deploy()
        review = next(i for i, c in enumerate(calls) if 'script' in c and '--apply' not in c[-2])
        self.assertLess(review, calls.index(['stop_runner']))

    def test_paused_runner_after_restart_fails_verification(self):
        for status in ('paused', 'needs_attention'):
            with self.subTest(status), patch.object(module['time'], 'sleep'):
                error, _, output, _, _ = self.deploy(pilot_status=status)
                self.assertIn('not active', error)
                self.assertFalse(any(c.args and c.args[0] == 'M5_JEV_SHADOW_DEPLOYED' for c in output.call_args_list))

    def test_tampered_or_incomplete_stage_never_reaches_docker(self):
        for kwargs, message in (({'tamper': True}, 'Stage file identity'), ({'drop_jev': True}, 'differs from stage')):
            with self.subTest(**kwargs):
                error, calls, _, _, _ = self.deploy(**kwargs)
                self.assertIn(message, error)
                self.assertEqual(calls, [])


class StageM5Test(unittest.TestCase):
    def remote(self):
        source = Path(__file__).with_name('stage-m5-jev.ps1').read_text()
        return source, source.split("$taskRemote = @'\n", 1)[1].split("\n'@", 1)[0]

    def test_stage_ships_reviewed_sources_and_runs_read_only_review(self):
        source, remote = self.remote()
        compile(remote.replace('PAYLOAD', ''), 'm5-stage', 'exec')
        shipped = source.split('$taskNames = @(', 1)[1].split(')', 1)[0]
        for name in (*pilot.SOURCES, 'control_server.py', 'status_server.py', 'cutover-m1-pilot.py',
                     'switch-pilot-m5.py', 'promote-jev-veto.py', 'jev_m5_scorecard.py'):
            self.assertIn("'" + name + "'", shipped)
        self.assertIn("sources = " + repr(pilot.SOURCES).replace(', ', ','), remote)
        review = remote.split("command = ('stty", 1)[1].split('\n', 2)[:2]
        self.assertIn('--journal --reviewed-code-sha256', ''.join(review))
        self.assertNotIn('--apply', ''.join(review))
        for marker in ('M5_JEV_STAGE', 'M5_JEV_REVIEWED_CODE', 'REVIEW_ONLY'):
            self.assertIn("print('" + marker, remote)

    def test_staged_helper_loads_staged_modules_with_manifest_identity(self):
        import subprocess, sys
        source = Path(__file__).parent
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            for name in (*pilot.SOURCES, 'switch-pilot-m5.py'):
                (stage / name).write_bytes((source / name).read_bytes().replace(b'\r\n', b'\n'))
            expected = pilot.digest({n: digest(stage / n) for n in pilot.SOURCES})
            result = subprocess.run([sys.executable, '-I', '-B', '-c',
                "import runpy,sys; p=runpy.run_path(sys.argv[1])['pilot']; print(p.__file__); print(p.identity())",
                str(stage / 'switch-pilot-m5.py')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertEqual(Path(lines[0]).resolve(), (stage / 'demo_pilot.py').resolve())
            self.assertEqual(lines[1], expected)

    def test_scorecard_timer_units_run_read_only_every_minute(self):
        import ast
        _, remote = self.remote()
        tree = ast.parse(remote.replace('PAYLOAD', ''))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'units')
        constants = {t.id: ast.literal_eval(n.value.args[0]) for n in tree.body if isinstance(n, ast.Assign)
                     for t in n.targets if isinstance(t, ast.Name) and isinstance(n.value, ast.Call)
                     and getattr(n.value.func, 'attr', None) == 'Path' and n.value.args
                     and isinstance(n.value.args[0], ast.Constant)}
        mt5 = '/var/lib/docker/volumes/kwg-mt5-qualification_mt5-home/_data/.wine/drive_c/users/mt5'
        status = '/var/lib/docker/volumes/kwg-mt5-qualification_status-snapshot/_data'
        self.assertEqual(constants['volume'], mt5)
        self.assertEqual(constants['output'], status + '/jev-m5-scorecard.json')
        self.assertIn("journal = volume / 'gold-pilot.sqlite3'", remote)
        self.assertIn("receipts = volume / 'jev-m5-receipts.sqlite3'", remote)
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'units', 'exec'), namespace)
        command = ['/usr/bin/python3', '/opt/kwg-mt5-qualification/jev-m5-scorecard/jev_m5_scorecard.py',
                   '--journal', mt5 + '/gold-pilot.sqlite3', '--receipts', mt5 + '/jev-m5-receipts.sqlite3',
                   '--output', status + '/jev-m5-scorecard.json']
        units = namespace['units'](command, status)
        self.assertEqual(set(units), {'kwg-jev-m5-scorecard.service', 'kwg-jev-m5-scorecard.timer'})
        service, timer = units['kwg-jev-m5-scorecard.service'], units['kwg-jev-m5-scorecard.timer']
        self.assertIn('Type=oneshot\n', service)
        self.assertIn('ExecStart=' + ' '.join(command) + '\n', service)
        for line in ('ProtectSystem=strict', 'ReadWritePaths=' + status, 'PrivateNetwork=yes', 'NoNewPrivileges=yes',
                     'PrivateTmp=yes', 'ProtectHome=yes', 'RestrictAddressFamilies=AF_UNIX',
                     'CapabilityBoundingSet=CAP_DAC_OVERRIDE'):
            self.assertIn(line + '\n', service)
        self.assertNotIn('User=', service)  # Root: /var/lib/docker is not traversable by uid 10001.
        self.assertIn('OnUnitActiveSec=60\n', timer)
        self.assertIn('WantedBy=timers.target\n', timer)
        self.assertIn("'enable','--now','kwg-jev-m5-scorecard.timer'", remote)
        # Publisher scripts live in a root-owned host directory, not the container-writable volume.
        self.assertIn("publisher = root / 'jev-m5-scorecard'", remote)
        self.assertEqual(command[0], '/usr/bin/python3')  # Host Python only; no docker exec or Wine.

    def test_receiver_rejects_bad_hash(self):
        import ast, base64, subprocess, sys
        _, remote = self.remote()
        receiver = next(ast.literal_eval(n.value) for n in ast.parse(remote.replace('PAYLOAD', '')).body
                        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'receiver' for t in n.targets))
        raw = b'x = 1\n'
        bundle = {'sample.py': {'data': base64.b64encode(raw).decode(), 'sha256': 'wrong'}}
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', '-c', receiver, directory + '/stage'],
                                    input=json.dumps(bundle).encode(), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(directory) / 'stage' / 'sample.py').exists())


class PublisherTest(unittest.TestCase):
    def test_installed_pair_runs_standalone_and_publishes_unavailable_without_journal(self):
        import subprocess, sys
        source = Path(__file__).parent
        with tempfile.TemporaryDirectory() as directory:
            publisher = Path(directory) / 'jev-m5-scorecard'
            publisher.mkdir()
            for name in ('jev_m5_scorecard.py', 'jev_m5.py'):
                (publisher / name).write_bytes((source / name).read_bytes())
            output = Path(directory) / 'jev-m5-scorecard.json'
            result = subprocess.run([sys.executable, '-B', str(publisher / 'jev_m5_scorecard.py'),
                                     '--journal', directory + '/missing.sqlite3', '--receipts', directory + '/r.sqlite3',
                                     '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())['status'], 'unavailable')
            self.assertFalse((Path(directory) / 'r.sqlite3').exists())


if __name__ == '__main__':
    unittest.main()
