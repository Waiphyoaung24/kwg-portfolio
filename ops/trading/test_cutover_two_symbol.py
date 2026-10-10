import hashlib
import json
from pathlib import Path
import runpy
import tempfile
import time
import unittest
from unittest.mock import patch


class CutoverTwoSymbolTest(unittest.TestCase):
    def test_receipt_required_before_recreation_and_btc_starts_standby(self):
        module = runpy.run_path(str(Path(__file__).with_name('cutover-two-symbol-pilot.py')))
        deploy = module['deploy']
        for failure in (None, 'receipt', 'base'):
            receipt_ok = failure is None
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                stage = root/'two-symbol-review-test'
                stage.mkdir()
                original = 'services:\n  desktop:\n    environment:\n      MT5_RUN_MODE: pilot\n'
                (root/'compose.yml').write_text(original)
                (root/'status_server.py').write_text('old status')
                names = ('demo_pilot.py', 'control_server.py', 'status_server.py', 'cutover-m1-pilot.py')
                for name in names:
                    (stage/name).write_text(name)
                hashes = {n:hashlib.sha256((stage/n).read_bytes()).hexdigest() for n in names}
                (stage/'manifest.json').write_text(json.dumps(dict(code_sha256='reviewed', previous_image='old',
                    sources={'demo_pilot.py':hashes['demo_pilot.py']}, files=hashes)))
                calls = []
                def run(args, **kwargs):
                    calls.append(args)
                    if args[:2] == ['docker','inspect']:
                        return '[{"Image":"old"}]'
                    if args[:3] == ['docker', 'image', 'inspect']:
                        return 'wrong' if failure == 'base' else 'old'
                    if args[:2] == ['docker', 'build']:
                        base = next(c[3] for c in calls if c[:3] == ['docker', 'tag', 'old'])
                        self.assertTrue(base.startswith('kwg-mt5-desktop:two-symbol-base-'))
                        self.assertEqual((stage/'Dockerfile').read_text().splitlines()[0], 'FROM ' + base)
                    if 'config' in args:
                        return json.dumps({'services':{'desktop':{'image':'kwg-mt5-desktop:qualification', 'environment':{'MT5_RUN_MODE':'pilot'}}}})
                    if args[:2] == ['docker','run']:
                        return json.dumps({n:hashes[n] for n in ('demo_pilot.py','control_server.py')})
                    if 'script' in args:
                        return 'TWO_SYMBOL_MIGRATED '+json.dumps(dict(ends_at=999999, gold_pause='Paused by owner', btc_status='standby', order_sent=False)) if receipt_ok else 'missing'
                    if 'kwg-trading-status' in args:
                        return json.dumps([dict(symbol='XAUUSD-VIP', checked_at=time.time(), pilot=dict(ends_at=999999, reason='Paused by owner')),
                                           dict(symbol='BTCUSD', checked_at=time.time(), pilot=dict(status='standby'))])
                    return ''
                def stopped():
                    calls.append(['stop_runner'])
                    return '{}'
                with patch.dict(deploy.__globals__, ROOT=root, run=run), \
                        patch.object(module['runpy'], 'run_path', return_value={'stop_runner':stopped}):
                    if receipt_ok:
                        deploy(stage, 'reviewed')
                        self.assertIn('MT5_PILOT_SYMBOLS: "XAUUSD-VIP,BTCUSD"', (root/'compose.yml').read_text())
                    else:
                        with self.assertRaisesRegex(ValueError, 'Local base image identity mismatch' if failure == 'base' else 'Migration receipt missing'):
                            deploy(stage, 'reviewed')
                        self.assertEqual((root/'compose.yml').read_text(), original)
                self.assertEqual(any('up' in call for call in calls), receipt_ok)
                if failure == 'base':
                    self.assertNotIn(['stop_runner'], calls)
                    self.assertFalse(any('build' in c for c in calls))
                else:
                    self.assertLess(next(i for i,c in enumerate(calls) if 'build' in c), calls.index(['stop_runner']))


if __name__ == '__main__':
    unittest.main()
