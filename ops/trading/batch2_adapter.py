"""Offline baseline CLI-report reconciliation; never qualifies or dispatches research."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from batch3_adapter import encode, sha, simulator
from batch3_runner import research_module, write_once
from gold_costs import validate_profile
from gold_experiment import RISK, SCENARIOS, digest, source_hashes

MAX_INPUT_BYTES = 32 * 1024 * 1024


def protocol_draft(created_at):
    if type(created_at) is not int or created_at <= 0:
        raise ValueError('Invalid protocol creation time')
    research = research_module()
    if digest(RISK) != research.RISK_SHA256:
        raise ValueError('Risk changed')
    policy = json.loads(Path(__file__).with_name('evaluation-policy.json').read_bytes())
    if digest(policy) != research.POLICY_SHA256:
        raise ValueError('Policy changed')
    return {'schema_version': 1, 'status': 'prepared_not_started', 'created_at': created_at,
            'symbol': 'XAUUSD-VIP', 'timeframe': 'M15', 'strategy': 'gold-ema-v1',
            'timestamp_basis': 'utc_required', 'code_sha256': source_hashes(),
            'risk_sha256': research.RISK_SHA256, 'policy_sha256': research.POLICY_SHA256,
            'collection_start': None, 'windows': None, 'holdout': None,
            'source_references': {}, 'blockers': ['dated_costs_unverified',
                'dated_clock_sessions_unverified', 'future_windows_holdout_unset',
                'diagnostic_retention_unverified', 'observed_sample_missing',
                'simulator_provenance_unverified']}


def load(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_INPUT_BYTES:
        raise ValueError('Input too large')
    def reject_constant(value):
        raise ValueError('Nonfinite input')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=research_module().unique_object,
                       parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError('JSON object required')
    encode(value)  # Reject overflowing numbers anywhere in the parsed object.
    return value


def utc_daily(window, initial):
    closes = {datetime.fromtimestamp(mark['bar_time'], timezone.utc).date().isoformat():
              mark['equity'] for mark in window['equity_curve']}
    previous, returns = initial, {}
    for day, equity in closes.items():
        if previous <= 0:
            raise ValueError('Daily equity denominator invalid')
        returns[day] = equity / previous - 1
        previous = equity
    return returns


def adapt_baseline(dataset_raw, windows_raw, costs_raw, report_raw, clock_raw, protocol):
    try:
        if encode(protocol) != encode(protocol_draft(protocol['created_at'])):
            raise ValueError('Protocol identity mismatch')
        data, windows, costs, report, clock = map(load,
            (dataset_raw, windows_raw, costs_raw, report_raw, clock_raw))
        if (data.get('symbol') != 'XAUUSD-VIP' or data.get('timeframe') != 'M15'
                or data.get('timestamp_basis') != 'utc' or clock.get('timestamp_basis') != 'utc'
                or clock.get('status') != 'unreviewed' or report.get('candidate') is not None
                or set(windows) != {'development', 'validation', 'folds'}):
            raise ValueError('Explicit unreviewed UTC baseline required')
        start, end = windows['development']['start'], windows['validation']['end']
        if not validate_profile(costs, start, end)['historical_coverage']:
            raise ValueError('Costs uncovered')
        expected = simulator()(data, windows=windows, cost_profile=costs)
        expected.update(dataset_sha256=sha(dataset_raw), windows_sha256=sha(windows_raw),
                        cost_profile_sha256=sha(costs_raw), code_sha256={
                            k: protocol['code_sha256'][k] for k in
                            ('simulate-gold.py', 'replay-gold.py', 'gold_signal.py')})
        if encode(report) != encode(expected) or report['holdout']['bars'] <= 0:
            raise ValueError('Baseline report mismatch or holdout missing')
        lower = report['runs']['lower']
        initial = report['initial_usd_per_window']
        validation = lower['windows']['validation']
        result = {'mode': 'baseline-adapter-preparation', 'qualification': 'unqualified',
            'baseline_reproduced': True, 'provenance_verified_for_real_data': False,
            'promotion_status': 'blocked', 'human_promotion_approval_required': True,
            'model_requests': 0, 'dispatch_status': 'blocked', 'holdout': report['holdout'],
            'limitations': protocol['blockers'] + ['utc_declaration_not_mapping_proof'],
            'identity': {'dataset_sha256': sha(dataset_raw), 'report_sha256': sha(report_raw),
                'windows_sha256': sha(windows_raw), 'cost_profile_sha256': sha(costs_raw),
                'clock_sha256': sha(clock_raw), 'protocol_sha256': digest(protocol),
                'evaluator_sha256': digest(protocol['code_sha256']),
                'risk_sha256': protocol['risk_sha256'], 'policy_sha256': protocol['policy_sha256'],
                'window_start': windows['validation']['start'], 'window_end': end},
            'validation': {'observed_days': 0,
                'trades': min(report['runs'][k]['windows']['validation']['summary']['trades'] for k in SCENARIOS),
                'daily_returns': utc_daily(validation, initial),
                'scenarios': {k: report['runs'][k]['windows']['validation']['summary'] for k in SCENARIOS},
                'folds': [{'start': datetime.fromtimestamp(f['first_bar'], timezone.utc).date().isoformat(),
                          'end': datetime.fromtimestamp(f['last_bar'], timezone.utc).date().isoformat(),
                          'days': 0, 'calendar_days_with_marks': len(utc_daily(f, initial)),
                          'return_pct': f['summary']['return_pct']} for f in lower['folds']]}}
        return result
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError, IndexError, RecursionError):
        raise ValueError('Invalid or unreconciled baseline adapter input') from None


def save_adapter(path, result):
    return write_once(Path(path), result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    names = ('dataset', 'windows', 'costs', 'report', 'clock', 'protocol')
    for name in names:
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.draft and any(getattr(args, n) for n in names):
        parser.error('Draft mode takes no report inputs')
    if not args.draft and not all(getattr(args, n) for n in names):
        parser.error('Adapter mode requires all six input files')
    try:
        if args.draft:
            result = protocol_draft(int(time.time()))
        else:
            inputs = []
            for name in names:
                with getattr(args, name).open('rb') as source:
                    inputs.append(source.read(MAX_INPUT_BYTES + 1))
            result = adapt_baseline(*inputs[:5], load(inputs[5]))
        save_adapter(args.output, result)
    except (ValueError, OSError, UnicodeError, RecursionError):
        parser.exit(2, 'Adapter refused input or exclusive output.\n')
    print('Protocol prepared, not started.' if args.draft else
          'Baseline reconciled; unqualified; model_requests=0; promotion=blocked.')


if __name__ == '__main__':
    main()
