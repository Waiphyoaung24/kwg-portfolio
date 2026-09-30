import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import hashlib
import io
import json
import sys
import tempfile
from unittest.mock import Mock, patch

from mt5_data import AccountGuardError, SERVER, SYMBOL

spec = importlib.util.spec_from_file_location('batch2_evidence', Path(__file__).with_name('batch2-evidence.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ReadOnlyMT5:
    # Deliberately offers no order_send, order_check, login or symbol_select.
    def account_info(self):
        return NS(login=123, server=SERVER, trade_mode=0, password='never publish')

    def terminal_info(self):
        return NS(connected=True, trade_allowed=True)

    def positions_get(self, *, symbol):
        assert symbol == SYMBOL
        return ()

    def orders_get(self, *, symbol):
        assert symbol == SYMBOL
        return (NS(ticket=999),)

    def symbol_info(self, symbol):
        assert symbol == SYMBOL
        return NS(name=SYMBOL, point=.01, swap_mode=1, swap_long=-79.48, swap_short=34.41)

    def symbol_info_tick(self, symbol):
        assert symbol == SYMBOL
        return NS(time=11800, time_msc=11800000, bid=4150., ask=4150.27)


class EvidenceTest(unittest.TestCase):
    def test_saved_evidence_hash_matches_bytes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.json'
            digest = probe.save_evidence(path, {'status': 'unqualified', 'value': 1})
            original = path.read_bytes()
            self.assertEqual(digest, hashlib.sha256(original).hexdigest())
            self.assertTrue(original.endswith(b'\n'))
            with self.assertRaises(FileExistsError):
                probe.save_evidence(path, {'value': 2})
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_json_never_creates_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.json'
            with self.assertRaises(ValueError):
                probe.save_evidence(path, {'value': float('nan')})
            self.assertFalse(path.exists())

    def run_cli(self, path=None, *, sdk=None, now=1000.2, output=None):
        sdk = sdk or ReadOnlyMT5()
        sdk.initialize = Mock(return_value=True)
        sdk.shutdown = Mock()
        sdk.__version__ = 'test'
        args = ['batch2-evidence.py', '--login', '123', '--server-offset-seconds', '10800']
        if path is not None:
            args += ['--output', str(path)]
        output = output if output is not None else io.StringIO()
        with patch.dict(sys.modules, {'MetaTrader5': sdk}), patch.object(sys, 'argv', args), \
                patch.object(probe.time, 'sleep'), patch.object(probe.time, 'time', return_value=now), \
                patch('sys.stdout', output):
            probe.main()
        return json.loads(output.getvalue())

    def test_cli_saved_summary_matches_complete_capture_and_keeps_stale_quotes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.json'
            result = self.run_cli(path, now=1100)
            saved = json.loads(path.read_bytes())
            self.assertEqual(len(saved['samples']), 3)
            self.assertTrue(all(sample['quote']['quote'] == 'stale' for sample in saved['samples']))
            self.assertEqual(result, {'mode': 'batch2-read-only-evidence', 'cost_status': 'incomplete',
                                     'timestamp_status': 'current_spot_checks_only',
                                     'output_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

    def test_cli_failed_capture_or_write_never_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture.json'
            sdk = ReadOnlyMT5()
            sdk.orders_get = lambda **kwargs: None
            with self.assertRaisesRegex(SystemExit, 'Evidence capture refused'):
                self.run_cli(path, sdk=sdk)
            self.assertFalse(path.exists())
            output = io.StringIO()
            with patch.object(probe, 'save_evidence', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(SystemExit, 'disk full'):
                    self.run_cli(path, output=output)
                self.assertEqual(output.getvalue(), '')

    def test_cli_without_output_preserves_samples(self):
        result = self.run_cli()
        self.assertEqual(len(result['samples']), 3)
        self.assertEqual(result['cost_status'], 'incomplete')
        self.assertNotIn('output_sha256', result)

    def test_pending_algo_on_is_inspected_without_execution_or_secrets(self):
        result = probe.capture(ReadOnlyMT5(), 123, 1000.2, 10800)
        self.assertEqual(result['gold_pending_orders'], 1)
        self.assertEqual(result['gold_positions'], 0)
        self.assertTrue(result['algo_trading_on'])
        self.assertEqual(result['quote']['quote'], 'fresh')
        self.assertIsNone(result['contract_current_only']['commission'])
        self.assertNotIn('ticket', str(result))
        self.assertNotIn('password', str(result))
        self.assertNotIn('login', str(result))

    def test_unknown_order_query_cannot_be_reported_empty(self):
        mt5 = ReadOnlyMT5()
        mt5.orders_get = lambda **kwargs: None
        with self.assertRaisesRegex(ValueError, 'unknown is not empty'):
            probe.capture(mt5, 123, 1000.2, 10800)

    def test_wrong_account_refused_even_when_algo_is_on(self):
        with self.assertRaises(AccountGuardError):
            probe.capture(ReadOnlyMT5(), 124, 1000.2, 10800)


if __name__ == '__main__':
    unittest.main()
