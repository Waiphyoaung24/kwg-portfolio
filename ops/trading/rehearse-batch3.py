"""Rehearse packet -> bounded fake request -> validator -> simulator -> report."""
import argparse
import math
import json
import runpy
from pathlib import Path

from batch3_adapter import adapt_synthetic, encode, sha, simulator, synthetic_gate_input
from batch3_runner import run_fixture, write_once
from gold_experiment import RISK, SCENARIOS, digest, source_hashes


def fixtures():
    # Artificial oscillations exercise actual entries/exits; never broker data.
    bars = []
    for i in range(4000):
        price = 2000 + 15 * math.sin(i / 25) + 8 * math.sin(i * 1.731) + 5 * math.sin(i * .47)
        bars.append(dict(time=(i + 1) * 900, open=price, high=price + 1,
                         low=price - 1, close=price, spread=2))
    data = {'schema_version': 1, 'symbol': 'XAUUSD-VIP', 'timeframe': 'M15',
        'evidence_mode': 'synthetic_fixture', 'bars': bars,
        'source': {'start_pos': 1}, 'captured_at': 4001 * 900,
        'current_contract_specification': dict(point=.01, trade_contract_size=100,
            trade_tick_size=.01, volume_min=.01, volume_max=100, volume_step=.01, currency_profit='USD')}
    windows = {'development': {'start': bars[249]['time'], 'end': bars[1599]['time']},
               'validation': {'start': bars[1600]['time'], 'end': bars[3399]['time']},
               'folds': [{'start': bars[a]['time'], 'end': bars[b]['time']}
                         for a, b in ((1600, 2199), (2200, 2799), (2800, 3399))]}
    costs = {'symbol': 'XAUUSD-VIP', 'evidence_mode': 'synthetic_fixture',
        'commission': {'status': 'verified_historical', 'source_sha256': 'a' * 64,
            'effective_from': 900, 'effective_to': 4000 * 900, 'value': 7,
            'currency': 'USD', 'basis': 'round_trip_per_lot'},
        'swap': {'status': 'verified_historical', 'source_sha256': 'b' * 64,
            'effective_from': 900, 'effective_to': 4000 * 900,
            'mode': 'USD_PER_LOT', 'currency': 'USD', 'rollover_timezone': 'UTC',
            'rollover_local_time': '00:00', 'rollover_events': [
                {'at': day * 86400, 'multiplier': 1, 'rate_long': -2, 'rate_short': 1}
                for day in range(1, 42)]}}
    clock = {'status': 'synthetic_fixture', 'source_sha256': 'c' * 64,
             'effective_from': 900, 'effective_to': 4000 * 900, 'offset_seconds': 10800}
    return data, windows, costs, clock


def rehearsal(output_dir, *, sandbox=False):
    output_dir = Path(output_dir)
    output_dir.mkdir(mode=0o700)
    data, windows, costs, clock = fixtures()
    run = simulator()
    baseline = run(data, windows=windows, cost_profile=costs)
    dataset_raw, baseline_raw = encode(data), encode(baseline)
    from batch3_runner import research_module
    research = research_module()
    manifest = {'schema_version': 1, 'mode': 'synthetic-only',
        'dataset_sha256': sha(dataset_raw), 'baseline_sha256': sha(baseline_raw),
        'code_sha256': source_hashes(), 'windows': windows, 'risk': RISK,
        'policy_sha256': research.POLICY_SHA256, 'cost_sha256': digest(costs), 'clock_sha256': digest(clock)}
    packet, audit = adapt_synthetic(dataset_raw, baseline_raw, manifest, costs, clock)
    proposal = {'kind': 'ema20_slope_filter', 'lookback_bars': 3,
                'hypothesis': 'Synthetic plumbing fixture, not a research selection'}
    fixture = {'response': encode(proposal).decode(), 'tool_calls': [],
               'usage': {'input_tokens': 100, 'output_tokens': 30, 'total_tokens': 130},
               'delay_seconds': 0}
    attempt = run_fixture(packet, fixture, output_dir / 'attempt', sandbox=sandbox)
    if attempt['status'] != 'parsed_synthetic':
        raise ValueError('Synthetic runner failed')
    # Read the validated artifact, rather than bypassing the runner with the fixture.
    validated = research.parse_proposal((output_dir / 'attempt/proposal.json').read_bytes())
    registration = {'mode': 'synthetic-local-audit-only', 'manifest_sha256': digest(manifest),
                    'proposal_sha256': digest(validated), 'promotion_status': 'blocked'}
    write_once(output_dir / 'synthetic-registration.json', registration)
    candidate = run(data, windows=windows, cost_profile=costs, candidate=validated)
    if baseline != run(data, windows=windows, cost_profile=costs):
        raise ValueError('Baseline changed on repeat')
    if candidate != run(data, windows=windows, cost_profile=costs, candidate=validated):
        raise ValueError('Candidate changed on repeat')
    baseline_gate = synthetic_gate_input(baseline, manifest, clock)
    candidate_gate = synthetic_gate_input(candidate, manifest, clock)
    candidate_gate.update(declared_changes=1, evidence={
        'batch1_status': 'synthetic_not_qualified', 'cost_status': 'synthetic_not_qualified',
        'registration_at': 1, 'execution_started_at': 2})
    policy = json.loads(Path(__file__).with_name('evaluation-policy.json').read_bytes())
    if digest(policy) != research.POLICY_SHA256:
        raise ValueError('Approved policy changed')
    evaluate = runpy.run_path(str(Path(__file__).with_name('evaluate-gold.py')))['evaluate_reports']
    gate_verdict = evaluate(baseline_gate, candidate_gate, policy)
    comparison = {'mode': 'synthetic-offline-comparison', 'qualification': 'unqualified',
        'promotion_status': 'blocked', 'human_promotion_approval_required': True,
        'model_requests': 0, 'fake_requests': 1, 'repeatability': 'byte-identical',
        'gate_verdict': gate_verdict,
        'manifest_sha256': digest(manifest), 'baseline_sha256': sha(baseline_raw),
        'candidate_sha256': sha(encode(candidate)), 'proposal_sha256': digest(validated),
        'risk_sha256': digest(RISK), 'policy_sha256': research.POLICY_SHA256,
        'cost_sha256': digest(costs), 'clock_sha256': digest(clock),
        'deltas': {name: {window: {key: candidate['runs'][name]['windows'][window]['summary'][key]
                    - baseline['runs'][name]['windows'][window]['summary'][key]
            for key in ('trades', 'net_pnl_usd', 'return_pct', 'close_sampled_drawdown_pct')}
            for window in ('development', 'validation')} for name in SCENARIOS},
        'gates': ['synthetic_data', 'batch2_unqualified', 'unknown_oauth_cost',
                  'production_isolation_unverified', 'human_promotion_approval_required']}
    for name, value in (('dataset.json', data), ('baseline.json', baseline), ('manifest.json', manifest),
                        ('adapter-audit.json', audit), ('candidate.json', candidate),
                        ('baseline-gate-input.json', baseline_gate), ('candidate-gate-input.json', candidate_gate),
                        ('comparison.json', comparison)):
        write_once(output_dir / name, value)
    return comparison


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sandbox', action='store_true', help='Use the pinned cached local Docker runtime; never pull images')
    args = parser.parse_args()
    result = rehearsal(args.output, sandbox=args.sandbox)
    print('PASS: synthetic comparison saved; model_requests=0; promotion=blocked')
