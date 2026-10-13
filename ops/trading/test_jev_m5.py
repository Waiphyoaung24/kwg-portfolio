import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import jev_m5


def bars(n=250, start=300, close=lambda i: 100 + i * .01):
    return [dict(time=start + i * 300, open=close(i) - .005, high=close(i) + .02,
                 low=close(i) - .02, close=close(i)) for i in range(n)]


def receipt(choice='buy', confidence=.8, status='ok', completed=930, **extra):
    probabilities = {'buy': .1, 'hold': .1, 'sell': .1}
    probabilities[choice] = .8
    return {**dict(bar_time=600, input_sha256='a' * 64, model=jev_m5.MODEL,
                   question_sha256=jev_m5.QUESTION_SHA256, status=status, choice=choice,
                   confidence=confidence, probabilities=probabilities, completed_at=completed), **extra}


class FeatureTest(unittest.TestCase):
    def test_features_are_categorical_and_deterministic(self):
        b = bars()
        indicators = dict(ema20=102.4, ema50=102.2, atr14=.05)
        stamp = b[-1]['time']
        state = jev_m5.state(b, 102.48, 102.49, indicators, captured_at=stamp + 302)
        self.assertEqual(state['features']['trend'], 'up')
        self.assertIn(state['features']['session'], {'asia', 'london', 'new_york', 'overlap'})
        self.assertEqual(len(state['bars']), 50)
        self.assertNotIn('side', state)            # code side never shown to Jev
        self.assertNotIn('account', state)
        again = jev_m5.state(b, 102.48, 102.49, indicators, captured_at=stamp + 302)
        self.assertEqual(jev_m5.input_sha256(state), jev_m5.input_sha256(again))

    def test_rejects_non_m5_or_short_history(self):
        with self.assertRaises(ValueError):
            jev_m5.state(bars(49), 1, 1.1, dict(ema20=1, ema50=1, atr14=1), captured_at=10**9)
        bad = bars()
        bad[-1]['time'] += 60
        with self.assertRaises(ValueError):
            jev_m5.state(bad, 1, 1.1, dict(ema20=1, ema50=1, atr14=1), captured_at=10**9)

    def test_rejects_float_times_and_non_finite_prices(self):
        indicators = dict(ema20=102.4, ema50=102.2, atr14=.05)
        for key, value in (('time', 300.0 + 249 * 300), ('close', math.nan), ('high', None)):
            sample = bars()
            sample[-1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                jev_m5.state(sample, 102.48, 102.49, indicators, captured_at=10**9)


class VetoRuleTest(unittest.TestCase):
    def test_frozen_rule_table(self):
        allow = lambda r, side='long': jev_m5.allows(r, side=side, bar_time=600,
                                                     input_sha256='a' * 64, now=930)
        self.assertEqual(allow(receipt('buy')), (True, 'Jev agreed'))
        self.assertEqual(allow(receipt('sell'), 'short'), (True, 'Jev agreed'))
        self.assertFalse(allow(receipt('hold'))[0])
        self.assertFalse(allow(receipt('sell'))[0])
        self.assertFalse(allow(receipt('buy', confidence=.49))[0])
        self.assertEqual(allow(receipt(status='timeout', choice=None, confidence=None, probabilities=None)),
                         (False, 'Jev timeout'))
        self.assertFalse(allow(None)[0])
        self.assertFalse(allow(receipt(completed=600 + 300 + 91))[0])  # after T+90 s
        self.assertFalse(jev_m5.allows(receipt(), side='long', bar_time=600,
                                       input_sha256='b' * 64, now=930)[0])
        self.assertFalse(jev_m5.allows(receipt(), side='long', bar_time=600,
                                       input_sha256='a' * 64, now=600 + 300 + 91)[0])

    def test_validate_rejects_malformed(self):
        for mutate in (lambda r: r.update(model='jev-latest'),
                       lambda r: r.update(question_sha256='0' * 64),
                       lambda r: r['probabilities'].update(buy=.9),
                       lambda r: r.update(confidence=math.nan),
                       lambda r: r.update(choice='review_setup'),
                       lambda r: r.update(extra='x')):
            value = receipt()
            mutate(value)
            with self.assertRaises(ValueError):
                jev_m5.validate_receipt(value)
        self.assertEqual(jev_m5.validate_receipt(receipt(status='timeout', choice=None,
            confidence=None, probabilities=None))['status'], 'timeout')


    def test_validate_bounds_times_and_requires_lowercase_hex_digest(self):
        for changes in ({'bar_time': 0}, {'bar_time': -300}, {'bar_time': 300 * (2 ** 53 // 300 + 1)},
                        {'completed_at': 0}, {'completed_at': -1}, {'completed_at': 2 ** 53},
                        {'completed_at': 2.0 ** 53}, {'input_sha256': 'A' * 64}, {'input_sha256': 'g' * 64}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                jev_m5.validate_receipt(receipt(**changes))
        self.assertEqual(jev_m5.validate_receipt(receipt(input_sha256='0123456789abcdef' * 4))['bar_time'], 600)

    def test_boundaries_and_fail_closed_inputs(self):
        allow = lambda r, side='long', bar_time=600, now=930: jev_m5.allows(
            r, side=side, bar_time=bar_time, input_sha256='a' * 64, now=now)
        self.assertEqual(allow(receipt(confidence=.5)), (True, 'Jev agreed'))
        self.assertEqual(allow(receipt(completed=600 + 390), now=600 + 390), (True, 'Jev agreed'))
        self.assertEqual(allow(receipt(), bar_time=900, now=1230), (False, 'Receipt is for another candle'))
        self.assertEqual(allow(receipt(completed=899)), (False, 'Receipt predates candle close'))
        for now in (math.nan, None, math.inf, '930'):
            self.assertEqual(allow(receipt(), now=now), (False, 'Invalid clock'))
        self.assertEqual(allow(receipt(), side='flat'), (False, 'Invalid code side'))

    def test_validate_statuses_sums_and_ties(self):
        with self.assertRaises(ValueError):
            jev_m5.validate_receipt(receipt(status='timeout'))
        for status in ('unavailable', 'budget_exhausted', 'invalid'):
            self.assertEqual(jev_m5.validate_receipt(receipt(status=status, choice=None,
                confidence=None, probabilities=None))['status'], status)
        for probabilities in ({'buy': .8, 'hold': .1, 'sell': .2}, {'buy': .45, 'hold': .45, 'sell': .1}):
            with self.subTest(probabilities=probabilities), self.assertRaises(ValueError):
                jev_m5.validate_receipt(receipt(probabilities=probabilities))

class StoreTest(unittest.TestCase):
    def test_first_receipt_wins_and_reads_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'r.sqlite3'
            first = receipt('buy')
            self.assertTrue(jev_m5.store_receipt(path, first, received=1031))
            self.assertFalse(jev_m5.store_receipt(path, receipt('sell'), received=1032))
            self.assertEqual(jev_m5.load_receipt(path, 600)['choice'], 'buy')
            self.assertIsNone(jev_m5.load_receipt(path, 1200))
            with self.assertRaises(ValueError):
                jev_m5.store_receipt(path, {**first, 'bar_time': 1200, 'model': 'x'}, received=1)

    def test_rejects_invalid_received_time(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'r.sqlite3'
            for received in (None, math.nan, '1031'):
                with self.subTest(received=received), self.assertRaises(ValueError):
                    jev_m5.store_receipt(path, receipt(), received=received)
            self.assertIsNone(jev_m5.load_receipt(path, 600))

    def test_schema_failure_closes_connection(self):
        db = mock.MagicMock()
        db.execute.side_effect = RuntimeError('schema')
        with mock.patch.object(jev_m5.sqlite3, 'connect', return_value=db), self.assertRaises(RuntimeError):
            jev_m5.store_receipt(Path('unused'), receipt(), received=1031)
        db.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
