import copy
import hashlib
import json
from pathlib import Path
import runpy
import unittest

evaluate = runpy.run_path(str(Path(__file__).with_name('evaluate-gold.py')))['evaluate_reports']
policy = json.loads(Path(__file__).with_name('evaluation-policy.json').read_text())


def reports():
    identity = {key: 'same' for key in ('dataset_sha256', 'evaluator_sha256',
                'cost_profile_sha256', 'policy_sha256', 'window_start', 'window_end', 'risk_sha256')}
    folds = [{'start': f'{i:02}', 'end': f'{i+19:02}', 'days': 20, 'return_pct': 1}
             for i in (0, 20, 40)]
    scenario = {'return_pct': 1, 'close_sampled_drawdown_pct': 1,
                'net_pnl_usd': 1000, 'profit_factor': 1.2}
    base = {'identity': identity, 'validation': {
        'trades': 120, 'observed_days': 60,
        'scenarios': {name: copy.deepcopy(scenario) for name in ('lower', 'middle', 'stress')},
        'folds': folds, 'daily_returns': {f'{i:02}': 0.001 for i in range(60)}}}
    candidate = copy.deepcopy(base)
    candidate['declared_changes'] = 1
    candidate['evidence'] = {'batch1_status': 'passed', 'cost_status': 'verified_historical',
                             'registration_at': 1, 'execution_started_at': 2}
    candidate['validation']['scenarios']['lower']['return_pct'] = 1.3
    for name in ('middle', 'stress'):
        candidate['validation']['scenarios'][name]['return_pct'] = 1.1
    for fold in candidate['validation']['folds']:
        fold['return_pct'] = 1.1
    candidate['validation']['daily_returns'] = {f'{i:02}': 0.002 for i in range(60)}
    approved = {**policy, 'status': 'approved', 'bootstrap_replicates': 100}
    policy_hash = hashlib.sha256(json.dumps(approved, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    base['identity']['policy_sha256'] = policy_hash
    candidate['identity']['policy_sha256'] = policy_hash
    return base, candidate, approved


class GateTest(unittest.TestCase):
    def test_draft_and_small_sample_never_eligible(self):
        base, candidate, approved = reports()
        self.assertEqual(evaluate(base, candidate, {**approved, 'status': 'draft'})['decision'], 'inconclusive')
        candidate['validation']['trades'] = 30
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'inconclusive')

    def test_positive_candidate_and_scope(self):
        base, candidate, approved = reports()
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'eligible_for_shadow')
        candidate['identity']['risk_sha256'] = 'changed'
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'rejected')

    def test_cost_and_stress_fail_closed(self):
        base, candidate, approved = reports()
        candidate['evidence']['cost_status'] = 'unknown'
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'inconclusive')
        candidate['evidence']['cost_status'] = 'verified_historical'
        candidate['validation']['scenarios']['stress']['return_pct'] = -1
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'rejected')

    def test_nonfinite_report_or_policy_is_inconclusive(self):
        base, candidate, approved = reports()
        candidate['validation']['scenarios']['lower']['return_pct'] = float('nan')
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'inconclusive')
        base, candidate, approved = reports()
        approved['min_profit_factor'] = float('nan')
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'inconclusive')

    def test_zero_bootstrap_block_is_inconclusive(self):
        base, candidate, approved = reports()
        approved['bootstrap_block_days'] = 0
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'inconclusive')

    def test_changed_approved_policy_invalidates_comparison(self):
        base, candidate, approved = reports()
        approved['min_profit_factor'] = 1.0
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'rejected')

    def test_overflowing_bootstrap_arithmetic_is_inconclusive(self):
        base, candidate, approved = reports()
        base['validation']['daily_returns'] = {f'{i:02}': -1e308 for i in range(60)}
        candidate['validation']['daily_returns'] = {f'{i:02}': 1e308 for i in range(60)}
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'inconclusive')
        base['validation']['daily_returns'] = {f'{i:02}': 0 for i in range(60)}
        self.assertEqual(evaluate(base, candidate, approved)['decision'], 'inconclusive')


if __name__ == '__main__':
    unittest.main()
