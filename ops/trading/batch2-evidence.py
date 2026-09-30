"""Read current demo evidence without placing, changing or canceling orders."""
import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from mt5_data import AlgoTradingOn, SYMBOL, read_contract, validate_account, validate_tick


def check_identity(mt5, login):
    account, terminal = mt5.account_info(), mt5.terminal_info()
    try:
        validate_account(account, terminal, login)
    except AlgoTradingOn:
        # A read-only probe may inspect an existing supervised order with Algo on.
        # Other account/connection failures still stop the probe.
        pass
    return terminal


def capture(mt5, login, now, server_offset_seconds):
    check_identity(mt5, login)
    positions = mt5.positions_get(symbol=SYMBOL)
    orders = mt5.orders_get(symbol=SYMBOL)
    if positions is None or orders is None:
        raise ValueError('Gold broker state unavailable; unknown is not empty.')
    contract = read_contract(mt5)
    if contract['name'] != SYMBOL:
        raise ValueError('Gold contract metadata unavailable.')
    quote = {}
    tick = mt5.symbol_info_tick(SYMBOL)
    now = time.time() if now is None else now
    try:
        validate_tick(tick, now, quote,
                      server_offset_seconds=server_offset_seconds)
    except ValueError as exc:
        quote['blocker'] = str(exc)
    terminal = check_identity(mt5, login)
    return {'host_utc': datetime.fromtimestamp(now, timezone.utc).isoformat(),
            'sampled_at': now, 'algo_trading_on': terminal.trade_allowed,
            'gold_positions': len(positions), 'gold_pending_orders': len(orders),
            'protected_positions': sum(p.sl > 0 and p.tp > 0 for p in positions),
            'contract_current_only': contract, 'quote': quote}


def save_evidence(path: Path, result: dict) -> str:
    payload = (json.dumps(result, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    with path.open('xb') as output:
        output.write(payload)
    return hashlib.sha256(payload).hexdigest()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--login', type=int, required=True)
    parser.add_argument('--server-offset-seconds', type=int, choices=(0, 7200, 10800), default=0)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    import MetaTrader5 as mt5
    if not mt5.initialize(r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=10000):
        raise SystemExit('MT5 attach failed; check the private desktop.')
    try:
        samples = []
        for index in range(3):
            if index:
                time.sleep(2)
            samples.append(capture(mt5, args.login, None, args.server_offset_seconds))
        result = {'mode': 'batch2-read-only-evidence', 'symbol': SYMBOL,
                  'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'sdk_version': mt5.__version__, 'server_offset_seconds': args.server_offset_seconds,
                  'cost_status': 'incomplete', 'timestamp_status': 'current_spot_checks_only',
                  'limitations': ['Current contract values do not establish historical cost coverage.',
                                  'Commission and rollover timezone/time still need sourced evidence.',
                                  'Three quote samples do not qualify historical dates or DST.'],
                  'samples': samples}
        if args.output is not None:
            digest = save_evidence(args.output, result)
            result = {key: result[key] for key in ('mode', 'cost_status', 'timestamp_status')}
            result['output_sha256'] = digest
        print(json.dumps(result, sort_keys=True, allow_nan=False))
    except (ValueError, TypeError, OSError) as exc:
        raise SystemExit(f'Evidence capture refused: {exc}') from exc
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    main()
