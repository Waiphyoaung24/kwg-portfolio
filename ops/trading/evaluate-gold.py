"""Offline gate for one registered gold candidate. No broker or order API."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Missing or nonfinite metric')
    return float(value)


def _percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def evaluate_reports(baseline: dict, candidate: dict, policy: dict) -> dict:
    reasons = []
    decision = 'inconclusive'
    identity_keys = ('dataset_sha256', 'evaluator_sha256', 'cost_profile_sha256',
                     'policy_sha256', 'window_start', 'window_end', 'risk_sha256')
    try:
        base_id, cand_id = baseline['identity'], candidate['identity']
        base, cand = baseline['validation'], candidate['validation']
        evidence = candidate['evidence']
    except (KeyError, TypeError):
        return {'decision': decision, 'reasons': ['report_incomplete']}
    if any(base_id.get(key) != cand_id.get(key) or not base_id.get(key) for key in identity_keys):
        return {'decision': 'rejected', 'reasons': ['identity_or_risk_mismatch']}
    if candidate.get('declared_changes') != 1:
        return {'decision': 'rejected', 'reasons': ['candidate_scope_invalid']}
    try:
        for key in ('min_profit_factor', 'min_improvement_pp', 'max_drawdown_pct',
                    'max_drawdown_increase_pp', 'max_fold_underperformance_pp'):
            if _finite(policy[key]) < 0:
                raise ValueError('Invalid policy threshold')
        for key in ('min_trades', 'min_observed_days', 'min_fold_days',
                    'required_improved_folds', 'bootstrap_replicates', 'bootstrap_block_days'):
            if type(policy[key]) is not int or policy[key] <= 0:
                raise ValueError('Invalid policy count')
        if type(policy['bootstrap_seed']) is not int or policy['required_improved_folds'] > 3:
            raise ValueError('Invalid policy seed or fold count')
    except (KeyError, TypeError, ValueError):
        return {'decision': decision, 'reasons': ['policy_invalid']}
    if policy.get('status') == 'approved':
        try:
            policy_sha256 = hashlib.sha256(json.dumps(policy, sort_keys=True,
                separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        except (TypeError, ValueError):
            return {'decision': decision, 'reasons': ['policy_invalid']}
        if base_id['policy_sha256'] != policy_sha256:
            return {'decision': 'rejected', 'reasons': ['policy_identity_mismatch']}
    if policy.get('status') != 'approved':
        reasons.append('policy_not_approved')
    if evidence.get('batch1_status') != 'passed' or evidence.get('cost_status') != 'verified_historical':
        reasons.append('evidence_incomplete')
    registered, started = evidence.get('registration_at'), evidence.get('execution_started_at')
    if type(registered) is not int or type(started) is not int or registered >= started:
        reasons.append('registration_missing_or_late')
    if reasons:
        return {'decision': decision, 'reasons': reasons}
    try:
        for report in (base, cand):
            if _finite(report['trades']) < policy['min_trades'] or _finite(report['observed_days']) < policy['min_observed_days']:
                reasons.append('sample_insufficient')
        scenarios = ('lower', 'middle', 'stress')
        for name in scenarios:
            b, c = base['scenarios'][name], cand['scenarios'][name]
            for item in (b, c):
                for metric in ('return_pct', 'close_sampled_drawdown_pct', 'net_pnl_usd'):
                    _finite(item[metric])
            if c['net_pnl_usd'] <= 0:
                reasons.append(name + '_net_pnl_nonpositive')
            if name == 'lower':
                pf = c.get('profit_factor')
                if pf is None:
                    reasons.append('profit_factor_undefined')
                elif _finite(pf) < policy['min_profit_factor']:
                    reasons.append('profit_factor_low')
                if c['return_pct'] <= 0 or _finite(c['return_pct'] - b['return_pct']) < policy['min_improvement_pp']:
                    reasons.append('base_return_gate_failed')
            elif c['return_pct'] <= 0 or c['return_pct'] < b['return_pct']:
                reasons.append(name + '_return_gate_failed')
            if (c['close_sampled_drawdown_pct'] > policy['max_drawdown_pct']
                    or _finite(c['close_sampled_drawdown_pct'] - b['close_sampled_drawdown_pct']) > policy['max_drawdown_increase_pp']):
                reasons.append(name + '_drawdown_gate_failed')
        folds_b, folds_c = base['folds'], cand['folds']
        if len(folds_b) != 3 or len(folds_c) != 3:
            reasons.append('folds_incomplete')
        else:
            better = 0
            for b, c in zip(folds_b, folds_c):
                if b['start'] != c['start'] or b['end'] != c['end'] or _finite(c['days']) < policy['min_fold_days']:
                    reasons.append('fold_mismatch_or_short')
                    continue
                delta = _finite(_finite(c['return_pct']) - _finite(b['return_pct']))
                better += delta > 0
                if delta < -policy['max_fold_underperformance_pp']:
                    reasons.append('fold_underperformed')
            if better < policy['required_improved_folds']:
                reasons.append('fold_stability_failed')
        daily_b, daily_c = base['daily_returns'], cand['daily_returns']
        if set(daily_b) != set(daily_c) or len(daily_b) < policy['min_observed_days']:
            reasons.append('paired_days_mismatch')
        if reasons:
            return {'decision': 'inconclusive' if any(x in reasons for x in
                    ('sample_insufficient', 'profit_factor_undefined', 'folds_incomplete',
                     'fold_mismatch_or_short', 'paired_days_mismatch')) else 'rejected',
                    'reasons': reasons}
        days = sorted(daily_b)
        diffs = {d: _finite(_finite(daily_c[d]) - _finite(daily_b[d])) for d in days}
        block = policy['bootstrap_block_days']
        blocks = []
        assigned = set()
        for fold in folds_b:
            fold_days = [d for d in days if fold['start'] <= d <= fold['end']]
            if (len(fold_days) != fold['days'] or len(fold_days) < block
                    or assigned.intersection(fold_days)):
                return {'decision': 'inconclusive', 'reasons': ['bootstrap_fold_days_missing']}
            assigned.update(fold_days)
            blocks.extend([[diffs[d] for d in fold_days[i:i + block]]
                           for i in range(len(fold_days) - block + 1)])
        if len(days) < block or assigned != set(days):
            return {'decision': 'inconclusive', 'reasons': ['bootstrap_sample_short']}
        rng = random.Random(policy['bootstrap_seed'])
        means = []
        for _ in range(policy['bootstrap_replicates']):
            draw = []
            while len(draw) < len(days):
                draw.extend(rng.choice(blocks))
            means.append(_finite(sum(draw[:len(days)]) / len(days)))
        interval = [_percentile(means, .025), _percentile(means, .975)]
        if interval[0] <= 0:
            reasons.append('bootstrap_lower_bound_nonpositive')
        return {'decision': 'rejected' if reasons else 'eligible_for_shadow',
                'reasons': reasons, 'paired_daily_difference_ci95': interval}
    except (KeyError, TypeError, ValueError, IndexError):
        return {'decision': 'inconclusive', 'reasons': ['report_incomplete']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'policy', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    inputs = {name: getattr(args, name).read_bytes() for name in ('baseline', 'candidate', 'policy')}
    result = evaluate_reports(*(json.loads(inputs[name]) for name in ('baseline', 'candidate', 'policy')))
    result['input_sha256'] = {name: hashlib.sha256(raw).hexdigest() for name, raw in inputs.items()}
    with args.output.open('xb') as output:
        output.write((json.dumps(result, sort_keys=True, allow_nan=False) + '\n').encode())
    print(result['decision'], ','.join(result['reasons']))


if __name__ == '__main__':
    main()
