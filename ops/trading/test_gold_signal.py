import math
import unittest

from gold_signal import atr, ema, evaluate


def bars(last_close=100):
    return [dict(time=(i + 1) * 900, open=100, high=101, low=99,
                 close=last_close if i == 249 else 100) for i in range(250)]


NOW = 251 * 900


class GoldSignalTest(unittest.TestCase):
    def test_indicator_seeds(self):
        self.assertEqual(ema([1, 2, 3, 4], 3), [None, None, 2, 3])
        self.assertEqual(atr(bars())[14], 2)
        self.assertEqual(atr(bars())[-1], 2)

    def test_cross_and_spread(self):
        self.assertEqual(evaluate(bars(), 100, 100.2, NOW)["signal"], "none")
        self.assertEqual(evaluate(bars(101), 100, 100.2, NOW)["signal"], "long")
        self.assertEqual(evaluate(bars(99), 100, 100.2, NOW)["signal"], "short")
        self.assertEqual(evaluate(bars(101), 100, 100.2001, NOW)["signal"], "blocked")

    def test_bad_history_never_signals(self):
        cases = []
        cases.append(bars()[:249])
        for key, value in (("close", math.nan), ("high", 98), ("low", 102), ("time", 249 * 900)):
            sample = bars(101)
            sample[-1][key] = value
            cases.append(sample)
        for sample in cases:
            with self.subTest(sample=sample[-1]), self.assertRaises(ValueError):
                evaluate(sample, 100, 100.1, NOW)
        self.assertEqual(evaluate(bars(101), 100, 100.1, NOW + 900)["signal"], "blocked")
        self.assertEqual(evaluate(bars(101), 100, 100.1, NOW - 900)["signal"], "blocked")
        sample = bars(101)
        sample[10]["time"] -= 900
        with self.assertRaises(ValueError):
            evaluate(sample, 100, 100.1, NOW)


if __name__ == "__main__":
    unittest.main()
