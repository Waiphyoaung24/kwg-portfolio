"""Read-only M1 market and account snapshot; never submits or arms an order."""
import json
import os
import sys
import time

sys.path.insert(0, '/opt/trading')
from gold_signal import evaluate, ema
from gold_experiment import entry_allowed
from mt5_data import SYMBOL, validate_account, validate_tick


def review(mt5, login, now, offset):
    health = {}
    validate_account(mt5.account_info(), mt5.terminal_info(), login, execution=True)
    tick = mt5.symbol_info_tick(SYMBOL)
    validate_tick(tick, now, health, server_offset_seconds=offset)
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 1, 250)
    if rates is None:
        raise ValueError('M1 history unavailable')
    bars = [{key: int(row[key]) - offset if key == 'time' else float(row[key])
             for key in ('time', 'open', 'high', 'low', 'close')} for row in rates]
    result = evaluate(bars, float(tick.bid), float(tick.ask), now, bar_seconds=60)
    fast, slow, atr = result['ema20'], result['ema50'], result['atr14']
    spread = float(tick.ask) - float(tick.bid)
    trend = 'none' if fast is None or slow is None or fast == slow else 'long' if fast > slow else 'short'
    slope = ema([bar['close'] for bar in bars], 20)
    account, terminal = mt5.account_info(), mt5.terminal_info()
    positions, orders = mt5.positions_get(), mt5.orders_get()
    return dict(checked_at=now, bar_time=result['bar_time'], bid=tick.bid, ask=tick.ask,
                quote_age_seconds=health['quote_age_seconds'], atr14=atr, spread_price=spread,
                spread_limit_price=None if atr is None else atr * .1,
                spread_atr_ratio=None if atr is None or atr <= 0 else spread / atr,
                market_gate_passed=result['signal'] != 'blocked', market_reason=result['reason'],
                ema20=fast, ema50=slow, ema20_three_bar_change=slope[-1] - slope[-4],
                crossover_signal=result['signal'], trend_direction=trend,
                trend_slope_passed=entry_allowed(bars, trend, 3),
                account_match=account is not None and account.login == login,
                demo_account=account is not None and account.trade_mode == 0,
                account_trade_allowed=account is not None and account.trade_allowed and account.trade_expert,
                algo_enabled=terminal is not None and terminal.trade_allowed and not terminal.tradeapi_disabled,
                positions=None if positions is None else len(positions),
                orders=None if orders is None else len(orders), order_sent=False,
                scope='Snapshot only; journal limits, cooldown and final submission checks are not evaluated')


if __name__ == '__main__':
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise SystemExit('MT5 unavailable')
    try:
        print('ENTRY_READINESS', json.dumps(review(mt5, int(os.environ['MT5_DEMO_LOGIN']),
              time.time(), int(os.environ.get('MT5_SERVER_OFFSET_SECONDS', '0'))), allow_nan=False))
    finally:
        mt5.shutdown()
