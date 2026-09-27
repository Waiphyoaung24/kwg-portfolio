"""Freeze broker gold history for research; never qualifies data or places orders."""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from mt5_data import SERVER, SYMBOL, validate_account, validate_tick

BAR_FIELDS = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")
INTEGER_FIELDS = ("time", "tick_volume", "spread", "real_volume")
SPEC_NUMBERS = ("digits", "point", "trade_contract_size", "trade_tick_size",
                "trade_tick_value", "trade_calc_mode", "volume_min", "volume_max",
                "volume_step", "swap_mode", "swap_long", "swap_short", "swap_rollover3days")


def snapshot(rates, info, requested: int, captured_at: float, sdk_version: str, quote: dict) -> dict:
    if rates is None or len(rates) < 251:
        raise ValueError("Need at least 251 historical bars; synchronize MT5 chart history and retry.")
    bars = []
    previous = 0
    gaps = []
    for row in rates:
        bar = {}
        for key in BAR_FIELDS:
            value = float(row[key])
            if not math.isfinite(value) or value < 0 or (key in INTEGER_FIELDS and value != int(value)):
                raise ValueError("Non-finite, negative or fractional integer history field")
            bar[key] = int(value) if key in INTEGER_FIELDS else value
        stamp = bar["time"]
        prices = [bar[key] for key in ("open", "high", "low", "close")]
        if (stamp <= previous or stamp % 900 or min(prices) <= 0
                or bar["high"] < max(prices) or bar["low"] > min(prices)):
            raise ValueError("Invalid OHLC or unordered/alignment-invalid M15 history")
        if previous and stamp - previous != 900:
            gaps.append({"after": previous, "before": stamp, "seconds": stamp - previous})
        previous = stamp
        bars.append(bar)
    specification = {}
    for key in SPEC_NUMBERS:
        value = getattr(info, key, None)
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError("Invalid contract specification")
        specification[key] = value
    for key in ("currency_base", "currency_profit", "currency_margin"):
        value = getattr(info, key, None)
        if value is not None and (not isinstance(value, str) or len(value) > 16):
            raise ValueError("Invalid contract currency")
        specification[key] = value
    return {
        "schema_version": 1, "symbol": SYMBOL, "timeframe": "M15", "captured_at": captured_at,
        "source": {"server": SERVER, "sdk_version": sdk_version, "start_pos": 1,
                   "requested_bars": requested, "timestamp_basis": "raw MT5 epoch; broker semantics unqualified"},
        "qualification": {"status": "unqualified", "blockers": [
            "Open-session timestamp and freshness qualification pending",
            "Historical commission, slippage and overnight costs not supplied",
            "Bar spread is not a historical bid/ask execution path",
            "Current contract specification is not historical contract evidence"]},
        "coverage": {"bars": len(bars), "first_bar": bars[0]["time"], "last_bar": bars[-1]["time"],
                     "partial_request": len(bars) < requested, "gaps": gaps,
                     "zero_spread_bars": sum(bar["spread"] == 0 for bar in bars),
                     "bars_not_completed_by_host_clock": sum(bar["time"] + 900 > captured_at for bar in bars)},
        "current_contract_specification": specification, "latest_quote_check": quote,
        "cost_assumptions": {"commission": None, "slippage": None, "historical_overnight_costs": None},
        "bars": bars,
    }


def save_snapshot(path: Path, data: dict) -> str:
    encoded = (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with path.open("xb") as output:  # Never overwrite an experiment's source dataset.
        output.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", type=int, required=True)
    parser.add_argument("--bars", type=int, default=10000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if not 251 <= args.bars <= 100000:
        parser.error("--bars must be between 251 and 100000")
    if not target.is_relative_to(Path.home().resolve()) or not target.parent.is_dir():
        parser.error("--output must be in an existing directory inside the persistent MT5 home")
    if target.exists():
        parser.error("Output already exists; choose a new dataset filename")
    import MetaTrader5 as mt5
    if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=10000):
        raise SystemExit("MT5 attach failed; use the private desktop to check the session.")
    try:
        validate_account(mt5.account_info(), mt5.terminal_info(), args.login)
        if not mt5.symbol_select(SYMBOL, True):
            raise ValueError("Gold symbol unavailable")
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 1, args.bars)
        info = mt5.symbol_info(SYMBOL)
        if info is None:
            raise ValueError("Gold contract specification unavailable")
        tick = mt5.symbol_info_tick(SYMBOL)
        captured_at = time.time()
        quote = {}
        try:
            validate_tick(tick, captured_at, quote)
        except ValueError:
            pass  # Historical capture is allowed while the live quote is blocked.
        validate_account(mt5.account_info(), mt5.terminal_info(), args.login)
        data = snapshot(rates, info, args.bars, captured_at, mt5.__version__, quote)
        digest = save_snapshot(target, data)
        print(json.dumps({"symbol": SYMBOL, "bars": data["coverage"]["bars"],
                          "first_bar": data["coverage"]["first_bar"], "last_bar": data["coverage"]["last_bar"],
                          "partial_request": data["coverage"]["partial_request"],
                          "qualification": "unqualified", "sha256": digest, "output": str(target)}))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise SystemExit(f"Export refused: {exc}") from exc
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
