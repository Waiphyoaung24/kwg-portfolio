"""Replay frozen gold signal rules offline; no orders or profitability claims."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from gold_signal import evaluate
from gold_experiment import entry_allowed, validate_candidate


def replay(data, *, candidate=None):
    if candidate is not None:
        validate_candidate(candidate)
    if (data.get('schema_version') != 1 or data.get('symbol') != 'XAUUSD-VIP'
            or data.get('timeframe') != 'M15' or data.get('source', {}).get('start_pos') != 1):
        raise ValueError('Expected a completed-bar gold export')
    bars = data['bars']
    point = data['current_contract_specification']['point']
    captured = data['captured_at']
    if not math.isfinite(point) or point <= 0 or not math.isfinite(captured) or len(bars) < 251:
        raise ValueError('Invalid specification, capture time or history length')
    for bar in bars:
        if type(bar['spread']) is not int or bar['spread'] < 0:
            raise ValueError('Invalid historical spread')
    counts, reasons = Counter(), Counter()
    decisions = []
    last_recorded = None
    bootstrap = True
    # ponytail: O(n * 250) exactly matches the runner's rolling indicator seeds.
    # Keep this until profiling justifies an equivalent optimized calculation.
    for index in range(249, len(bars)):
        bar = bars[index]
        result = evaluate(bars[index - 249:index + 1], bar['close'],
                          bar['close'] + bar['spread'] * point, bar['time'] + 900)
        signal = result['signal']
        if signal == 'blocked':
            counts['blocked'] += 1
            reasons[result['reason']] += 1
            bootstrap = True
        else:
            if bootstrap or last_recorded is None or bar['time'] - last_recorded != 900:
                counts['baseline_reset'] += 1
                signal = 'none'
            else:
                counts[signal] += 1
            last_recorded = bar['time']
            bootstrap = False
        decision = {'bar_time': bar['time'], 'signal': signal, 'reason': result['reason'],
                    'atr14': result['atr14']}
        if candidate is not None:
            decision['entry_allowed'] = entry_allowed(bars[index - 249:index + 1], signal,
                                                       candidate['lookback_bars'])
        decisions.append(decision)
    return {
        'mode': 'historical-signal-replay', 'qualification': 'unqualified',
        'baseline': 'gold-ema-v1', 'bars': len(bars), 'warmup_bars': 249,
        'first_evaluated_bar': bars[249]['time'], 'last_evaluated_bar': bars[-1]['time'],
        'counts': dict(sorted(counts.items())), 'blocked_reasons': dict(sorted(reasons.items())),
        'assumptions': [
            'Evaluation occurs after each completed bar; no later candles enter the calculation',
            'Bid proxy is bar close; ask proxy adds recorded bar spread times current point size',
            'Startup and first accepted bar after a block or gap suppress signals, matching observer',
            'Live tick availability and actual execution spreads cannot be recreated from OHLC'],
        'limitations': ['No fills, positions, commission, slippage, swap or profit calculation',
                        'Not evidence of live freshness, candle transitions or trading performance'],
        'source_qualification': data.get('qualification'), 'decisions': decisions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.dataset.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != args.sha256.lower():
        parser.error('Dataset checksum mismatch')
    report = replay(json.loads(raw))
    report['dataset_sha256'] = digest
    report['code_sha256'] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                             for name in ('replay-gold.py', 'gold_signal.py')}
    encoded = (json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with args.output.open('xb') as output:
        output.write(encoded)
    print(json.dumps({key: report[key] for key in ('mode', 'qualification', 'bars', 'counts', 'blocked_reasons')}))
    print('Report SHA256:', hashlib.sha256(encoded).hexdigest())


if __name__ == '__main__':
    main()
