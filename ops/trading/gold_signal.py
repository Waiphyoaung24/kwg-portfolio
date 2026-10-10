"""Pure, signal-only gold crossover calculation on completed M15 bars."""
import math
from instruments import GOLD, BTC, validate_market


def ema(values: list[float], period: int) -> list[float | None]:
    if period < 1:
        raise ValueError("EMA period must be positive")
    out = [None] * len(values)
    if len(values) < period:
        return out
    level = sum(values[:period]) / period
    out[period - 1] = level
    weight = 2 / (period + 1)
    for index in range(period, len(values)):
        level += weight * (values[index] - level)
        out[index] = level
    return out


def atr(bars: list[dict], period: int = 14) -> list[float | None]:
    if period < 1:
        raise ValueError("ATR period must be positive")
    out = [None] * len(bars)
    if len(bars) <= period:
        return out
    ranges = [max(bar["high"] - bar["low"],
                  abs(bar["high"] - bars[index - 1]["close"]),
                  abs(bar["low"] - bars[index - 1]["close"]))
              for index, bar in enumerate(bars) if index]
    level = sum(ranges[:period]) / period
    out[period] = level
    for index in range(period + 1, len(bars)):
        level = (level * (period - 1) + ranges[index - 1]) / period
        out[index] = level
    return out


def evaluate(bars: list[dict], bid: float, ask: float, now: float, *, bar_seconds: int = 900, trend_demo: bool = False, symbol: str = GOLD) -> dict:
    validate_market(symbol, bar_seconds, trend_demo)
    if type(bar_seconds) is not int or bar_seconds not in (60, 900):
        raise ValueError('Only M1 and M15 candles are supported')
    if type(trend_demo) is not bool or trend_demo and bar_seconds != (900 if symbol == BTC else 60):
        raise ValueError('Trend demo spread policy requires M1 candles')
    if len(bars) < 250:
        raise ValueError("Need 250 completed gold bars")
    bars = bars[-250:]
    if not all(math.isfinite(value) for value in (bid, ask, now)) or bid <= 0 or ask < bid:
        raise ValueError("Invalid bid/ask")
    previous_time = None
    for bar in bars:
        stamp = bar["time"]
        prices = [bar[key] for key in ("open", "high", "low", "close")]
        if (not isinstance(stamp, int) or stamp <= 0 or stamp % bar_seconds != 0 or
                previous_time is not None and stamp <= previous_time or
                not all(math.isfinite(value) and value > 0 for value in prices) or
                bar["high"] < max(prices[0], prices[3], bar["low"]) or
                bar["low"] > min(prices[0], prices[3])):
            raise ValueError("Invalid or unordered bars")
        previous_time = stamp
    result = {"bar_time": bars[-1]["time"], "signal": "blocked", "reason": "",
              "ema20": None, "ema50": None, "atr14": None}
    if bars[-1]["time"] != math.floor(now / bar_seconds) * bar_seconds - bar_seconds or bars[-1]["time"] - bars[-2]["time"] != bar_seconds:
        result["reason"] = "Latest completed candle is stale or future"
        return result
    closes = [bar["close"] for bar in bars]
    fast, slow, volatility = ema(closes, 20), ema(closes, 50), atr(bars)
    result.update(ema20=fast[-1], ema50=slow[-1], atr14=volatility[-1])
    if volatility[-1] <= 0 or ask - bid > volatility[-1] * (.25 if trend_demo else .1) + 1e-12:
        result["reason"] = "ATR or spread outside allowed range"
        return result
    if fast[-2] <= slow[-2] and fast[-1] > slow[-1]:
        result["signal"] = "long"
    elif fast[-2] >= slow[-2] and fast[-1] < slow[-1]:
        result["signal"] = "short"
    else:
        result["signal"] = "none"
    result["reason"] = "evaluated"
    return result
