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


class AlgoTradingOn(AccountGuardError):
    """The pinned demo is connected, but read-only observation is paused."""


def validate_account(account, terminal, login, server=SERVER, *, execution=False):
    if account is None or terminal is None or not terminal.connected:
        raise AccountGuardError("MT5 is not connected; sign in through the private desktop.")
    if account.trade_mode != 0 or account.login != login or account.server != server:
        raise AccountGuardError("Expected pinned demo account and server; refusing to continue.")
    if execution:
        if (not terminal.trade_allowed or getattr(terminal, "tradeapi_disabled", True)
                or not getattr(account, "trade_allowed", False)
                or not getattr(account, "trade_expert", False)):
            raise AccountGuardError("Demo execution is disabled in the account or terminal.")
    elif terminal.trade_allowed:
        raise AlgoTradingOn("Turn Algo Trading off for this read-only check.")


def validate_tick(tick, now: float, evidence: dict | None = None, *, server_offset_seconds: int = 0) -> float:
    if server_offset_seconds not in (0, 7200, 10800):
        raise ValueError("Unsupported server clock offset.")
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
    normalized_stamp = stamp - server_offset_seconds
    if math.isfinite(normalized_stamp) and math.isfinite(now):
        evidence["quote_age_seconds"] = now - normalized_stamp
    if not all(map(math.isfinite, (bid, ask, stamp, now))) or bid <= 0 or ask < bid or stamp <= 0:
        raise ValueError("Invalid gold bid/ask or timestamp.")
    age = now - normalized_stamp
    if age < 0:
        evidence["quote"] = "future"
        raise ValueError("Gold quote timestamp is ahead of the checking clock.")
    if age > 30:
        evidence["quote"] = "stale"
        raise ValueError("Gold quote is older than 30 seconds.")
    evidence["quote"] = "fresh"
    return age


def read_contract(mt5) -> dict:
    """Allowlisted current symbol properties; commission is not exposed here."""
    info = mt5.symbol_info(SYMBOL)
    fields = ('name', 'chart_mode', 'digits', 'point', 'trade_tick_size',
              'trade_tick_value', 'trade_contract_size', 'currency_profit',
              'currency_margin', 'volume_min', 'volume_max', 'volume_step',
              'trade_calc_mode', 'swap_mode', 'swap_long', 'swap_short',
              'swap_rollover3days')
    return {field: getattr(info, field, None) for field in fields} | {'commission': None}


def read_gold(mt5, login: int, now: float | None, evidence: dict | None = None,
              *, server_offset_seconds: int = 0, execution: bool = False) -> tuple[object, list[dict]]:
    if server_offset_seconds not in (0, 7200, 10800):
        raise ValueError("Unsupported server clock offset.")
    evidence = evidence if evidence is not None else {}
    evidence.update(terminal="unknown", quote="unknown", sampled_at=now,
                    tick_time=None, tick_time_msc=None, quote_age_seconds=None,
                    history_bar_time=None, history_count=0, bid=None, ask=None,
                    spread_price=None, point=None, spread_points=None,
                    history_valid=False, expected_bar_time=None,
                    strategy_signal="blocked", strategy_reason="Not evaluated")
    account, terminal = mt5.account_info(), mt5.terminal_info()
    try:
        validate_account(account, terminal, login, execution=execution)
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
        validate_tick(tick, sampled_at, evidence, server_offset_seconds=server_offset_seconds)
    except ValueError as exc:
        quote_error = exc
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 1, 250)
    if rates is not None:
        evidence["history_count"] = len(rates)
        if len(rates):
            try:
                raw_bar_time = int(rates[-1]["time"])
                evidence["history_bar_time"] = raw_bar_time - server_offset_seconds
                if server_offset_seconds:
                    evidence["raw_history_bar_time"] = raw_bar_time
            except (KeyError, TypeError, ValueError, OverflowError):
                pass
    validate_account(mt5.account_info(), mt5.terminal_info(), login, execution=execution)
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
        bars.append({key: int(row[key]) - server_offset_seconds if key == "time" else float(row[key])
                     for key in ("time", "open", "high", "low", "close")})
    try:
        assessment = evaluate(bars, float(tick.bid), float(tick.ask), sampled_at)
    except ValueError as exc:
        evidence["strategy_reason"] = str(exc)
        raise
    evidence["history_valid"] = assessment["reason"] != "Latest completed candle is stale or future"
    evidence["strategy_signal"] = assessment["signal"]
    evidence["strategy_reason"] = assessment["reason"]
    if execution and assessment["signal"] == "blocked":
        raise ValueError(assessment["reason"])
    return tick, bars
