"""Development-only comparison of the frozen gold baseline and four allowed filters."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

from gold_experiment import RISK, SCENARIOS, digest, experiment_identity, source_hashes

HERE = Path(__file__).parent
simulate = runpy.run_path(str(HERE / 'simulate-gold.py'))['simulate']
replay = runpy.run_path(str(HERE / 'replay-gold.py'))['replay']


def grid(data, manifest):
    # The frozen experiment has 6,000 development bars, including warm-up.
    # No configurable end index can extend selection into validation or reserved bars.
    bars = data.get('bars', [])
    if (manifest.get('status') != 'frozen' or len(bars) != 10000
            or manifest.get('reserved_start_index') != 8000
            or manifest.get('code_sha256') != source_hashes()
            or manifest.get('risk') != RISK or manifest.get('scenarios') != SCENARIOS):
        raise ValueError('Expected the unchanged frozen gold experiment')
    dev = {**data, 'bars': bars[:6000]}
    if manifest.get('windows', {}).get('development') != {
            'start': dev['bars'][249]['time'], 'end': dev['bars'][-1]['time']}:
        raise ValueError('Development window mismatch')
    rows = []
    for lookback in (None, 2, 3, 4, 5):
        candidate = None if lookback is None else {
            'kind': 'ema20_slope_filter', 'lookback_bars': lookback, 'hypothesis': 'deterministic grid'}
        signals = {d['bar_time']: d for d in replay(dev, candidate=candidate)['decisions']}
        summary = simulate(dev['bars'][249:], signals, data['current_contract_specification'],
                           SCENARIOS['middle'])['summary']
        rows.append({'lookback_bars': lookback, 'trades': summary['trades'],
                     'net_pnl_usd': summary['net_pnl_usd'],
                     'drawdown_pct': summary['close_sampled_drawdown_pct']})
    # Ties retain the baseline, then the shorter lookback. Selection is not promotion.
    best = max(rows, key=lambda row: (row['net_pnl_usd'], -(row['lookback_bars'] or 0)))
    return {'mode': 'development-only-grid', 'qualification': 'unqualified',
            'cost_profile_status': 'hypothetical', 'scenario': 'middle', 'dev_end_index': 6000,
            'identity': experiment_identity(manifest), 'manifest_sha256': digest(manifest),
            'development_input_sha256': digest(dev),
            'grid_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'policy_sha256': digest(json.loads((HERE / 'evaluation-policy.json').read_text())),
            'risk_sha256': digest(RISK), 'rows': rows, 'selected': best['lookback_bars']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    raw = args.dataset.read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest.get('dataset_sha256'):
        parser.error('Dataset checksum mismatch')
    report = grid(json.loads(raw), manifest)
    with args.output.open('x') as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write('\n')


if __name__ == '__main__':
    main()
