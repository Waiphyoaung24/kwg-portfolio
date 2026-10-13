import math
import unittest

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


if __name__ == '__main__':
    unittest.main()
