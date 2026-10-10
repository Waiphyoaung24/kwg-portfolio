from pathlib import Path
import runpy
import unittest

from test_demo_one_shot import fake_mt5, NOW

review = runpy.run_path(str(Path(__file__).with_name('review-entry-readiness.py')))['review']


class ReadinessTest(unittest.TestCase):
    def test_trend_and_spread_are_reported_without_order_calls(self):
        mt5 = fake_mt5(enabled=True)
        mt5.copy_rates_from_pos.return_value = [dict(time=NOW-(250-i)*60,
            open=90+i*.04, close=90+i*.04, high=91+i*.04, low=89+i*.04) for i in range(250)]
        value = review(mt5, 123, NOW, 0)
        self.assertEqual(value['trend_direction'], 'long')
        self.assertTrue(value['trend_slope_passed'])
        self.assertEqual(value['crossover_signal'], 'none')
        self.assertTrue(value['market_gate_passed'])
        self.assertAlmostEqual(value['spread_limit_price'], .2)
        mt5.symbol_info_tick.return_value.ask = 100.3
        value = review(mt5, 123, NOW, 0)
        self.assertFalse(value['market_gate_passed'])
        self.assertAlmostEqual(value['spread_atr_ratio'], .15)
        self.assertFalse(value['order_sent'])
        mt5.order_send.assert_not_called()
        mt5.order_check.assert_not_called()


if __name__ == '__main__':
    unittest.main()
