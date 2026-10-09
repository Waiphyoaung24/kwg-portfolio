import ast
import hashlib
import json
from pathlib import Path
import runpy
import pathlib
import tempfile
import unittest
from unittest.mock import patch


class CutoverM1Test(unittest.TestCase):
    def test_trend_wrapper_pins_reviewed_stage_and_explicit_migration(self):
        wrapper = runpy.run_path(str(Path(__file__).with_name('cutover-trend-pilot.py')))
        namespace = {}
        exec("def main():\n    globals()['called'] = True", namespace)
        calls = []
        def run(args):
            calls.append(args)
            return 'sha256:built-trend-image'
        shared = dict(main=namespace['main'], ROOT=Path('/opt/kwg-mt5-qualification'), run=run)
        with patch.object(wrapper['runpy'], 'run_path', return_value=shared), patch('sys.argv', ['cutover', '--enable-demo-execution']):
            wrapper['main']()
        self.assertTrue(namespace['called'])
        self.assertEqual(namespace['MIGRATION_FLAGS'], ' --trend')
        self.assertEqual(namespace['TARGET_STRATEGY'], 'gold-ema-v1-m1-trend-3')
        self.assertEqual(namespace['CODE'], 'c1a2c965fc1bba6c7834d25c1977e79418208491874d9c7e6509c56e94da165b')
        self.assertEqual(namespace['STAGE'].name, 'm1-review-20261009T141607Z-69e01b51')
        self.assertEqual(namespace['IMAGE'], 'sha256:built-trend-image')
        self.assertEqual(len(calls), 1)
        with patch('sys.argv', ['cutover']), self.assertRaises(SystemExit):
            wrapper['main']()

    def test_runner_detection_handles_wine_null_padding_without_matching_shells(self):
        tree = ast.parse(Path(__file__).with_name('cutover-m1-pilot.py').read_text())
        stop = next(ast.literal_eval(node.value) for node in ast.walk(tree)
                    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'stop' for t in node.targets))
        function = next(node for node in ast.parse(stop).body if isinstance(node, ast.FunctionDef) and node.name == 'args')
        namespace = {'pathlib': pathlib}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'runner-parser', 'exec'), namespace)
        expected = [b'/opt/trading/demo_pilot.py', b'run']
        cases = [
            (b'/opt/python/python.exe\0/opt/trading/demo_pilot.py\0run' + b'\0' * 24, True),
            (b'/opt/python/python.exe\0/opt/trading/demo_pilot.py\0run\0', True),
            (b'sh\0-c\0wine /opt/python/python.exe /opt/trading/demo_pilot.py run\0', False),
            (b'script\0-q\0-e\0-c\0wine /opt/python/python.exe /opt/trading/demo_pilot.py run\0/dev/null\0', False),
        ]
        for raw, matches in cases:
            with self.subTest(raw=raw), patch.object(Path, 'read_bytes', return_value=raw):
                self.assertEqual(namespace['args'](282)[-2:] == expected, matches)

    def test_cutover_order_and_fail_closed_receipt(self):
        module = runpy.run_path(str(Path(__file__).with_name('cutover-m1-pilot.py')))
        main = module['main']
        for receipt_ok in (True, False):
            with self.subTest(receipt_ok=receipt_ok), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                stage = root / 'stage'
                stage.mkdir()
                for name in ('compose.yml', 'status_server.py'):
                    (root / name).write_text('old')
                (stage / 'status_server.py').write_text('new')
                (stage / 'demo_pilot.py').write_bytes(b'source')
                hashes = {'demo_pilot.py': hashlib.sha256(b'source').hexdigest()}
                (stage / 'manifest.json').write_text(json.dumps(dict(code_sha256=module['CODE'], sources=hashes)))
                calls = []
                def run(args, **kwargs):
                    calls.append(args)
                    if args[:3] == ['docker', 'inspect', 'kwg-mt5-desktop']:
                        return module['IMAGE'] if '--format' in args else json.dumps([{'Image': module['OLD_IMAGE']}])
                    if 'config' in args:
                        return json.dumps({'services': {'desktop': {'image': 'kwg-mt5-desktop:qualification', 'environment': {'MT5_RUN_MODE': 'pilot'}}}})
                    if args[:3] == ['docker', 'image', 'inspect']:
                        return module['IMAGE']
                    if args[:2] == ['docker', 'run']:
                        return json.dumps(hashes)
                    if 'python3' in args and args[:2] == ['docker', 'exec']:
                        compile(args[-1], 'stop-runner', 'exec')
                        return '{"supervisor":20,"runner":24}'
                    if 'script' in args:
                        return 'M1_SWITCH_SAVED {}' if receipt_ok else 'unexpected output'
                    if 'kwg-trading-status' in args:
                        return json.dumps({'pilot': {'strategy': 'gold-ema-v1-m1-slope-3', 'updated_at': module['time'].time(), 'ends_at': 1792096151}})
                    return ''
                with patch.dict(main.__globals__, ROOT=root, STAGE=stage, run=run), patch('sys.argv', ['cutover', '--enable-demo-execution']):
                    if receipt_ok:
                        main()
                        self.assertEqual((root / 'status_server.py').read_text(), 'new')
                        migration = next(i for i, c in enumerate(calls) if 'script' in c)
                        recreate = next(i for i, c in enumerate(calls) if '--force-recreate' in c)
                        self.assertLess(migration, recreate)
                    else:
                        with self.assertRaisesRegex(AssertionError, 'receipt missing'):
                            main()
                        self.assertEqual((root / 'status_server.py').read_text(), 'old')
                        self.assertFalse(any('--force-recreate' in c for c in calls))


if __name__ == '__main__':
    unittest.main()
