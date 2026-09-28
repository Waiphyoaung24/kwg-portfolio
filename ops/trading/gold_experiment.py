"""Offline experiment contract for one provisional gold comparison."""
import hashlib
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import statistics

from gold_signal import ema


SCENARIOS = {
    'lower': dict(commission=3.5, slippage=.05, overnight=5, spread_multiplier=1),
    'middle': dict(commission=7, slippage=.10, overnight=15, spread_multiplier=1.5),
    'stress': dict(commission=14, slippage=.30, overnight=30, spread_multiplier=2),
}
RISK = {'entry_equity_fraction': .001, 'stop_atr': 2, 'target_atr': 3,
        'daily_entry_pause_fraction': .01, 'max_positions': 1,
        'same_bar_reversal': False}
SOURCES = ('simulate-gold.py', 'replay-gold.py', 'gold_signal.py',
           'gold_costs.py', 'gold_experiment.py', 'compare-gold.py')


def source_hashes() -> dict:
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in SOURCES}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value.lower())


def prepare_experiment(data: dict, dataset_sha256: str, code_sha256: dict) -> dict:
    if (not _hash(dataset_sha256) or not isinstance(code_sha256, dict)
            or set(code_sha256) != set(SOURCES)
            or any(not _hash(value) for value in code_sha256.values())):
        raise ValueError('Missing dataset or evaluator hash')
    if (data.get('schema_version') != 1 or data.get('symbol') != 'XAUUSD-VIP'
            or data.get('timeframe') != 'M15' or data.get('source', {}).get('start_pos') != 1
            or len(data.get('bars', [])) != 10000):
        raise ValueError('Expected the frozen completed-bar gold export')
    bars = data['bars']
    previous = 0
    gaps = 0
    for bar in bars:
        try:
            stamp = bar['time']
            prices = [bar[k] for k in ('open', 'high', 'low', 'close')]
            spread = bar['spread']
            valid = (type(stamp) is int and stamp > previous and stamp % 900 == 0
                     and all(type(p) in (int, float) and math.isfinite(p) and p > 0 for p in prices)
                     and prices[1] >= max(prices[0], prices[2], prices[3])
                     and prices[2] <= min(prices[0], prices[3])
                     and type(spread) is int and spread >= 0)
        except (KeyError, TypeError):
            valid = False
        if not valid:
            raise ValueError('Invalid frozen gold bar')
        gaps += bool(previous and stamp - previous != 900)
        previous = stamp
    # Raw broker bar epochs are not yet qualified against the host clock.
    if type(data.get('captured_at')) not in (int, float) or not math.isfinite(data['captured_at']):
        raise ValueError('Invalid capture time')
    windows = {'development': {'start': bars[249]['time'], 'end': bars[5999]['time']},
               'validation': {'start': bars[6000]['time'], 'end': bars[7999]['time']}}
    return {'schema_version': 1, 'status': 'prepared', 'mode': 'provisional-offline',
            'symbol': 'XAUUSD-VIP', 'dataset_sha256': dataset_sha256.lower(),
            'code_sha256': code_sha256, 'windows': windows, 'reserved_start_index': 8000,
            'gap_count': gaps,
            'scenarios': SCENARIOS, 'risk': RISK,
            'cost_evidence': {'historical': 'unverified', 'current_commission': 'indicative_zero_standard_or_vip_stp',
                              'current_swap_points_long': -79.48, 'current_swap_points_short': 34.41,
                              'observed_spread_price_range': [0.27, 0.28]},
            'timestamp_basis': 'raw_broker_epoch_unqualified',
            'prior_exposure': 'validation_trade_results_inspected;reserved_bars_signal_replayed',
            'live_qualification': 'inconclusive_disconnect'}


def validate_candidate(proposal: dict) -> dict:
    if (not isinstance(proposal, dict) or set(proposal) != {'kind', 'lookback_bars', 'hypothesis'}
            or proposal['kind'] != 'ema20_slope_filter'
            or type(proposal['lookback_bars']) is not int or not 2 <= proposal['lookback_bars'] <= 5
            or not isinstance(proposal['hypothesis'], str)
            or not 0 < len(proposal['hypothesis'].strip()) <= 2000):
        raise ValueError('Invalid or out-of-scope candidate')
    return proposal


