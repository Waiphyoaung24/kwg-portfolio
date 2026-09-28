import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

path = Path(__file__).with_name('verify-demo.py')
spec = importlib.util.spec_from_file_location('verify_demo', path)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class CollectorTest(unittest.TestCase):
    def test_finite_collection_and_no_account_identifier(self):
        sdk = SimpleNamespace(__version__='test', order_send=None,
                              symbol_info=lambda symbol: SimpleNamespace(name=symbol, secret='hidden'))
        calls = [0]
        def sample(mt5, login, now, health, *, server_offset_seconds=0):
            i = calls[0]
            calls[0] += 1
            stamp = 90900 + i * 5
            health.update(sampled_at=stamp, tick_time_msc=(stamp - 1) * 1000,
                          quote_age_seconds=1, quote='fresh', terminal='connected',
                          history_valid=True, history_count=250,
                          history_bar_time=(stamp // 900) * 900 - 900, spread_price=.2)
        with patch.object(verifier, 'read_gold', side_effect=sample), \
             patch.object(verifier.time, 'sleep'), \
             patch.object(verifier.time, 'monotonic', side_effect=lambda: calls[0] * 5):
            report = verifier.collect(sdk, 1234567, 3600, 10800)
        self.assertEqual(report['data_status'], 'passed')
        self.assertEqual(report['accepted_sample_count'], 361)
        self.assertNotIn('1234567', json.dumps(report))
        self.assertEqual(report['cost_status'], 'incomplete')
        self.assertEqual(report['server_offset_seconds'], 10800)
        self.assertEqual(report['contract']['name'], 'XAUUSD-VIP')
        self.assertNotIn('hidden', json.dumps(report))

    def test_interruption_keeps_partial_report_inconclusive(self):
        sdk = SimpleNamespace(__version__='test')
        with patch.object(verifier, 'read_gold', side_effect=KeyboardInterrupt):
            report = verifier.collect(sdk, 123, 60)
        self.assertEqual(report['data_status'], 'inconclusive')
        self.assertEqual(report['samples'], [])


if __name__ == '__main__':
    unittest.main()
