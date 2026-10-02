import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import base64
import contextlib
import io
import ast

spec = importlib.util.spec_from_file_location('capture', Path(__file__).with_name('capture-observer.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
original_open = Path.open


class CaptureTest(unittest.TestCase):
    def test_powershell_serializes_exact_pinned_retention_trials(self):
        launcher = Path(__file__).with_name('run-diagnostic-trial.ps1')
        command = "Import-Module ($PSHOME + '/Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1'); function global:ssh { $global:LASTEXITCODE = 0; $input }; & '" + str(launcher) + "' -RetentionReview"
        result = subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command',command],
            capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,'Offline launcher generation failed: '+result.stderr[:1000])
        tree = ast.parse(result.stdout)
        trials = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='trials' for t in n.targets))
        self.assertEqual(trials,[
            ['/root/kwg-gold-research/evidence/retention-handoff-20261002T092809Z-d1e5fda8',
             'e9f299d55b5c81f6d47456cac44a3a799c066bc946947277bd7e479eb1da7636'],
            ['/root/kwg-gold-research/evidence/retention-handoff-20261002T093048Z-df5db154',
             '6bb0dc77240f6e125c7e185f193147d034828b12d9b9960cb2646ee633c53772']])

    def test_retention_review_reconciles_saved_bytes_without_writes(self):
        from test_retention_supervisor import segment
        import retention_supervisor as retention
        script = Path(__file__).with_name('run-diagnostic-trial.ps1').read_text()
        remote = script.split("if ($RetentionReview) {\n    $taskRemote = @'\n", 1)[1].split("\n'@", 1)[0]
        with tempfile.TemporaryDirectory() as parent:
            run = Path(parent)/'trial'
            (run/'code').mkdir(parents=True)
            root = run/'supervision'
            root.mkdir()
            bundle = {}
            for name in ('capture-observer.py','review_observer_log.py','retention_supervisor.py'):
                raw = Path(__file__).with_name(name).read_bytes()
                (run/'code'/name).write_bytes(raw)
                bundle[name] = {'sha256':hashlib.sha256(raw).hexdigest()}
            folders = [root/'segment-00',root/'segment-01']
            segment(folders[0],[1000,1005,1010])
            segment(folders[1],[1005,1010,1015])
            for folder in folders:
                path = folder/'receipt.json'
                value = json.loads(path.read_bytes())
                value['mode'] = 'docker_follow'
                path.write_text(json.dumps(value))
            checked = retention.review(folders,1000,1015)
            receipt = {'segments':[str(f) for f in folders],'started_at':1000,'ended_at':1015,
                'mode':'bounded_supervision','evidence_mode':'docker_follow','review':checked,
                'code_sha256':retention.source_hashes(),
                'supervisor_sha256':bundle['retention_supervisor.py']['sha256'],
                'blockers':[],'qualification':'unqualified','promotion_status':'blocked',
                'observed_days':0,'model_requests':0}
            path = root/'supervisor.json'
            path.write_bytes(retention.encode(receipt))
            payload = base64.b64encode(json.dumps(bundle).encode()).decode()
            remote = remote.replace('PAYLOAD',payload)
            assignment = next(line for line in remote.splitlines() if line.startswith('trials = '))
            remote = remote.replace(assignment,'trials = '+repr([(str(run),hashlib.sha256(path.read_bytes()).hexdigest())]))
            original = {str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()}
            output = io.StringIO()
            with patch('subprocess.Popen',side_effect=AssertionError('No processes')), \
                    patch('stat.S_IMODE',side_effect=lambda m: 0o700 if __import__('stat').S_ISDIR(m) else 0o600), \
                    patch('pathlib.Path.open',autospec=True,side_effect=lambda p,mode='r',*a,**k:
                          original_open(p,mode,*a,**k) if mode=='rb' else (_ for _ in ()).throw(AssertionError('No writes'))), \
                    contextlib.redirect_stdout(output):
                exec(compile(remote,'retention-review','exec'),{})
            result = json.loads(output.getvalue())
            self.assertEqual(result['attempts'][0]['unique_samples'],4)
            self.assertEqual(result['attempts'][0]['blockers'],[])
            self.assertEqual(original,{str(p):p.read_bytes() for p in run.rglob('*') if p.is_file()})
            exists = Path.exists
            output = io.StringIO()
            with patch('pathlib.Path.exists',autospec=True,side_effect=lambda p:
                    False if p == root/'supervisor.json' else exists(p)), contextlib.redirect_stdout(output):
                with self.assertRaisesRegex(SystemExit,'saved path unavailable'):
                    exec(compile(remote,'retention-review','exec'),{})
            self.assertIn({'relative':'supervision'+__import__('os').sep+'supervisor.json',
                'exists':False,'symlink':False},json.loads(output.getvalue())['required_paths'])
            is_file = Path.is_file
            with patch('pathlib.Path.is_file',autospec=True,side_effect=lambda p:
                    False if p == folders[1]/'diagnostics.jsonl' else is_file(p)), \
                    patch('stat.S_IMODE',side_effect=lambda m: 0o700 if __import__('stat').S_ISDIR(m) else 0o600), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(SystemExit,'artifact shape invalid'):
                    exec(compile(remote,'retention-review','exec'),{})
            (folders[1]/'diagnostics.jsonl').write_bytes(b'changed')
            with self.assertRaisesRegex(SystemExit,'reconciliation differs'):
                exec(compile(remote,'retention-review','exec'),{})

    def test_read_only_review_checks_actual_fixture_bytes(self):
        script = Path(__file__).with_name('run-diagnostic-trial.ps1').read_text()
        remote = script.split("if ($ReviewOnly) {\n    $taskRemote = @'\n", 1)[1].split("\n'@", 1)[0]
        with tempfile.TemporaryDirectory() as parent:
            run = Path(parent)/'run'
            run.mkdir()
            (run/'code').mkdir()
            bundle = {}
            for name in ('capture-observer.py', 'review_observer_log.py'):
                raw = Path(__file__).with_name(name).read_bytes()
                (run/'code'/name).write_bytes(raw)
                bundle[name] = {'sha256': hashlib.sha256(raw).hexdigest()}
            sample = json.dumps({'mode':'signal-only','symbol':'XAUUSD-VIP',
                'status':'duplicate','signal':'none','health':{'sampled_at':1000,'quote':'fresh'}}).encode()
            receipt = capture.capture([sample], run/'capture', mode='synthetic_fixture')
            remote = remote.replace('PAYLOAD', base64.b64encode(json.dumps(bundle).encode()).decode())
            remote = remote.replace("'/root/kwg-gold-research/evidence/diagnostic-trial-20261002T083518Z-840efc3b'", repr(str(run)))
            remote = remote.replace('32b15c2054d491e217ebb5322f8e2029719414a8c960e08a5aa5fc2bfdac1b45', receipt['sha256'])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile(remote, 'fixture-receipt-review', 'exec'), {})
            result = json.loads(output.getvalue())
            self.assertTrue(result['bytes_verified'])
            self.assertEqual(result['status_counts'], {'duplicate': 1})
            changed = dict(receipt, observed_days=99, promotion_status='approved')
            (run/'capture'/'receipt.json').write_text(json.dumps(changed))
            with self.assertRaisesRegex(SystemExit, 'evidence boundary differs'):
                exec(compile(remote, 'fixture-receipt-review', 'exec'), {})
            (run/'capture'/'receipt.json').write_text(json.dumps(receipt))
            before = (run/'capture'/'diagnostics.jsonl').read_bytes()
            self.assertEqual(hashlib.sha256(before).hexdigest(), receipt['sha256'])
            (run/'capture'/'diagnostics.jsonl').write_bytes(before+b'changed')
            with self.assertRaisesRegex(SystemExit, 'byte identity differs'):
                exec(compile(remote, 'fixture-receipt-review', 'exec'), {})

    def test_trial_launcher_refuses_wrong_source_before_writes(self):
        script = Path(__file__).with_name('run-diagnostic-trial.ps1').read_text()
        remote = script.split("$taskRemote = @'\n", 1)[1].split("\n'@", 1)[0]
        bundle = base64.b64encode(json.dumps({'desktop.sh': {'sha256': '0'*64}}).encode()).decode()
        remote = remote.replace('PAYLOAD', bundle)
        remote = remote.replace('RETENTION', 'True')
        with patch('subprocess.check_output', side_effect=[b'running fixed 0', b'wrong launcher']), \
                patch('pathlib.Path.mkdir') as mkdir, patch('os.umask'):
            with self.assertRaisesRegex(SystemExit, 'launcher identity differs'):
                exec(compile(remote, 'trial-launcher', 'exec'), {})
        mkdir.assert_not_called()

    def test_wrapped_samples_private_fields_and_gaps(self):
        records = [{'mode': 'signal-only', 'symbol': 'XAUUSD-VIP', 'status': status,
                    'signal': 'none', 'reason': 'SECRET-CANARY',
                    'token': 'SECRET-CANARY', 'health': {'sampled_at': stamp,
                    'quote': 'fresh', 'bid': 2000, 'login': 12345}}
                   for status, stamp in [('blocked', 1000), ('duplicate', 1005), ('observed', 1040)]]
        chunks = []
        for record in records:
            raw = json.dumps(record).encode()
            chunks.extend([raw[:60] + b'\n', raw[60:] + b'\n'])
        with tempfile.TemporaryDirectory() as parent:
            target = Path(parent) / 'run'
            receipt = capture.capture(chunks, target, mode='synthetic_fixture')
            raw = (target / 'diagnostics.jsonl').read_bytes()
            self.assertNotIn(b'SECRET-CANARY', raw)
            self.assertNotIn(b'login', raw)
            rows = [json.loads(line) for line in raw.splitlines()]
            samples = [r for r in rows if r['kind'] == 'sample']
            self.assertEqual([s['status'] for s in samples], ['blocked', 'duplicate', 'observed'])
            self.assertEqual(receipt['sample_count'], 3)
            self.assertEqual(receipt['gap_count'], 1)
            self.assertEqual(receipt['sha256'], hashlib.sha256(raw).hexdigest())
            self.assertFalse(receipt['completeness_verified'])
            with self.assertRaises(FileExistsError):
                capture.capture([], target, mode='synthetic_fixture')
            self.assertEqual((target / 'diagnostics.jsonl').read_bytes(), raw)

    def test_truncation_and_output_limit_remain_failed(self):
        with tempfile.TemporaryDirectory() as parent:
            receipt = capture.capture([b'{"mode":"signal-only"'], Path(parent)/'truncated', mode='synthetic_fixture')
            self.assertEqual(receipt['stop_reason'], 'incomplete_frame')
            receipt = capture.capture([b'x' * (capture.MAX_FRAME + 1)], Path(parent)/'large', mode='synthetic_fixture')
            self.assertEqual(receipt['stop_reason'], 'frame_limit')
            receipt = capture.capture([b'x'], Path(parent)/'limited', mode='synthetic_fixture', max_bytes=1)
            self.assertEqual(receipt['stop_reason'], 'output_limit')

    def test_timeout_and_source_failure_preserve_receipts(self):
        def stopped(error):
            yield b'SECRET-CANARY fatal last line\n'
            raise error
        with tempfile.TemporaryDirectory() as parent:
            for name, error, expected in [('timeout', TimeoutError(), 'timeout'),
                    ('failed', RuntimeError(), 'invalid_sample_or_source_failure')]:
                receipt = capture.capture(stopped(error), Path(parent)/name, mode='synthetic_fixture')
                self.assertEqual(receipt['stop_reason'], expected)
                self.assertEqual(receipt['observed_days'], 0)
                self.assertGreater(receipt['trailing_unparsed_bytes'], 0)
                self.assertEqual(receipt['trailing_unparsed_sha256'],
                    hashlib.sha256(b'SECRET-CANARY fatal last line\n').hexdigest())
                self.assertTrue((Path(parent)/name/'receipt.json').exists())

    def test_rejected_source_frames_are_not_erased(self):
        good = json.dumps({'mode': 'signal-only', 'symbol': 'XAUUSD-VIP',
            'status': 'blocked', 'signal': 'none', 'health': {'sampled_at': 1000}}).encode() + b'\n'
        with tempfile.TemporaryDirectory() as parent:
            for index, bad in enumerate((b'{"mode":"signal-only"}\n',
                    b'{"mode":"signal-only",BROKEN\n', b'SECRET-CANARY fatal log\n')):
                target = Path(parent) / str(index)
                receipt = capture.capture([bad, good], target, mode='synthetic_fixture')
                self.assertEqual(receipt['sample_count'], 1)
                self.assertGreater(receipt['rejected_frame_count'], 0)
                self.assertNotIn(b'SECRET-CANARY', (target/'diagnostics.jsonl').read_bytes())

    def test_log_source_cleanup_on_early_close(self):
        from unittest.mock import MagicMock
        process = MagicMock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('docker', 2), 0]
        with patch.object(capture.subprocess, 'Popen', return_value=process), \
                patch.object(capture.selectors, 'DefaultSelector') as selector, \
                patch.object(capture.os, 'read', return_value=b'line\n'):
            selector.return_value.__enter__.return_value.select.return_value = [True]
            stream = capture.docker_lines(1)
            self.assertEqual(next(stream), b'line\n')
            stream.close()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        process.stdout.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
