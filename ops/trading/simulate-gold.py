"""Hypothetical USD gold trade simulation. Offline only; never qualifies execution."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import runpy

replay = runpy.run_path(str(Path(__file__).with_name('replay-gold.py')))['replay']

# Explicit scenario inputs, not estimates of VT Markets charges.
SCENARIOS = {
    'lower': dict(commission=3.5, slippage=.05, overnight=5, spread_multiplier=1),
    'middle': dict(commission=7, slippage=.10, overnight=15, spread_multiplier=1.5),
    'stress': dict(commission=14, slippage=.30, overnight=30, spread_multiplier=2),
}


def tick_round(price, tick, up):
    return (math.ceil(price / tick - 1e-9) if up else math.floor(price / tick + 1e-9)) * tick


def protective_exit(position, bar, spread):
    """Bid OHLC for longs, synthetic ask OHLC for shorts; adverse gaps, stop first."""
    side, stop, target = position['side'], position['stop'], position['target']
    offset = spread if side == -1 else 0
    opening, high, low = (bar[key] + offset for key in ('open', 'high', 'low'))
    if side * (opening - stop) <= 0:
        return opening, 'gap_stop'
    if side * (opening - target) >= 0:
        return target, 'target'  # No favorable gap improvement assumed.
    stop_hit = low <= stop if side == 1 else high >= stop
    target_hit = high >= target if side == 1 else low <= target
    if stop_hit:
        return stop, 'stop_both_touched' if target_hit else 'stop'
    if target_hit:
        return target, 'target'
    return None


def simulate(bars, signals, spec, costs, initial=100000):
    for key in ('point', 'trade_contract_size', 'trade_tick_size', 'volume_min', 'volume_max', 'volume_step'):
        if not math.isfinite(spec[key]) or spec[key] <= 0:
            raise ValueError('Invalid contract specification')
    if spec['currency_profit'] != 'USD' or spec['volume_max'] < spec['volume_min']:
        raise ValueError('Only valid USD profit contracts supported')
    if not math.isfinite(initial) or initial <= 0 or any(not math.isfinite(v) or v < 0 for v in costs.values()):
        raise ValueError('Invalid simulation capital or costs')
    cash = peak = day_start = initial
    drawdown = 0
    position = pending = None
    day = None
    paused = False
    trades, curve = [], []
    counts = Counter()
    contract, tick = spec['trade_contract_size'], spec['trade_tick_size']

    def equity(bid, spread):
        if position is None:
            return cash
        liquidation = bid + (spread if position['side'] == -1 else 0)
        liquidation = tick_round(liquidation - position['side'] * costs['slippage'], tick, position['side'] == -1)
        return cash + position['side'] * (liquidation - position['entry']) * contract * position['lots'] - costs['commission'] / 2 * position['lots']

    def close(price, reason, stamp):
        nonlocal cash, position
        price = tick_round(price - position['side'] * costs['slippage'], tick, position['side'] == -1)
        gross = position['side'] * (price - position['entry']) * contract * position['lots']
        fee = costs['commission'] / 2 * position['lots']
        cash += gross - fee
        trades.append({**position, 'exit': price, 'exit_bar': stamp, 'exit_reason': reason,
                       'gross_pnl': gross, 'net_pnl': gross - position['fees'] - fee})
        position = None

    for index, bar in enumerate(bars):
        stamp = bar['time']
        spread = bar['spread'] * spec['point'] * costs['spread_multiplier']
        current_day = stamp // 86400
        if current_day != day:
            day_start = equity(bar['open'], spread)
            paused = False
            if position is not None:
                fee = (current_day - day) * costs['overnight'] * position['lots']
                cash -= fee
                position['fees'] += fee
            day = current_day
        paused |= equity(bar['open'], spread) <= day_start * .99
        closed = False
        # Existing stops are processed before a pending opposite-signal close.
        if position is not None:
            opening_bar = {**bar, 'high': bar['open'], 'low': bar['open']}
            hit = protective_exit(position, opening_bar, spread)
            if hit:
                close(*hit, stamp)
                closed = True
        if pending is not None and stamp == pending['bar_time'] + 900:
            side = 1 if pending['signal'] == 'long' else -1
            if position is not None and side != position['side']:
                close(bar['open'] + (spread if position['side'] == -1 else 0), 'opposite_signal', stamp)
                closed = True
            paused |= cash <= day_start * .99 if position is None else False
            if position is None and not closed and not paused:
                volatility = pending['atr14']
                if spread > volatility * .1 + 1e-12:
                    counts['entry_spread_rejected'] += 1
                else:
                    entry = tick_round(bar['open'] + (spread if side == 1 else 0) + side * costs['slippage'], tick, side == 1)
                    stop = tick_round(entry - side * 2 * volatility, tick, side == -1)
                    target = tick_round(entry + side * 3 * volatility, tick, side == 1)
                    per_lot_risk = (abs(entry - stop) + costs['slippage'] + tick) * contract + costs['commission']
                    limit = min(spec['volume_max'], max(0, cash) * .001 / per_lot_risk)
                    lots = math.floor(limit / spec['volume_step']) * spec['volume_step']
                    if lots + 1e-12 < spec['volume_min']:
                        counts['below_minimum_lot'] += 1
                    else:
                        fee = costs['commission'] / 2 * lots
                        cash -= fee
                        position = dict(side=side, entry=entry, entry_bar=stamp, signal_bar=pending['bar_time'],
                                        stop=stop, target=target, lots=lots, fees=fee)
            elif paused:
                counts['daily_pause_rejected'] += 1
        elif pending is not None:
            counts['gap_entry_cancelled'] += 1
        pending = None
        if position is not None:
            hit = protective_exit(position, bar, spread)
            if hit:
                close(*hit, stamp)
        if index == len(bars) - 1 and position is not None:
            close(bar['close'] + (spread if position['side'] == -1 else 0), 'window_end', stamp)
        marked = equity(bar['close'], spread)
        peak = max(peak, marked)
        drawdown = max(drawdown, (peak - marked) / peak)
        paused |= marked <= day_start * .99
        curve.append({'bar_time': stamp, 'equity': marked})
        signal = signals.get(stamp)
        if index > 0 and signal and signal['signal'] in ('long', 'short'):
            pending = signal
    gains = sum(max(0, t['net_pnl']) for t in trades)
    losses = -sum(min(0, t['net_pnl']) for t in trades)
    return {'summary': {'trades': len(trades), 'net_pnl_usd': cash - initial,
                       'return_pct': (cash / initial - 1) * 100, 'close_sampled_drawdown_pct': drawdown * 100,
                       'win_rate_pct': sum(t['net_pnl'] > 0 for t in trades) / len(trades) * 100 if trades else None,
                       'expectancy_usd_per_trade': (cash - initial) / len(trades) if trades else None,
                       'profit_factor': gains / losses if losses else None,
                       'round_trip_lots': sum(t['lots'] for t in trades), 'skips': dict(counts)},
            'trades': trades, 'equity_curve': curve}


def run(data):
    bars = data['bars']
    if len(bars) < 1000:
        raise ValueError('Need 1000 bars for chronological diagnostic windows')
    dev_end, validation_end = int(len(bars) * .6), int(len(bars) * .8)
    # No evaluation or performance inspection on the reserved newest 20%.
    available = {**data, 'bars': bars[:validation_end]}
    signals = {d['bar_time']: d for d in replay(available)['decisions']}
    runs = {}
    for name, costs in SCENARIOS.items():
        # Signal gate uses recorded spread; entry gate applies the scenario stress.
        runs[name] = {'costs': costs, 'windows': {}}
        for window, start, end in [('development', 249, dev_end), ('validation', dev_end, validation_end)]:
            result = simulate(bars[start:end], signals, data['current_contract_specification'], costs)
            result['first_bar'], result['last_bar'] = bars[start]['time'], bars[end - 1]['time']
            runs[name]['windows'][window] = result
    return {'mode': 'hypothetical-trade-simulation', 'qualification': 'unqualified', 'initial_usd_per_window': 100000,
            'holdout': {'start_index': validation_end, 'bars': len(bars) - validation_end, 'evaluated': False},
            'rules': ['Completed EMA20/50 crossover; ATR14; next adjacent bar open entry',
                      'Risk 0.1% equity including modeled stop exit costs; stop 2 ATR; target 3 ATR',
                      'One position; opposite signal closes without same-bar reversal',
                      'Stop first if stop and target both touched; gaps filled adversely',
                      'Daily 1% entry pause observed at bar open/close; not a guaranteed loss cap',
                      'Window boundaries liquidate and reset; no positions cross validation boundaries'],
            'cost_units': {'commission': 'USD per lot round trip', 'slippage': 'USD price per side',
                           'overnight': 'USD per lot per raw-epoch calendar day', 'spread_multiplier': 'recorded bar spread multiplier'},
            'limitations': ['All costs hypothetical; current contract assumed historically constant',
                            'OHLC assumed bid; bar spread held constant intrabar; no historical ask path',
                            'No margin, broker rejection, latency or intrabar daily-pause modeling',
                            'Flat overnight debit is not historical broker swap or triple-roll schedule',
                            'Raw timestamp semantics and live freshness remain unqualified',
                            'Drawdown sampled at closes; no statistical evidence or promotion gate passed'],
            'runs': runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.dataset.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.sha256.lower():
        parser.error('Dataset checksum mismatch')
    report = run(json.loads(raw))
    report['dataset_sha256'] = args.sha256.lower()
    report['code_sha256'] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                             for name in ('simulate-gold.py', 'replay-gold.py', 'gold_signal.py')}
    encoded = (json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with args.output.open('xb') as output:
        output.write(encoded)
    for name, scenario in report['runs'].items():
        for window, result in scenario['windows'].items():
            print(name, window, json.dumps(result['summary']))
    print('Report SHA256:', hashlib.sha256(encoded).hexdigest())


if __name__ == '__main__':
    main()
