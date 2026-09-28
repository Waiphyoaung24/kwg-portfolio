"""Read-only freshness and history check for the pinned gold demo account."""
import argparse
import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

from mt5_data import AccountGuardError, DataUnavailable, SYMBOL, read_contract, read_gold, validate_tick
from gold_signal import evaluate
from gold_qualification import qualify_samples


def collect(mt5, login: int, seconds: int, server_offset_seconds: int = 0) -> dict:
    started = time.time()
    deadline = time.monotonic() + seconds
    samples = []
    failure = None
    contract = None
    try:
        while len(samples) < 721:
            began = time.monotonic()
            health = {}
            try:
                read_gold(mt5, login, None, health, server_offset_seconds=server_offset_seconds)
                if contract is None:
                    contract = read_contract(mt5)
            except AccountGuardError as exc:
                failure = str(exc)
                break
            except (DataUnavailable, ValueError):
                pass
            samples.append(health)
            if qualify_samples(samples)['data_status'] == 'passed' or time.monotonic() >= deadline:
                break
            time.sleep(max(0, 5 - (time.monotonic() - began)))
    except KeyboardInterrupt:
        failure = 'Collection interrupted'
    outcome = qualify_samples(samples)
    if failure:
        outcome.update(data_status='inconclusive', blockers=[failure])
    return {'schema_version': 1, 'mode': 'read-only-qualification', 'symbol': SYMBOL,
            'server_offset_seconds': server_offset_seconds,
            'started_at': started, 'ended_at': time.time(), 'sdk_version': mt5.__version__,
            'code_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                            for name in ('verify-demo.py', 'mt5_data.py', 'gold_qualification.py', 'gold_signal.py')},
            'sample_interval_seconds': 5, 'samples': samples, 'contract': contract,
            'cost_status': 'incomplete', **outcome}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True, type=int)
    parser.add_argument("--collect-seconds", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--server-offset-seconds", type=int, choices=(0, 7200, 10800), default=0,
                        help="Diagnostic clock offset confirmed against MT5 Market Watch; live observer is unchanged")
    args = parser.parse_args()
    if (args.collect_seconds is None) != (args.output is None):
        parser.error("--collect-seconds and --output must be supplied together")
    if args.collect_seconds is not None:
        if not 60 <= args.collect_seconds <= 3600:
            parser.error("--collect-seconds must be 60–3600")
        target = args.output.resolve()
        if not target.is_relative_to(Path.home().resolve()) or not target.parent.is_dir():
            parser.error("--output must be inside an existing persistent MT5 home directory")
        if target.exists():
            parser.error("Output already exists")
    import MetaTrader5 as mt5

    if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=10000):
        raise SystemExit(f"MT5 attach failed: {mt5.last_error()}")
    try:
        if args.collect_seconds is not None:
            report = collect(mt5, args.login, args.collect_seconds, args.server_offset_seconds)
            with target.open('xb') as output:
                output.write((json.dumps(report, sort_keys=True, allow_nan=False) + '\n').encode())
            print(json.dumps({key: report[key] for key in ('data_status', 'blockers',
                                                            'accepted_sample_count', 'transition_bar_times',
                                                            'spread_summary', 'cost_status')}, allow_nan=False))
            raise SystemExit(0 if report['data_status'] == 'passed' else 2)
        evidence = {}
        deadline = time.monotonic() + 15
        while True:
            now = time.time()
            try:
                tick, bars = read_gold(mt5, args.login, None, evidence,
                                       server_offset_seconds=args.server_offset_seconds)
                break
            except DataUnavailable:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(1)
        now = evidence["sampled_at"]
        evaluation = evaluate(bars, float(tick.bid), float(tick.ask), now)
        if evaluation["signal"] == "blocked":
            raise ValueError(evaluation["reason"])
        print(json.dumps({"symbol": SYMBOL,
                          "host_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                          "tick_time": int(tick.time),
                          "server_offset_seconds": args.server_offset_seconds,
                          "quote_age_seconds": round(validate_tick(tick, now,
                              server_offset_seconds=args.server_offset_seconds), 3),
                          "completed_m15_bars": len(bars),
                          "latest_bar_time": bars[-1]["time"],
                          "reason": "ready", "health": evidence}, allow_nan=False))
    except ValueError as exc:
        print(json.dumps({"symbol": SYMBOL, "status": "blocked", "reason": str(exc),
                          "host_utc": datetime.now(timezone.utc).isoformat(),
                          "health": evidence}, allow_nan=False), flush=True)
        raise SystemExit(f"Gold readiness blocked: {exc}") from exc
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
