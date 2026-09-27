"""Read-only freshness and history check for the pinned gold demo account."""
import argparse
import json
import time
from datetime import datetime, timezone

from mt5_data import DataUnavailable, SYMBOL, read_gold, validate_tick


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True, type=int)
    args = parser.parse_args()
    import MetaTrader5 as mt5

    if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=10000):
        raise SystemExit(f"MT5 attach failed: {mt5.last_error()}")
    try:
        deadline = time.monotonic() + 15
        while True:
            now = time.time()
            try:
                tick, bars = read_gold(mt5, args.login, now)
                break
            except DataUnavailable:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        print(json.dumps({"symbol": SYMBOL,
                          "host_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                          "tick_time": int(tick.time),
                          "quote_age_seconds": round(validate_tick(tick, now), 3),
                          "completed_m15_bars": len(bars),
                          "latest_bar_time": bars[-1]["time"],
                          "reason": "ready"}))
    except ValueError as exc:
        raise SystemExit(f"Gold readiness blocked: {exc}") from exc
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
