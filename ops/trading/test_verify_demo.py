import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from mt5_data import read_gold, validate_account, validate_tick


class GoldDataTest(unittest.TestCase):
    def test_account_guard(self):
        account = dict(trade_mode=0, login=123, server="VTMarkets-Demo")
        terminal = dict(connected=True, trade_allowed=False)
        validate_account(SimpleNamespace(**account), SimpleNamespace(**terminal), 123, "VTMarkets-Demo")
        for field, value in (("trade_mode", 2), ("login", 456), ("server", "other")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_account(SimpleNamespace(**(account | {field: value})), SimpleNamespace(**terminal), 123, "VTMarkets-Demo")
        for field, value in (("connected", False), ("trade_allowed", True)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_account(SimpleNamespace(**account), SimpleNamespace(**(terminal | {field: value})), 123, "VTMarkets-Demo")

    def test_tick_age_and_prices(self):
        tick = SimpleNamespace(bid=100, ask=101, time=1000, time_msc=0)
        self.assertEqual(validate_tick(tick, 1000), 0)
        self.assertEqual(validate_tick(tick, 1030), 30)
        for now in (999.999, 1030.001):
            with self.assertRaises(ValueError):
                validate_tick(tick, now)
        for bid, ask in ((0, 101), (math.nan, 101), (100, math.inf), (102, 101)):
            with self.subTest(bid=bid, ask=ask), self.assertRaises(ValueError):
                validate_tick(SimpleNamespace(bid=bid, ask=ask, time=1000, time_msc=0), 1000)
        self.assertEqual(validate_tick(SimpleNamespace(bid=100, ask=101, time=0, time_msc=1000500), 1001), .5)

    def test_read_gold_exact_request_and_fail_closed(self):
        sdk = Mock(TIMEFRAME_M15=15)
        sdk.account_info.return_value = SimpleNamespace(trade_mode=0, login=123, server="VTMarkets-Demo")
        sdk.terminal_info.return_value = SimpleNamespace(connected=True, trade_allowed=False)
        sdk.symbol_select.return_value = True
        sdk.symbol_info.return_value = SimpleNamespace(point=.01)
        sdk.symbol_info_tick.return_value = SimpleNamespace(bid=100, ask=100.1, time=251 * 900, time_msc=0)
        sdk.copy_rates_from_pos.return_value = [dict(time=(i + 1) * 900, open=100, high=101, low=99, close=100) for i in range(250)]
        tick, bars = read_gold(sdk, 123, 251 * 900)
        self.assertEqual((tick.bid, len(bars)), (100, 250))
        sdk.copy_rates_from_pos.assert_called_once_with("XAUUSD-VIP", 15, 1, 250)
        sdk.account_info.return_value.trade_mode = 2
        with self.assertRaises(ValueError):
            read_gold(sdk, 123, 251 * 900)

        sdk.account_info.return_value.trade_mode = 0
        sdk.terminal_info.return_value.connected = False
        with self.assertRaises(ValueError):
            read_gold(sdk, 123, 251 * 900)
        sdk.terminal_info.return_value.connected = True
        sdk.symbol_info_tick.return_value = None
        with self.assertRaises(ValueError):
            read_gold(sdk, 123, 251 * 900)
        sdk.symbol_info_tick.return_value = tick
        sdk.copy_rates_from_pos.return_value = [{}] * 249
        with self.assertRaises(ValueError):
            read_gold(sdk, 123, 251 * 900)


    def test_quote_failures_keep_timestamp_evidence(self):
        for now, state, age in ((1031, "stale", 30.5), (999, "future", -1.5), (1001, "fresh", .5)):
            with self.subTest(state=state):
                evidence = {}
                tick = SimpleNamespace(bid=100, ask=101, time=1000, time_msc=1000500)
                if state == "fresh":
                    validate_tick(tick, now, evidence)
                else:
                    with self.assertRaises(ValueError):
                        validate_tick(tick, now, evidence)
                self.assertEqual(evidence, dict(quote=state, sampled_at=now,
                    tick_time=1000, tick_time_msc=1000500, quote_age_seconds=age))

    def test_read_gold_records_spread_and_rejects_bad_history(self):
        sdk = Mock(TIMEFRAME_M15=15)
        sdk.account_info.return_value = SimpleNamespace(trade_mode=0, login=123, server="VTMarkets-Demo")
        sdk.terminal_info.return_value = SimpleNamespace(connected=True, trade_allowed=False)
        sdk.symbol_select.return_value = True
        sdk.symbol_info.return_value = SimpleNamespace(point=.01)
        sdk.symbol_info_tick.return_value = SimpleNamespace(bid=100, ask=100.2, time=251 * 900, time_msc=0)
        sdk.copy_rates_from_pos.return_value = [dict(time=(i + 1) * 900, open=100,
            high=101, low=99, close=100) for i in range(250)]
        health = {}
        read_gold(sdk, 123, 251 * 900, health)
        self.assertAlmostEqual(health['spread_price'], .2)
        self.assertAlmostEqual(health['spread_points'], 20)
        self.assertTrue(health['history_valid'])
        self.assertEqual(health['strategy_signal'], 'none')
        sdk.copy_rates_from_pos.return_value[-1]['time'] -= 900
        with self.assertRaises(ValueError):
            read_gold(sdk, 123, 251 * 900, health)
        self.assertEqual(health['quote'], 'fresh')
        self.assertFalse(health['history_valid'])
        self.assertNotEqual(health['strategy_signal'], 'none')
        sdk.order_send.assert_not_called()

    def test_bad_point_cannot_fabricate_spread_points(self):
        sdk = Mock(TIMEFRAME_M15=15)
        sdk.account_info.return_value = SimpleNamespace(trade_mode=0, login=123, server="VTMarkets-Demo")
        sdk.terminal_info.return_value = SimpleNamespace(connected=True, trade_allowed=False)
        sdk.symbol_select.return_value = True
        sdk.symbol_info.return_value = SimpleNamespace(point=0)
        sdk.symbol_info_tick.return_value = SimpleNamespace(bid=100, ask=100.2, time=251 * 900, time_msc=0)
        sdk.copy_rates_from_pos.return_value = [dict(time=(i + 1) * 900, open=100,
            high=101, low=99, close=100) for i in range(250)]
        health = {}
        with self.assertRaises(ValueError):
            read_gold(sdk, 123, 251 * 900, health)
        self.assertIsNone(health['spread_points'])


if __name__ == "__main__":
    unittest.main()
