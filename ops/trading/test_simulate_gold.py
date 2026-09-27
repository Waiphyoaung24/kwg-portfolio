import copy
from pathlib import Path
import runpy
import unittest

sim = runpy.run_path(str(Path(__file__).with_name('simulate-gold.py')))
SPEC = dict(point=.01, trade_contract_size=100, trade_tick_size=.01,
            volume_min=.01, volume_max=100, volume_step=.01, currency_profit='USD')
FREE = dict(commission=0, slippage=0, overnight=0, spread_multiplier=1)


def bars():
    return [dict(time=(i + 1) * 900, open=100, high=100.5, low=99.5, close=100, spread=0)
            for i in range(5)]


class SimulationTest(unittest.TestCase):
    def test_stops_targets_short_ask_and_gaps(self):
        exit_at = sim['protective_exit']
        pos = dict(side=1, stop=98, target=103)
        both = dict(open=100, high=104, low=97)
        self.assertEqual(exit_at(pos, both, .1), (98, 'stop_both_touched'))
        self.assertEqual(exit_at(pos, {**both, 'open': 95}, .1), (95, 'gap_stop'))
        short = dict(side=-1, stop=102, target=97)
        self.assertEqual(exit_at(short, dict(open=100, high=101.9, low=99), .2), (102, 'stop'))
        self.assertEqual(exit_at(short, dict(open=100, high=101, low=96), .2), (97, 'target'))

    def test_entry_after_signal_risk_costs_and_opposite_no_reversal(self):
        sample = bars()
        signals = {1800: dict(signal='long', bar_time=1800, atr14=1),
                   2700: dict(signal='short', bar_time=2700, atr14=1)}
        result = sim['simulate'](sample, signals, SPEC, FREE)
        self.assertEqual(len(result['trades']), 1)
        trade = result['trades'][0]
        self.assertEqual((trade['signal_bar'], trade['entry_bar'], trade['exit_bar']), (1800, 2700, 3600))
        self.assertEqual(trade['exit_reason'], 'opposite_signal')
        self.assertLessEqual(trade['lots'] * 201, 100)
        self.assertEqual(trade['net_pnl'], 0)
        costs = dict(commission=7, slippage=.1, overnight=15, spread_multiplier=1)
        paid = sim['simulate'](sample, signals, SPEC, costs)
        self.assertLess(paid['summary']['net_pnl_usd'], 0)
        self.assertAlmostEqual(paid['summary']['net_pnl_usd'], sum(t['net_pnl'] for t in paid['trades']))
        self.assertEqual(paid, sim['simulate'](sample, signals, SPEC, costs))
        tiny = sim['simulate'](sample, signals, SPEC, FREE, initial=1)
        self.assertEqual(tiny['summary']['trades'], 0)

    def test_overnight_gap_cancel_and_window_close(self):
        sample = bars()
        for i, b in enumerate(sample): b['time'] = 84600 + i * 900
        signals = {85500: dict(signal='long', bar_time=85500, atr14=1)}
        sample[-1]['time'] += 86400
        result = sim['simulate'](sample, signals, SPEC, {**FREE, 'overnight': 10})
        trade = result['trades'][0]
        self.assertEqual(trade['exit_reason'], 'window_end')
        self.assertAlmostEqual(trade['net_pnl'], -10 * trade['lots'])
        gapped = bars()
        gapped[2]['time'] += 900
        result = sim['simulate'](gapped[:3], {1800: dict(signal='long', bar_time=1800, atr14=1)}, SPEC, FREE)
        self.assertEqual(result['summary']['skips']['gap_entry_cancelled'], 1)

    def test_holdout_never_changes_results_and_validation_resets(self):
        sample = [dict(time=(i + 1) * 900, open=100, high=101, low=99, close=100, spread=1) for i in range(1000)]
        data = dict(schema_version=1, symbol='XAUUSD-VIP', timeframe='M15', source={'start_pos': 1},
                    captured_at=1001 * 900, current_contract_specification=SPEC, bars=sample)
        result = sim['run'](data)
        changed = copy.deepcopy(data)
        changed['bars'][800:] = [{'unread_holdout': True}] * 200
        self.assertEqual(result, sim['run'](changed))
        self.assertFalse(result['holdout']['evaluated'])
        self.assertEqual(result['runs']['middle']['windows']['validation']['first_bar'], 601 * 900)

    def test_daily_pause_after_cost_and_adverse_gap(self):
        sample = bars()
        for i, b in enumerate(sample): b['time'] = 82800 + i * 900
        sample[-1].update(open=95, high=95.5, low=94.5, close=95)
        signals = {83700: dict(signal='long', bar_time=83700, atr14=1),
                   85500: dict(signal='short', bar_time=85500, atr14=1)}
        result = sim['simulate'](sample, signals, SPEC, {**FREE, 'overnight': 10000})
        self.assertEqual(len(result['trades']), 1)
        self.assertEqual(result['trades'][0]['exit_reason'], 'gap_stop')
        self.assertEqual(result['summary']['skips']['daily_pause_rejected'], 1)


if __name__ == '__main__':
    unittest.main()
