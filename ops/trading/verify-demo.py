"""Read-only connection check against a user-specified demo account."""
import argparse
import json
import time


def validate_account(account, terminal, login, server):
    if account is None or terminal is None or not terminal.connected:
        raise ValueError("MT5 is not connected; sign in through the private desktop.")
    if account.trade_mode != 0 or account.login != login or account.server != server:
        raise ValueError("Expected pinned demo account and server; refusing to continue.")
    if terminal.trade_allowed:
        raise ValueError("Turn Algo Trading off for this read-only check.")


def main():
    import MetaTrader5 as mt5

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True, type=int)
    parser.add_argument("--server", default="VTMarkets-Demo")
    args = parser.parse_args()
    if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=10000):
        raise SystemExit(f"MT5 attach failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        validate_account(account, mt5.terminal_info(), args.login, args.server)
        print(json.dumps({"demo": True, "server": account.server,
                          "currency": account.currency, "algo_trading": False}))
        for symbol in ("BTCUSD", "XAUUSD-VIP"):
            if not mt5.symbol_select(symbol, True):
                raise ValueError(f"Symbol unavailable: {symbol}")
            tick = mt5.symbol_info_tick(symbol)
            bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 1, 250)
            if tick is None or tick.bid <= 0 or tick.ask < tick.bid:
                raise ValueError(f"No valid bid/ask for {symbol}")
            if bars is None or len(bars) < 250:
                raise ValueError(f"Need 250 completed M15 bars for {symbol}; load chart history and retry.")
            print(json.dumps({"symbol": symbol, "bid": tick.bid, "ask": tick.ask,
                              "quote_age_seconds": round(time.time() - tick.time),
                              "completed_m15_bars": len(bars),
                              "latest_bar_time": int(bars[-1]["time"])}))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
