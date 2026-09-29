import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

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
