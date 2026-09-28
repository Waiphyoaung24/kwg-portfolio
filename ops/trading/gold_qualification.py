"""Reduce bounded, read-only MT5 samples to a live-data evidence result."""
import math


def qualify_samples(samples: list[dict]) -> dict:
    segment = []
    transitions = []
    blockers = []
    for sample in samples:
        stamp = sample.get('sampled_at')
        age = sample.get('quote_age_seconds')
        tick = sample.get('tick_time_msc')
        bar = sample.get('history_bar_time')
        spread = sample.get('spread_price')
        valid = (type(stamp) in (int, float) and math.isfinite(stamp)
                 and type(age) in (int, float) and math.isfinite(age) and 0 <= age <= 30
                 and type(tick) in (int, float) and math.isfinite(tick) and tick > 0
                 and type(bar) is int and bar > 0
                 and sample.get('quote') == 'fresh' and sample.get('terminal') == 'connected'
                 and sample.get('history_valid') is True
                 and type(sample.get('history_count')) is int and sample['history_count'] >= 250
                 and bar == int(stamp // 900) * 900 - 900
                 and type(spread) in (int, float) and math.isfinite(spread) and spread >= 0)
        if valid and segment:
            previous = segment[-1]
            step = stamp - previous['sampled_at']
            bar_step = bar - previous['history_bar_time']
            valid = 0 < step <= 10 and tick >= previous['tick_time_msc'] and bar_step in (0, 900)
        if not valid:
            segment = []
            transitions = []
            blockers = ['missing, invalid or discontinuous live sample']
            continue
        if segment and bar != segment[-1]['history_bar_time']:
            transitions.append(bar)
        segment.append(sample)
        blockers = []
    spread_values = sorted(s['spread_price'] for s in segment)
    def percentile(p):
        return spread_values[max(0, math.ceil(len(spread_values) * p) - 1)] if spread_values else None
    duration = segment[-1]['sampled_at'] - segment[0]['sampled_at'] if segment else 0
    advancing_ticks = any(b['tick_time_msc'] > a['tick_time_msc'] for a, b in zip(segment, segment[1:]))
    passed = len(segment) >= 361 and duration >= 1800 and len(transitions) >= 2 and advancing_ticks
    if not passed and not blockers:
        blockers = ['need 1800 continuous seconds, 361 samples and two advancing M15 bars']
    return {'data_status': 'passed' if passed else 'inconclusive', 'blockers': blockers,
            'transition_bar_times': transitions, 'accepted_sample_count': len(segment),
            'spread_summary': {'unit': 'price', 'sample_count': len(spread_values),
                               'p50_price': percentile(.5), 'p95_price': percentile(.95),
                               'max_price': spread_values[-1] if spread_values else None}}
