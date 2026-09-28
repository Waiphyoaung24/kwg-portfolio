import unittest

from gold_qualification import qualify_samples


def samples():
    first = 90900
    return [dict(sampled_at=first + i * 5, tick_time_msc=(first + i * 5 - 1) * 1000,
                 quote_age_seconds=1, quote='fresh', terminal='connected',
                 history_valid=True, history_count=250,
                 history_bar_time=((first + i * 5) // 900) * 900 - 900,
                 spread_price=.2) for i in range(361)]


class QualificationTest(unittest.TestCase):
    def test_two_completed_transitions_require_continuity(self):
        data = samples()
        result = qualify_samples(data)
        self.assertEqual(result['data_status'], 'passed')
        self.assertEqual(result['transition_bar_times'], [90900, 91800])
        self.assertEqual(result['accepted_sample_count'], 361)
        self.assertAlmostEqual(result['spread_summary']['p95_price'], .2)
        self.assertEqual(qualify_samples([data[0], data[180], data[-1]])['data_status'], 'inconclusive')
        data[-1]['quote_age_seconds'] = 30.001
        self.assertEqual(qualify_samples(data)['data_status'], 'inconclusive')

    def test_gaps_future_ticks_and_invalid_history_reset_segment(self):
        for key, value in [('quote_age_seconds', -.001), ('tick_time_msc', 1),
                           ('history_valid', False), ('history_count', 249),
                           ('history_bar_time', 1), ('quote', 'stale'),
                           ('terminal', 'disconnected')]:
            data = samples()
            data[200][key] = value
            with self.subTest(key=key):
                self.assertEqual(qualify_samples(data)['data_status'], 'inconclusive')
        data = samples()
        data[200]['sampled_at'] += 6
        self.assertEqual(qualify_samples(data)['data_status'], 'inconclusive')
        data = samples()
        data[200]['history_bar_time'] += 900
        self.assertEqual(qualify_samples(data)['data_status'], 'inconclusive')
        data = samples()
        data[200]['history_count'] = None
        self.assertEqual(qualify_samples(data)['data_status'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
