from pathlib import Path
import runpy
import unittest

from test_demo_one_shot import fake_mt5, NOW

review = runpy.run_path(str(Path(__file__).with_name('review-btc-readiness.py')))['review']


class BtcReadinessTest(unittest.TestCase):
    def setUp(self):
        self.mt5 = fake_mt5(enabled=True)
        self.mt5.symbol_info.return_value.name = 'BTCUSD'
        self.mt5.symbol_info.return_value.trade_contract_size = 1.0
        self.mt5.copy_rates_from_pos.return_value = [dict(time=NOW-(250-i)*60,
            open=100, close=100, high=101, low=99) for i in range(250)]
        self.mt5.order_calc_profit.return_value = -.04

    def test_readiness_uses_btc_contract_and_never_sends_orders(self):
        result = review(self.mt5, 123, NOW, 0)
        self.assertEqual(result['symbol'], 'BTCUSD')
        self.assertEqual(result['contract']['trade_contract_size'], 1)
        self.assertEqual(result['candidate_spread_limit_price'], .5)
        self.assertEqual(result['minimum_lot_stop_risk_usd'], {'buy': .04, 'sell': .04})
        for call in self.mt5.order_calc_profit.call_args_list:
            self.assertEqual(call.args[1:3], ('BTCUSD', .01))
        self.mt5.order_send.assert_not_called()
        self.mt5.order_check.assert_not_called()

    def test_rejects_wrong_account_stale_tick_and_unknown_risk(self):
        self.mt5.account_info.return_value.login = 456
        with self.assertRaises(ValueError):
            review(self.mt5, 123, NOW, 0)
        self.mt5.account_info.return_value.login = 123
        with self.assertRaises(ValueError):
            review(self.mt5, 123, NOW+60, 0)
        self.mt5.order_calc_profit.return_value = None
        with self.assertRaisesRegex(ValueError, 'risk calculation unavailable'):
            review(self.mt5, 123, NOW, 0)
        self.mt5.order_send.assert_not_called()

    def test_history_timing_failure_reports_evidence_without_calculating_risk(self):
        original = self.mt5.copy_rates_from_pos.return_value
        for shift in (-60, 10800):
            self.mt5.copy_rates_from_pos.return_value = [{**bar, 'time': bar['time']+shift} for bar in original]
            result = review(self.mt5, 123, NOW, 0)
            self.assertFalse(result['candidate_market_gate_passed'])
            self.assertEqual(result['bar_time']-result['expected_bar_time'], shift)
            self.assertEqual(result['previous_bar_gap_seconds'], 60)
            self.assertEqual(result['market_reason'], 'Latest completed candle is stale or future')
            self.assertNotIn('minimum_lot_stop_risk_usd', result)
        self.mt5.order_calc_profit.assert_not_called()
        self.mt5.order_send.assert_not_called()

    def test_compares_native_timeframes_at_the_same_spread_threshold(self):
        self.mt5.TIMEFRAME_M5 = 5
        self.mt5.TIMEFRAME_M15 = 15
        self.mt5.symbol_info_tick.return_value.ask = 101
        for name, seconds, width, passed in [('M1', 60, 1, False), ('M5', 300, 2, True), ('M15', 900, 3, True)]:
            with self.subTest(timeframe=name):
                end = NOW // seconds * seconds
                self.mt5.copy_rates_from_pos.return_value = [dict(time=end-(250-i)*seconds,
                    open=100, close=100, high=100+width, low=100-width) for i in range(250)]
                result = review(self.mt5, 123, NOW, 0, name)
                self.assertEqual(result['atr14'], width * 2)
                self.assertEqual(result['candidate_market_gate_passed'], passed)
                self.assertTrue(result['minimum_lot_risk_passed'])
                self.mt5.copy_rates_from_pos.assert_called_with('BTCUSD', getattr(self.mt5, 'TIMEFRAME_' + name), 1, 250)
                self.mt5.copy_rates_from_pos.return_value[-1]['time'] -= seconds
                with self.assertRaisesRegex(ValueError, 'unordered'):
                    review(self.mt5, 123, NOW, 0, name)
        self.mt5.order_send.assert_not_called()
        self.mt5.order_check.assert_not_called()

    def test_m5_clock_offset_and_stale_history(self):
        self.mt5.TIMEFRAME_M5 = 5
        self.mt5.symbol_info_tick.return_value.time = NOW + 10800
        self.mt5.symbol_info_tick.return_value.time_msc = (NOW + 10800) * 1000
        self.mt5.copy_rates_from_pos.return_value = [dict(time=NOW+10800-(250-i)*300,
            open=100, close=100, high=101, low=99) for i in range(250)]
        result = review(self.mt5, 123, NOW, 10800, 'M5')
        self.assertEqual(result['bar_time'], result['expected_bar_time'])
        for bar in self.mt5.copy_rates_from_pos.return_value:
            bar['time'] -= 300
        result = review(self.mt5, 123, NOW, 10800, 'M5')
        self.assertFalse(result['candidate_market_gate_passed'])
        self.assertNotIn('minimum_lot_stop_risk_usd', result)
