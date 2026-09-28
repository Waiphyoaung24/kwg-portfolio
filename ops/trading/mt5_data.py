"""Read-only MT5 data boundary for the pinned demo account and gold symbol."""
import math
import time

from gold_signal import evaluate

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


def validate_tick(tick, now: float, evidence: dict | None = None) -> float:
    evidence = evidence if evidence is not None else {}
    evidence.update(quote="missing", sampled_at=now, tick_time=None,
                    tick_time_msc=None, quote_age_seconds=None)
    if tick is None:
        raise DataUnavailable("Gold quote has not populated yet.")
    evidence["quote"] = "invalid"
    bid, ask = float(tick.bid), float(tick.ask)
    raw_msc = getattr(tick, "time_msc", 0)
    stamp = float(raw_msc) / 1000 if raw_msc else float(tick.time)
    if math.isfinite(float(tick.time)):
        evidence["tick_time"] = float(tick.time)
    if math.isfinite(float(raw_msc)):
        evidence["tick_time_msc"] = float(raw_msc)
    if math.isfinite(stamp) and math.isfinite(now):
        evidence["quote_age_seconds"] = now - stamp
    if not all(map(math.isfinite, (bid, ask, stamp, now))) or bid <= 0 or ask < bid or stamp <= 0:
        raise ValueError("Invalid gold bid/ask or timestamp.")
    age = now - stamp
    if age < 0:
        evidence["quote"] = "future"
        raise ValueError("Gold quote timestamp is ahead of the checking clock.")
    if age > 30:
        evidence["quote"] = "stale"
        raise ValueError("Gold quote is older than 30 seconds.")
    evidence["quote"] = "fresh"
    return age


def read_gold(mt5, login: int, now: float | None, evidence: dict | None = None) -> tuple[object, list[dict]]:
    evidence = evidence if evidence is not None else {}
    evidence.update(terminal="unknown", quote="unknown", sampled_at=now,
                    tick_time=None, tick_time_msc=None, quote_age_seconds=None,
                    history_bar_time=None, history_count=0, bid=None, ask=None,
                    spread_price=None, point=None, spread_points=None,
                    history_valid=False, expected_bar_time=None,
                    strategy_signal="blocked", strategy_reason="Not evaluated")
    account, terminal = mt5.account_info(), mt5.terminal_info()
    try:
        validate_account(account, terminal, login)
    except AccountGuardError:
        evidence.update(terminal="disconnected" if terminal is None or not terminal.connected else "guard_failed",
                        sampled_at=time.time() if now is None else now)
        raise
    evidence["terminal"] = "connected"
    if not mt5.symbol_select(SYMBOL, True):
        raise DataUnavailable("Gold symbol is unavailable on the demo account.")
    tick = mt5.symbol_info_tick(SYMBOL)
    sampled_at = time.time() if now is None else now
    evidence["expected_bar_time"] = int(sampled_at // 900) * 900 - 900
    info = mt5.symbol_info(SYMBOL)
    point = getattr(info, "point", None)
    if tick is not None:
        try:
            bid, ask = float(tick.bid), float(tick.ask)
            if math.isfinite(bid) and math.isfinite(ask):
                evidence.update(bid=bid, ask=ask, spread_price=ask - bid)
        except (TypeError, ValueError, AttributeError):
            pass
    if isinstance(point, (int, float)) and math.isfinite(point) and point > 0:
        evidence["point"] = float(point)
        if evidence["spread_price"] is not None:
            evidence["spread_points"] = evidence["spread_price"] / point
    quote_error = None
    try:
        validate_tick(tick, sampled_at, evidence)
    except ValueError as exc:
        quote_error = exc
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 1, 250)
    if rates is not None:
        evidence["history_count"] = len(rates)
        if len(rates):
            try:
                evidence["history_bar_time"] = int(rates[-1]["time"])
            except (KeyError, TypeError, ValueError, OverflowError):
                pass
    validate_account(mt5.account_info(), mt5.terminal_info(), login)
    if quote_error is not None:
        evidence["strategy_reason"] = str(quote_error)
        raise quote_error
    if evidence["point"] is None:
        evidence["strategy_reason"] = "Invalid or unavailable gold point size"
        raise ValueError(evidence["strategy_reason"])
    if rates is None or len(rates) < 250:
        raise DataUnavailable("Need 250 completed gold M15 bars; history has not populated yet.")
    bars = []
    for row in rates:
        bars.append({key: int(row[key]) if key == "time" else float(row[key])
                     for key in ("time", "open", "high", "low", "close")})
    try:
        assessment = evaluate(bars, float(tick.bid), float(tick.ask), sampled_at)
    except ValueError as exc:
        evidence["strategy_reason"] = str(exc)
        raise
    evidence["history_valid"] = assessment["reason"] != "Latest completed candle is stale or future"
    evidence["strategy_signal"] = assessment["signal"]
    evidence["strategy_reason"] = assessment["reason"]
    return tick, bars
