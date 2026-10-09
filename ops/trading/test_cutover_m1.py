import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch


class CutoverM1Test(unittest.TestCase):
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
