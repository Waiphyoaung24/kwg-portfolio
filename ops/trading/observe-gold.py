"""Persist read-only gold signals; there is intentionally no order path."""
import argparse
import json
import sqlite3
import time
from pathlib import Path

from gold_signal import evaluate
from mt5_data import AccountGuardError, AlgoTradingOn, DataUnavailable, SERVER, SYMBOL, read_gold

VERSION = "gold-ema-v1"
SNAPSHOT = Path(r"Z:\opt\status\latest.json")


def open_state(path: Path, login: int) -> sqlite3.Connection:
    path = Path(path)
    existed = path.exists()
    db = sqlite3.connect(path, autocommit=False)
    try:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("Observer state failed integrity check")
        if not existed:
            db.execute("CREATE TABLE metadata (login INTEGER NOT NULL, server TEXT NOT NULL, symbol TEXT NOT NULL, version TEXT NOT NULL)")
            db.execute("CREATE TABLE observations (bar_time INTEGER PRIMARY KEY, status TEXT NOT NULL, signal TEXT NOT NULL, observed_at REAL NOT NULL, payload TEXT NOT NULL)")
            db.execute("INSERT INTO metadata VALUES (?, ?, ?, ?)", (login, SERVER, SYMBOL, VERSION))
            db.commit()
        record = db.execute("SELECT login, server, symbol, version FROM metadata").fetchall()
        if record != [(login, SERVER, SYMBOL, VERSION)]:
            raise ValueError("Observer state belongs to another account, symbol, or strategy version")
        return db
    except BaseException:
        db.close()
        raise


def record_observation(db: sqlite3.Connection, result: dict, observed_at: float, bootstrap: bool) -> bool:
    latest = db.execute("SELECT max(bar_time) FROM observations").fetchone()[0]
    bar_time = result["bar_time"]
    if latest is not None and bar_time <= latest:
        result["status"] = "duplicate"
        result["signal"] = "none"
        result["reason"] = "Candle already recorded"
        return False
    status = "baseline" if bootstrap or latest is None or bar_time - latest != 900 else "observed"
    result["status"] = status
    if status == "baseline":
        result["signal"] = "none"
        result["reason"] = "Startup or missed candle baseline"
    with db:
        db.execute("INSERT INTO observations VALUES (?, ?, ?, ?, ?)",
                   (bar_time, status, result["signal"], observed_at, json.dumps(result, allow_nan=False)))
    return True


def poll_once(mt5, db: sqlite3.Connection, login: int, now: float | None, bootstrap: bool,
              server_offset_seconds: int = 0) -> dict:
    health = {}
    try:
        tick, bars = read_gold(mt5, login, now, health, server_offset_seconds=server_offset_seconds)
        now = health["sampled_at"]
        result = evaluate(bars, float(tick.bid), float(tick.ask), now)
    except AlgoTradingOn as exc:
        return {"mode": "signal-only", "symbol": SYMBOL, "status": "blocked",
                "signal": "none", "reason": str(exc), "health": health}
    except AccountGuardError as exc:
        exc.health = health
        raise
    except (DataUnavailable, ValueError) as exc:
        return {"mode": "signal-only", "symbol": SYMBOL, "status": "blocked",
                "signal": "none", "reason": str(exc), "health": health}
    finally:
        if health.get("tick_time") is not None:
            health["tick_time"] -= server_offset_seconds
        if health.get("tick_time_msc") is not None:
            health["tick_time_msc"] -= server_offset_seconds * 1000
    result.update(mode="signal-only", symbol=SYMBOL, health=health)
    if result["signal"] == "blocked":
        result["status"] = "blocked"
        result["signal"] = "none"
        return result
    record_observation(db, result, now, bootstrap)
    return result


def write_snapshot(path: Path, db: sqlite3.Connection, result: dict, now: float) -> None:
    """Publish only display fields to the volume shared with the status origin."""
    last_bar = db.execute("SELECT max(bar_time) FROM observations").fetchone()[0]
    payload = {"mode": "signal-only", "symbol": SYMBOL,
               "status": result["status"], "signal": result["signal"],
               "reason": result.get("reason", ""), "checked_at": int(now),
               "bar_time": result.get("bar_time", last_bar),
               "health": result.get("health")}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True, type=int)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--server-offset-seconds", type=int, choices=(0, 7200, 10800), default=0)
    args = parser.parse_args()
    state = args.state.resolve()
    if not state.is_relative_to(Path.home().resolve()) or state.is_dir():
        parser.error("--state must be a file inside the persistent MT5 home directory")
    import MetaTrader5 as mt5

    if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=10000):
        raise SystemExit(f"MT5 attach failed: {mt5.last_error()}")
    db = None
    try:
        db = open_state(state, args.login)
        bootstrap = True
        while True:
            started = time.monotonic()
            result = poll_once(mt5, db, args.login, None, bootstrap, args.server_offset_seconds)
            write_snapshot(SNAPSHOT, db, result, time.time())
            print(json.dumps(result, allow_nan=False), flush=True)
            bootstrap = result["status"] == "blocked" or (bootstrap and result["status"] == "duplicate")
            if args.once:
                break
            time.sleep(max(0, 5 - (time.monotonic() - started)))
    except KeyboardInterrupt:
        pass
    except (AccountGuardError, ValueError, sqlite3.Error) as exc:
        if isinstance(exc, AccountGuardError) and db is not None:
            write_snapshot(SNAPSHOT, db, {"status": "blocked", "signal": "none",
                           "reason": str(exc), "health": exc.health}, time.time())
        raise SystemExit(f"Observer stopped: {exc}") from exc
    finally:
        if db is not None:
            db.close()
        mt5.shutdown()


if __name__ == "__main__":
    main()
