"""Offline development packet adapters; never qualify or dispatch research."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import statistics
from datetime import datetime, timezone

from batch3_runner import research_module
from gold_costs import validate_profile
from gold_experiment import (RISK, SCENARIOS, digest, experiment_identity,
                             prepare_experiment, research_input, source_hashes)
from trusted_oauth_transport import strict_json


FROZEN_DATASET_SHA256 = 'ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614'
MAX_INPUT_BYTES = 32 * 1024 * 1024


def simulator():
    return runpy.run_path(str(Path(__file__).with_name('simulate-gold.py')))['run']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def adapt_real(dataset_raw, baseline_raw, manifest_raw):
    """Accept only the existing frozen export and a reproduced current baseline."""
    try:
        if (any(not isinstance(raw, bytes) or len(raw) > MAX_INPUT_BYTES
                for raw in (dataset_raw, baseline_raw, manifest_raw))
                or sha(dataset_raw) != FROZEN_DATASET_SHA256):
            raise ValueError('Frozen dataset required')
        data, baseline, manifest = map(strict_json, (dataset_raw, baseline_raw, manifest_raw))
        sources = source_hashes()
        expected_manifest = {**prepare_experiment(data, FROZEN_DATASET_SHA256, sources),
                             'status': 'frozen'}
        research = research_module()
        policy = strict_json(Path(__file__).with_name('evaluation-policy.json').read_bytes())
        if (encode(manifest) != encode(expected_manifest)
                or digest(RISK) != research.RISK_SHA256 or digest(policy) != research.POLICY_SHA256):
            raise ValueError('Frozen experiment identity mismatch')
        expected = simulator()(data, windows=manifest['windows'])
        expected.update(dataset_sha256=FROZEN_DATASET_SHA256, code_sha256=sources,
            cost_profile_sha256=None, windows_sha256=digest(manifest['windows']),
            identity=experiment_identity(manifest))
        if encode(baseline) != encode(expected) or source_hashes() != sources:
            raise ValueError('Baseline is not reproducible')
        development = research_input(data, manifest, baseline)
        packet = {'schema_version': 1, 'experiment_id': 'gold-development-20260928',
            'identity': {'manifest_sha256': digest(manifest), 'source_sha256': digest(sources),
                'development_input_sha256': digest(data['bars'][:6000]),
                'risk_sha256': research.RISK_SHA256, 'policy_sha256': research.POLICY_SHA256},
            'development': development['development'],
            'baseline_development': development['baseline_development'],
            'proposal_schema': research.PROPOSAL_SCHEMA,
            'limitations': ['validation_previously_inspected', 'reserved_bars_signal_replayed',
                'historical_costs_unverified', 'broker_timestamps_unqualified', 'slippage_assumed']}
        research.validate_packet(packet)
        return packet, {'mode': 'real-development-adapter-audit', 'qualification': 'unqualified',
            'dataset_sha256': FROZEN_DATASET_SHA256, 'manifest_sha256': sha(manifest_raw),
            'baseline_sha256': sha(baseline_raw), 'packet_sha256': digest(packet),
            'baseline_reproduced': True, 'provenance_verified_for_real_data': False,
            'research_input_bars': 6000, 'validation_in_prompt': False, 'reserved_in_prompt': False,
            'limitations': packet['limitations'], 'model_requests': 0,
            'dispatch_status': 'blocked', 'promotion_status': 'blocked'}
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, IndexError, RecursionError):
        raise ValueError('Invalid or unreconciled real development input') from None


def adapt_synthetic(dataset_raw, baseline_raw, manifest, costs, clock):
    research = research_module()
    required = {'schema_version', 'mode', 'dataset_sha256', 'baseline_sha256',
                'code_sha256', 'windows', 'risk', 'policy_sha256', 'cost_sha256', 'clock_sha256'}
    if (not isinstance(manifest, dict) or set(manifest) != required
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or manifest['mode'] != 'synthetic-only'
            or manifest['dataset_sha256'] != sha(dataset_raw)
            or manifest['baseline_sha256'] != sha(baseline_raw)
            or manifest['code_sha256'] != source_hashes()
            or digest(manifest['risk']) != research.RISK_SHA256 or digest(RISK) != research.RISK_SHA256
            or manifest['policy_sha256'] != research.POLICY_SHA256
            or manifest['cost_sha256'] != digest(costs) or manifest['clock_sha256'] != digest(clock)
            or costs.get('evidence_mode') != 'synthetic_fixture'
            or clock.get('status') != 'synthetic_fixture'):
        raise ValueError('Synthetic report identity mismatch')
    data = json.loads(dataset_raw, object_pairs_hook=research.unique_object)
    baseline = json.loads(baseline_raw, object_pairs_hook=research.unique_object)
    if (data.get('symbol') != 'XAUUSD-VIP' or data.get('timeframe') != 'M15'
            or data.get('evidence_mode') != 'synthetic_fixture'):
        raise ValueError('Synthetic dataset required')
    windows = manifest['windows']
    start, end = windows['development']['start'], windows['validation']['end']
    if not validate_profile(costs, start, end)['historical_coverage']:
        raise ValueError('Cost interval uncovered')
    if (set(clock) != {'status', 'source_sha256', 'effective_from', 'effective_to', 'offset_seconds'}
            or not isinstance(clock['source_sha256'], str)
            or len(clock['source_sha256']) != 64
            or any(c not in '0123456789abcdef' for c in clock['source_sha256'])
            or any(type(clock[k]) is not int for k in ('effective_from', 'effective_to', 'offset_seconds'))
            or not clock['effective_from'] <= start <= end <= clock['effective_to']):
        raise ValueError('Clock interval uncovered')
    # A new hash alone cannot make a modified report authentic: recompute it.
    expected = simulator()(data, windows=windows, cost_profile=costs)
    if baseline != expected or baseline.get('candidate') is not None:
        raise ValueError('Baseline is not reproducible')
    development_bars = [b for b in data['bars'] if b['time'] <= windows['development']['end']]
    closes = [b['close'] for b in development_bars]
    packet = {'schema_version': 1, 'experiment_id': 'synthetic-batch3-rehearsal',
        'identity': {'manifest_sha256': digest(manifest), 'source_sha256': digest(source_hashes()),
                     'development_input_sha256': digest(development_bars),
                     'risk_sha256': digest(RISK), 'policy_sha256': research.POLICY_SHA256},
        'development': {'bars_including_warmup': len(development_bars),
            'first_bar': development_bars[0]['time'], 'last_bar': development_bars[-1]['time'],
            'first_close': closes[0], 'last_close': closes[-1], 'minimum_close': min(closes),
            'maximum_close': max(closes), 'median_recorded_spread_points': statistics.median(b['spread'] for b in development_bars),
            'gap_count': sum(b['time'] - a['time'] != 900 for a, b in zip(development_bars, development_bars[1:]))},
        'baseline_development': {name: {key: baseline['runs'][name]['windows']['development']['summary'][key]
            for key in ('trades', 'return_pct', 'net_pnl_usd', 'profit_factor',
                        'expectancy_usd_per_trade', 'close_sampled_drawdown_pct')} for name in SCENARIOS},
        'proposal_schema': research.PROPOSAL_SCHEMA, 'limitations': ['synthetic_fixture']}
    research.validate_packet(packet)
    return packet, {'mode': 'synthetic-adapter-audit', 'qualification': 'unqualified',
        'provenance_verified_for_real_data': False, 'baseline_reproduced': True,
        'manifest': manifest, 'cost_evidence': costs, 'clock_evidence': clock,
        'packet_sha256': digest(packet), 'promotion_status': 'blocked'}


def synthetic_gate_input(report, manifest, clock):
    """Convert close-sampled curves, not raw-epoch daily buckets, into UTC days.

    Single-offset synthetic fixture only; real dated/DST mapping remains gated.
    """
    if manifest['mode'] != 'synthetic-only' or clock['status'] != 'synthetic_fixture':
        raise ValueError('Synthetic gate input only')

    def utc_day(stamp):
        return datetime.fromtimestamp(stamp - clock['offset_seconds'], timezone.utc).date().isoformat()

    def daily(window):
        closes = {utc_day(mark['bar_time']): mark['equity'] for mark in window['equity_curve']}
        previous = report['initial_usd_per_window']
        returns = {}
        for day, equity in closes.items():
            returns[day] = equity / previous - 1
            previous = equity
        return returns

    lower = report['runs']['lower']
    validation = lower['windows']['validation']
    returns = daily(validation)
    return {'mode': 'synthetic-gate-input', 'qualification': 'unqualified',
        'identity': {'dataset_sha256': manifest['dataset_sha256'],
            'evaluator_sha256': digest(manifest['code_sha256']),
            'cost_profile_sha256': manifest['cost_sha256'], 'clock_sha256': manifest['clock_sha256'],
            'policy_sha256': manifest['policy_sha256'], 'risk_sha256': digest(manifest['risk']),
            'window_start': manifest['windows']['validation']['start'],
            'window_end': manifest['windows']['validation']['end']},
        'validation': {'trades': min(report['runs'][name]['windows']['validation']['summary']['trades'] for name in SCENARIOS),
            'observed_days': len(returns), 'daily_returns': returns,
            'scenarios': {name: report['runs'][name]['windows']['validation']['summary'] for name in SCENARIOS},
            'folds': [{'start': utc_day(fold['first_bar']), 'end': utc_day(fold['last_bar']),
                       'days': len(daily(fold)), 'return_pct': fold['summary']['return_pct']}
                      for fold in lower['folds']]}}


def main():
    parser = argparse.ArgumentParser(description='Prepare the frozen real-data packet offline; no inference.')
    for name in ('dataset', 'baseline', 'manifest', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        from gold_account import private_acl
        from batch3_runner import write_once
        private_acl(args.output.parent)
        if args.output.exists():
            raise FileExistsError('Preserve existing packet preparation')
        inputs = []
        for path in (args.dataset, args.baseline, args.manifest):
            with path.open('rb') as source:
                inputs.append(source.read(MAX_INPUT_BYTES + 1))
        packet, audit = adapt_real(*inputs)
        args.output.mkdir()
        write_once(args.output/'packet.json', packet)
        private_acl(args.output/'packet.json')
        prepared = research_module().prepare_prompt(encode(packet), args.output/'prompt')
        for name in ('packet.json', 'prompt.txt', 'result.json'):
            private_acl(args.output/'prompt'/name)
        audit['prompt_sha256'] = prepared['prompt_sha256']
        write_once(args.output/'audit.json', audit)
        private_acl(args.output/'audit.json')
    except (ValueError, OSError, UnicodeError, RecursionError):
        parser.exit(2, 'Real packet preparation refused input, private boundary or exclusive output.\n')
    print('Real development packet prepared offline; unqualified; model_requests=0; dispatch=blocked.')


if __name__ == '__main__':
    main()
