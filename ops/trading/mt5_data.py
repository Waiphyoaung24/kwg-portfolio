"""Read-only MT5 data boundary for the pinned demo account and gold symbol."""
import math

SYMBOL = "XAUUSD-VIP"
SERVER = "VTMarkets-Demo"


class DataUnavailable(ValueError):
    """Market subscription or history has not populated yet."""


class AccountGuardError(ValueError):
    """The terminal is no longer the pinned, non-trading demo session."""


def validate_account(account, terminal, login, server=SERVER):
    if account is None or terminal is None or not terminal.connected:
        raise AccountGuardError("MT5 is not connected; sign in through the private desktop.")
    if account.trade_mode != 0 or account.login != login or account.server != server:
        raise AccountGuardError("Expected pinned demo account and server; refusing to continue.")
    if terminal.trade_allowed:
        raise AccountGuardError("Turn Algo Trading off for this read-only check.")


def validate_tick(tick, now: float) -> float:
    if tick is None:
        raise DataUnavailable("Gold quote has not populated yet.")
    bid, ask = float(tick.bid), float(tick.ask)
    raw_msc = getattr(tick, "time_msc", 0)
    stamp = float(raw_msc) / 1000 if raw_msc else float(tick.time)
    if not all(map(math.isfinite, (bid, ask, stamp, now))) or bid <= 0 or ask < bid or stamp <= 0:
        raise ValueError("Invalid gold bid/ask or timestamp.")
    age = now - stamp
    if not 0 <= age <= 30:
        raise ValueError("Gold quote is stale or timestamp is in the future.")
    return age


def read_gold(mt5, login: int, now: float) -> tuple[object, list[dict]]:
    validate_account(mt5.account_info(), mt5.terminal_info(), login)
    if not mt5.symbol_select(SYMBOL, True):
        raise DataUnavailable("Gold symbol is unavailable on the demo account.")
    tick = mt5.symbol_info_tick(SYMBOL)
    validate_tick(tick, now)
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 1, 250)
    if rates is None or len(rates) < 250:
        raise DataUnavailable("Need 250 completed gold M15 bars; history has not populated yet.")
    bars = []
    for row in rates:
        bars.append({key: int(row[key]) if key == "time" else float(row[key])
                     for key in ("time", "open", "high", "low", "close")})
    return tick, bars
