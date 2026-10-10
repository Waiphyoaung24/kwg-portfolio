"""Inspect BTCUSD demo data and minimum-lot risk without sending or checking orders."""
import json
import math
import os
import sys
import time

sys.path.insert(0, '/opt/trading')
from gold_signal import atr
from mt5_data import validate_account, validate_tick

SYMBOL = 'BTCUSD'


def review(mt5, login, now, offset, timeframe='M1'):
    seconds = {'M1': 60, 'M5': 300, 'M15': 900}[timeframe]
    account, terminal = mt5.account_info(), mt5.terminal_info()
    validate_account(account, terminal, login, execution=True)
    if account.currency != 'USD':
        raise ValueError('Expected USD demo account')
    info, tick = mt5.symbol_info(SYMBOL), mt5.symbol_info_tick(SYMBOL)
    if info is None or info.name != SYMBOL:
        raise ValueError('BTCUSD metadata unavailable')
    health = {}
    validate_tick(tick, now, health, server_offset_seconds=offset)
    rates = mt5.copy_rates_from_pos(SYMBOL, getattr(mt5, 'TIMEFRAME_' + timeframe), 1, 250)
    if rates is None or len(rates) < 250:
        raise ValueError('Need 250 completed BTCUSD ' + timeframe + ' candles')
    bars = [{k: int(r[k]) - offset if k == 'time' else float(r[k])
             for k in ('time', 'open', 'high', 'low', 'close')} for r in rates]
    previous = None
    for bar in bars:
        prices = [bar[k] for k in ('open', 'high', 'low', 'close')]
        if (bar['time'] <= 0 or bar['time'] % seconds or
                previous is not None and bar['time'] <= previous or
                not all(math.isfinite(p) and p > 0 for p in prices) or
                bar['high'] < max(prices) or bar['low'] > min(prices)):
            raise ValueError('Invalid or unordered BTCUSD candles')
        previous = bar['time']
    timing = dict(symbol=SYMBOL, timeframe=timeframe, checked_at=now, server_offset_seconds=offset,
                  raw_last_bar_time=int(rates[-1]['time']), bar_time=bars[-1]['time'],
                  expected_bar_time=int(now // seconds) * seconds - seconds,
                  previous_bar_gap_seconds=bars[-1]['time']-bars[-2]['time'],
                  tick_time_msc=tick.time_msc, quote_age_seconds=health['quote_age_seconds'])
    if timing['bar_time'] != timing['expected_bar_time'] or timing['previous_bar_gap_seconds'] != seconds:
        return dict(**timing, candidate_market_gate_passed=False,
                    market_reason='Latest completed candle is stale or future', order_sent=False,
                    scope='History timing blocked; risk calculation not performed')
    volatility = atr(bars)[-1]
    if volatility is None or not math.isfinite(volatility) or volatility <= 0:
        raise ValueError('BTCUSD ATR is not positive')
    fields = ('name', 'trade_mode', 'trade_exemode', 'order_mode', 'filling_mode',
              'digits', 'point', 'trade_tick_size', 'trade_contract_size',
              'volume_min', 'volume_max', 'volume_step', 'trade_stops_level',
              'trade_freeze_level', 'currency_profit')
    contract = {k: getattr(info, k, None) for k in fields}
    risks = {}
    for side, direction, entry, stop in (
            ('buy', mt5.ORDER_TYPE_BUY, tick.ask, tick.ask - 2 * volatility),
            ('sell', mt5.ORDER_TYPE_SELL, tick.bid, tick.bid + 2 * volatility)):
        value = mt5.order_calc_profit(direction, SYMBOL, info.volume_min, entry, stop)
        if type(value) not in (int, float) or not math.isfinite(value) or value >= 0:
            raise ValueError('BTCUSD stop-risk calculation unavailable')
        risks[side] = -value
    validate_account(mt5.account_info(), mt5.terminal_info(), login, execution=True)
    return dict(**timing, contract=contract,
                bid=tick.bid, ask=tick.ask, spread_price=tick.ask-tick.bid,
                atr14=volatility,
                spread_atr_ratio=(tick.ask-tick.bid)/volatility,
                candidate_spread_limit_price=volatility*.25,
                candidate_market_gate_passed=tick.ask-tick.bid <= volatility*.25 + 1e-12,
                market_reason='Spread within candidate limit' if tick.ask-tick.bid <= volatility*.25 + 1e-12 else 'Spread exceeds candidate limit',
                minimum_lot_stop_risk_usd=risks,
                entry_risk_ceiling_usd=account.equity*.001,
                minimum_lot_risk_passed=max(risks.values()) <= account.equity*.001,
                order_sent=False, scope='Snapshot spread comparison; estimated 2 ATR stop risk; no signal or order validation')


if __name__ == '__main__':
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise SystemExit('MT5 unavailable')
    try:
        if not mt5.symbol_select(SYMBOL, True):
            raise SystemExit('Cannot subscribe to BTCUSD quotes')
        login = int(os.environ['MT5_DEMO_LOGIN'])
        offset = int(os.environ.get('MT5_SERVER_OFFSET_SECONDS', '0'))
        first_tick = mt5.symbol_info_tick(SYMBOL)
        # Request each history before sampling to allow terminal history loading.
        for timeframe in ('M1', 'M5', 'M15'):
            mt5.copy_rates_from_pos(SYMBOL, getattr(mt5, 'TIMEFRAME_' + timeframe), 1, 250)
        time.sleep(5)
        for timeframe in ('M1', 'M5', 'M15'):
            try:
                result = review(mt5, login, time.time(), offset, timeframe)
                result['tick_advanced'] = first_tick is not None and result['tick_time_msc'] > first_tick.time_msc
            except ValueError as exc:
                result = dict(symbol=SYMBOL, timeframe=timeframe, candidate_market_gate_passed=False,
                              reason=str(exc), order_sent=False)
            print('BTC_TIMEFRAME_REVIEW', json.dumps(result, allow_nan=False))
    except ValueError as exc:
        print('BTC_READINESS_FAILED', json.dumps(dict(reason=str(exc), order_sent=False)))
        raise SystemExit(1)
    finally:
        mt5.shutdown()