def entry_allowed(bars: list[dict], signal: str, lookback_bars: int) -> bool:
    if signal not in ('long', 'short'):
        return False
    if type(lookback_bars) is not int or not 2 <= lookback_bars <= 5 or len(bars) != 250:
        raise ValueError('Invalid candidate window')
    levels = ema([bar['close'] for bar in bars], 20)
    slope = levels[-1] - levels[-1 - lookback_bars]
    return slope > 0 if signal == 'long' else slope < 0


def experiment_identity(manifest: dict) -> dict:
    if manifest.get('status') not in ('prepared', 'frozen'):
        raise ValueError('Invalid manifest')
    return {'manifest_sha256': digest(manifest), 'dataset_sha256': manifest['dataset_sha256'],
            'evaluator_sha256': digest(manifest['code_sha256']),
            'windows_sha256': digest(manifest['windows']),
            'risk_sha256': digest(manifest['risk']),
            'cost_sha256': digest(manifest['scenarios'])}


def register_candidate(manifest: dict, proposal: dict, registered_at: str) -> dict:
    validate_candidate(proposal)
    if manifest.get('status') != 'frozen':
        raise ValueError('Candidate requires a frozen experiment')
    try:
        stamp = datetime.fromisoformat(registered_at)
    except (TypeError, ValueError):
        raise ValueError('Registration time must be UTC') from None
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise ValueError('Registration time must be UTC')
    return {'status': 'registered', 'identity': experiment_identity(manifest),
            'proposal_sha256': digest(proposal), 'registered_at': registered_at}


def validate_registration(registration: dict, manifest: dict, proposal: dict) -> dict:
    if (not isinstance(registration, dict) or set(registration) !=
            {'status', 'identity', 'proposal_sha256', 'registered_at'}
            or registration != register_candidate(manifest, proposal, registration['registered_at'])):
        raise ValueError('Candidate registration mismatch')
    return registration


def report_matches_manifest(report: dict, manifest: dict) -> bool:
    return (report.get('mode') == 'hypothetical-trade-simulation'
            and report.get('identity') == experiment_identity(manifest)
            and report.get('dataset_sha256') == manifest['dataset_sha256']
            and report.get('code_sha256') == manifest['code_sha256']
            and report.get('windows_sha256') == digest(manifest['windows'])
            and report.get('cost_profile_sha256') is None
            and report.get('cost_profile_status') == 'hypothetical'
            and report.get('qualification') == 'unqualified'
            and report.get('holdout') == {'start_index': 8000, 'bars': 2000, 'evaluated': False})


def research_input(data: dict, manifest: dict, baseline: dict) -> dict:
    if manifest.get('status') != 'frozen' or not report_matches_manifest(baseline, manifest):
        raise ValueError('Frozen baseline identity mismatch')
    if baseline.get('candidate') is not None:
        raise ValueError('Research input requires an unchanged baseline')
    bars = data['bars'][:6000]
    if (len(bars) != 6000 or bars[249]['time'] != manifest['windows']['development']['start']
            or bars[-1]['time'] != manifest['windows']['development']['end']):
        raise ValueError('Development window mismatch')
    summaries = {}
    for scenario in SCENARIOS:
        run = baseline['runs'][scenario]
        development = run['windows']['development']
        if (run['costs'] != SCENARIOS[scenario]
                or development['first_bar'] != manifest['windows']['development']['start']
                or development['last_bar'] != manifest['windows']['development']['end']):
            raise ValueError('Baseline run mismatch')
        summaries[scenario] = {key: development['summary'][key] for key in
                               ('trades', 'return_pct', 'net_pnl_usd', 'profit_factor',
                                'expectancy_usd_per_trade', 'close_sampled_drawdown_pct')}
    closes = [bar['close'] for bar in bars]
    return {'mode': 'development-only-research-input', 'identity': experiment_identity(manifest),
            'symbol': 'XAUUSD-VIP', 'timeframe': 'M15',
            'development': {'bars_including_warmup': len(bars), 'first_bar': bars[0]['time'],
                            'last_bar': bars[-1]['time'], 'first_close': closes[0],
                            'last_close': closes[-1], 'minimum_close': min(closes),
                            'maximum_close': max(closes),
                            'median_recorded_spread_points': statistics.median(bar['spread'] for bar in bars),
                            'gap_count': sum(b['time'] - a['time'] != 900 for a, b in zip(bars, bars[1:]))},
            'baseline_development': summaries, 'scenarios': SCENARIOS, 'risk': RISK,
            'proposal_schema': {'kind': 'ema20_slope_filter', 'lookback_bars': 'integer 2..5',
                                'hypothesis': 'nonempty string, at most 2000 characters'},
            'limitations': ['Historical costs and broker timestamp semantics unverified',
                            'Earlier validation results inspected; no validation data included']}


