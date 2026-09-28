import unittest

from gold_costs import commission_usd, rollover_cashflow_usd, validate_profile


class CostTest(unittest.TestCase):
    def setUp(self):
        self.profile = {'symbol': 'XAUUSD-VIP',
                        'commission': {'status': 'verified_historical', 'source_sha256': 'a' * 64,
                                       'effective_from': 1, 'effective_to': 1000,
                                       'value': 7, 'currency': 'USD', 'basis': 'round_trip_per_lot',
                                       'minimum': None},
                        'swap': {'status': 'verified_historical', 'source_sha256': 'b' * 64,
                                 'effective_from': 1, 'effective_to': 1000,
                                 'mode': 'POINTS', 'rollover_timezone': 'UTC',
                                 'rollover_local_time': '00:00', 'rollover_events': [
                                     {'at': 100, 'multiplier': 1, 'rate_long': -2, 'rate_short': 1},
                                     {'at': 200, 'multiplier': 3, 'rate_long': -2, 'rate_short': 1}]}}

    def test_commission_basis_and_unknown(self):
        self.assertEqual(commission_usd(self.profile, 1, 'entry'), 3.5)
        self.profile['commission']['basis'] = 'per_side_per_lot'
        self.assertEqual(commission_usd(self.profile, 1, 'exit'), 7)
        self.profile['commission']['value'] = 0
        self.assertEqual(commission_usd(self.profile, 1, 'exit'), 0)
        self.profile['commission']['value'] = None
        with self.assertRaises(ValueError):
            commission_usd(self.profile, 1, 'exit')

    def test_rollover_boundary_and_credit(self):
        spec = {'currency_profit': 'USD', 'point': .01, 'trade_contract_size': 100}
        self.assertEqual(rollover_cashflow_usd(self.profile, 1, .5, spec, 99, 100), -1)
        self.assertEqual(rollover_cashflow_usd(self.profile, 1, .5, spec, 100, 200), -3)
        self.assertEqual(rollover_cashflow_usd(self.profile, -1, .5, spec, 99, 200), 2)

    def test_provenance_and_coverage(self):
        self.assertTrue(validate_profile(self.profile, 1, 1000)['historical_coverage'])
        self.assertIn('swap_history_uncovered', validate_profile(self.profile, 1, 1001)['blockers'])
        self.profile['swap']['status'] = 'unknown'
        self.assertIn('swap_unverified', validate_profile(self.profile, 1, 100)['blockers'])
        with self.assertRaises(ValueError):
            rollover_cashflow_usd(self.profile, 1, 1, {}, 1, 100)


if __name__ == '__main__':
    unittest.main()
