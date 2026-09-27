import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('replay_gold', Path(__file__).with_name('replay-gold.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReplayTest(unittest.TestCase):
    def test_known_signals_gaps_and_no_lookahead(self):
        bars = [dict(time=(i + 1) * 900, open=100, high=101, low=99, close=100, spread=10)
                for i in range(253)]
        bars[250]['close'] = 101
        bars[251]['close'] = 99
        data = dict(schema_version=1, symbol='XAUUSD-VIP', timeframe='M15', source={'start_pos': 1},
                    captured_at=300 * 900, current_contract_specification={'point': .01}, bars=bars)
        first = module.replay(data)
        self.assertEqual([d['signal'] for d in first['decisions']][:3], ['none', 'long', 'short'])
        self.assertEqual(module.replay(data), first)
        later = copy.deepcopy(data)
        later['bars'][-1]['close'] = 99
        self.assertEqual(module.replay(later)['decisions'][:-1], first['decisions'][:-1])
        gapped = copy.deepcopy(data)
        for bar in gapped['bars'][250:]:
            bar['time'] += 900
        self.assertEqual(module.replay(gapped)['counts']['blocked'], 1)
        self.assertEqual(module.replay(gapped)['counts']['baseline_reset'], 2)
        for mutate in ('future', 'spread', 'ohlc'):
            invalid = copy.deepcopy(data)
            if mutate == 'future': invalid['captured_at'] = 252 * 900
            elif mutate == 'spread': invalid['bars'][0]['spread'] = -1
            else: invalid['bars'][0]['high'] = 98
            with self.assertRaises(ValueError): module.replay(invalid)


if __name__ == '__main__':
    unittest.main()