def compare_reports(baseline: dict, candidate: dict, manifest: dict, proposal: dict) -> dict:
    validate_candidate(proposal)
    result = {'verdict': 'invalid', 'promotion_status': 'blocked',
              'limitations': ['historical_costs_unverified', 'live_data_unqualified',
                              'raw_broker_time_unqualified', 'validation_previously_inspected']}
    try:
        expected = experiment_identity(manifest)
        if (manifest.get('status') != 'frozen' or not report_matches_manifest(baseline, manifest)
                or not report_matches_manifest(candidate, manifest)
                or candidate['proposal_sha256'] != digest(proposal)
                or baseline.get('candidate') is not None or candidate.get('candidate') != proposal):
            return {**result, 'reason': 'identity_mismatch'}
        deltas = {}
        sufficient = True
        promising = True
        for scenario in SCENARIOS:
            deltas[scenario] = {}
            for window in ('development', 'validation'):
                baseline_run = baseline['runs'][scenario]['windows'][window]
                candidate_run = candidate['runs'][scenario]['windows'][window]
                if (baseline['runs'][scenario]['costs'] != manifest['scenarios'][scenario]
                        or candidate['runs'][scenario]['costs'] != manifest['scenarios'][scenario]
                        or any(run['first_bar'] != manifest['windows'][window]['start']
                               or run['last_bar'] != manifest['windows'][window]['end']
                               for run in (baseline_run, candidate_run))):
                    return {**result, 'reason': 'run_mismatch'}
                b, c = baseline_run['summary'], candidate_run['summary']
                if (any(type(report.get('trades')) is not int or report['trades'] < 0
                        or any(type(report.get(key)) not in (int, float) or not math.isfinite(report[key])
                               for key in ('return_pct', 'net_pnl_usd', 'close_sampled_drawdown_pct',
                                           'profit_factor', 'expectancy_usd_per_trade'))
                        for report in (b, c))):
                    return {**result, 'verdict': 'inconclusive', 'reason': 'metrics_missing_or_invalid'}
                deltas[scenario][window] = {key: c[key] - b[key] for key in
                                            ('return_pct', 'net_pnl_usd', 'close_sampled_drawdown_pct', 'trades')}
                if window == 'validation':
                    sufficient &= b['trades'] >= 100 and c['trades'] >= 100
                    pf = c['profit_factor']
                    promising &= (c['return_pct'] > 0 and c['close_sampled_drawdown_pct'] <= 5
                                  and c['close_sampled_drawdown_pct'] - b['close_sampled_drawdown_pct'] <= .25)
                    if scenario == 'lower':
                        promising &= c['return_pct'] - b['return_pct'] >= .25 and pf >= 1.1
                    else:
                        promising &= c['return_pct'] >= b['return_pct']
        verdict = 'inconclusive' if not sufficient else 'promising_for_further_research' if promising else 'rejected'
        return {**result, 'verdict': verdict, 'deltas': deltas,
                'identity': expected, 'proposal_sha256': digest(proposal)}
    except (KeyError, TypeError, ValueError, OverflowError):
        return {**result, 'reason': 'report_incomplete'}
