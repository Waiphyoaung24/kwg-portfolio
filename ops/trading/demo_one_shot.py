"""One supervised gold demo attempt; no strategy signal chooses its side."""
import math
import json
import os
import secrets
import sqlite3
import time
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from gold_signal import evaluate
from mt5_data import SERVER, SYMBOL, read_gold, validate_account, validate_tick

MAGIC = 20260929
SNAPSHOT = Path(r"Z:\opt\status\execution.json")
# SYMBOL_FILLING_MODE flags are 1/2; the pinned Python SDK omits their names.
FILLING_FOK_FLAG = 1
FILLING_IOC_FLAG = 2


def _positive(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"Invalid broker {name}.")
    return float(value)


def _direction_type(mt5, request):
    if request["type"] in (mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP):
        return mt5.ORDER_TYPE_BUY
    if request["type"] in (mt5.ORDER_TYPE_SELL, mt5.ORDER_TYPE_SELL_LIMIT, mt5.ORDER_TYPE_SELL_STOP):
        return mt5.ORDER_TYPE_SELL
    raise ValueError("Unknown journal order direction.")


def build_entry_request(mt5, login: int, side: str, now: float,
                        server_offset_seconds: int, *, execution: bool, levels=None) -> dict:
    """Return one locally checked protected request without submitting it."""
    if side not in ("buy", "sell"):
        raise ValueError("Operator must choose buy or sell.")
    tick, bars = read_gold(mt5, login, now,
                           server_offset_seconds=server_offset_seconds, execution=execution)
    assessment = evaluate(bars, float(tick.bid), float(tick.ask), now)
    if assessment["signal"] == "blocked":
        raise ValueError(assessment["reason"])
    account, terminal = mt5.account_info(), mt5.terminal_info()
    validate_account(account, terminal, login, SERVER, execution=execution)
    if getattr(account, "currency", None) != "USD":
        raise ValueError("Expected USD demo account for risk and result reporting.")
    equity = _positive(getattr(account, "equity", None), "equity")
    positions, orders = mt5.positions_get(symbol=SYMBOL), mt5.orders_get(symbol=SYMBOL)
    if positions is None or orders is None or positions or orders:
        raise ValueError("Gold position/order state is occupied or unavailable.")
    info = mt5.symbol_info(SYMBOL)
    if info is None or getattr(info, "name", None) != SYMBOL:
        raise ValueError("Gold contract metadata is unavailable.")
    point = _positive(getattr(info, "point", None), "point")
    tick_size = _positive(getattr(info, "trade_tick_size", None), "tick size")
    minimum = _positive(getattr(info, "volume_min", None), "minimum volume")
    step = _positive(getattr(info, "volume_step", None), "volume step")
    maximum = _positive(getattr(info, "volume_max", None), "maximum volume")
    digits = getattr(info, "digits", None)
    if (minimum > maximum or not math.isclose(minimum / step, round(minimum / step), abs_tol=1e-7)
            or type(digits) is not int or not 0 <= digits <= 10
            or not math.isclose(tick_size / point, round(tick_size / point), abs_tol=1e-7)
            or getattr(info, "trade_mode", None) != mt5.SYMBOL_TRADE_MODE_FULL
            or getattr(info, "trade_exemode", None) not in (0, 1, 2, 3)):
        raise ValueError("Gold contract cannot support this entry.")
    order_mode = getattr(info, "order_mode", None)
    if type(order_mode) is not int or order_mode & (1 | 16 | 32) != (1 | 16 | 32):
        raise ValueError("Broker does not allow market orders with SL and TP.")
    filling = getattr(info, "filling_mode", None)
    if type(filling) is not int:
        raise ValueError("Unknown broker filling policy.")
    if filling & FILLING_FOK_FLAG:
        fill_type = mt5.ORDER_FILLING_FOK
    elif filling & FILLING_IOC_FLAG:
        fill_type = mt5.ORDER_FILLING_IOC
    else:
        raise ValueError("Unsupported broker filling policy.")
    stops = getattr(info, "trade_stops_level", None)
    freeze = getattr(info, "trade_freeze_level", None)
    if (type(stops) is not int or stops < 0 or type(freeze) is not int or freeze < 0):
        raise ValueError("Unknown broker stop distance.")
    distance = max(stops, freeze) * point
    atr = _positive(assessment["atr14"], "ATR")
    price = float(tick.ask if side == "buy" else tick.bid)
    if side == "buy":
        sl = round(math.floor((price - 2 * atr) / tick_size + 1e-9) * tick_size, digits)
        tp = round(math.ceil((price + 3 * atr) / tick_size - 1e-9) * tick_size, digits)
        if sl <= 0 or float(tick.bid) - sl < distance or tp - float(tick.bid) < distance:
            raise ValueError("Protected buy prices violate broker stop/freeze distance.")
        order_type = mt5.ORDER_TYPE_BUY
    else:
        sl = round(math.ceil((price + 2 * atr) / tick_size - 1e-9) * tick_size, digits)
        tp = round(math.floor((price - 3 * atr) / tick_size + 1e-9) * tick_size, digits)
        if tp <= 0 or sl - float(tick.ask) < distance or float(tick.ask) - tp < distance:
            raise ValueError("Protected sell prices violate broker stop/freeze distance.")
        order_type = mt5.ORDER_TYPE_SELL
    profit = mt5.order_calc_profit(order_type, SYMBOL, minimum, price, sl)
    if (type(profit) not in (int, float) or not math.isfinite(profit)
            or profit >= 0 or -profit > equity * .001):
        raise ValueError("Minimum-lot stop exposure exceeds 0.1% of equity or is unknown.")
    request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": minimum,
            "type": order_type, "price": price, "sl": sl, "tp": tp,
            "deviation": 10, "magic": MAGIC,
            "comment": f"kwg-demo-{secrets.token_hex(4)}",
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": fill_type}
    if levels is None:
        return request
    if set(levels) != {"entry", "sl", "tp"}:
        raise ValueError("Entry, stop loss and take profit are required.")
    entry, sl, tp = (_positive(levels[key], key) for key in ("entry", "sl", "tp"))
    if any(abs(value / tick_size - round(value / tick_size)) > 1e-7
           for value in (entry, sl, tp)):
        raise ValueError("Prices must align with the gold tick size.")
    if side == "buy":
        pending_type = mt5.ORDER_TYPE_BUY_LIMIT if entry < float(tick.ask) else mt5.ORDER_TYPE_BUY_STOP
        if not sl < entry < tp or abs(entry - float(tick.ask)) < distance + tick_size:
            raise ValueError("Buy entry and protection must be beyond the broker minimum distance.")
        mode_flag = 2 if pending_type == mt5.ORDER_TYPE_BUY_LIMIT else 4
    else:
        pending_type = mt5.ORDER_TYPE_SELL_LIMIT if entry > float(tick.bid) else mt5.ORDER_TYPE_SELL_STOP
        if not tp < entry < sl or abs(entry - float(tick.bid)) < distance + tick_size:
            raise ValueError("Sell entry and protection must be beyond the broker minimum distance.")
        mode_flag = 2 if pending_type == mt5.ORDER_TYPE_SELL_LIMIT else 4
    if order_mode & mode_flag != mode_flag or min(abs(entry - sl), abs(entry - tp)) < distance:
        raise ValueError("Broker does not permit this protected pending order.")
    profit = mt5.order_calc_profit(order_type, SYMBOL, minimum, entry, sl)
    if (type(profit) not in (int, float) or not math.isfinite(profit)
            or profit >= 0 or -profit > equity * .001):
        raise ValueError("Minimum-lot stop exposure exceeds 0.1% of equity or is unknown.")
    request.update(action=mt5.TRADE_ACTION_PENDING, type=pending_type, price=entry,
                   sl=sl, tp=tp, type_filling=mt5.ORDER_FILLING_RETURN)
    return request


def open_journal(path: Path, login: int) -> sqlite3.Connection:
    """Open the persistent, account-bound attempt history; never touch observer state."""
    path = Path(path)
    if path.is_dir() or not path.parent.is_dir():
        raise ValueError("One-shot journal needs an existing private directory.")
    existed = path.exists()
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        os.chmod(path, 0o600)
        db.execute("PRAGMA synchronous=FULL")
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("One-shot journal integrity check failed")
        if not existed:
            with db:
                db.execute("CREATE TABLE metadata (login INTEGER NOT NULL, server TEXT NOT NULL, symbol TEXT NOT NULL)")
                db.execute("CREATE TABLE attempts (id TEXT PRIMARY KEY, side TEXT NOT NULL, armed_at INTEGER NOT NULL, "
                           "expires_at INTEGER NOT NULL, state TEXT NOT NULL, phase TEXT NOT NULL, "
                           "request_json TEXT, result_code INTEGER, order_id INTEGER, deal_id INTEGER, "
                           "position_ticket INTEGER, volume REAL, opened_at REAL, closed_at REAL, "
                           "close_reason TEXT, realized_net_usd REAL, entry_equity REAL, "
                           "close_order_id INTEGER, close_deal_id INTEGER, plan_json TEXT)")
                db.execute("INSERT INTO metadata VALUES (?, ?, ?)", (login, SERVER, SYMBOL))
        elif "plan_json" not in {row[1] for row in db.execute("PRAGMA table_info(attempts)")}:
            with db:
                db.execute("ALTER TABLE attempts ADD COLUMN plan_json TEXT")
        identity = db.execute("SELECT login, server, symbol FROM metadata").fetchall()
        if [tuple(row) for row in identity] != [(login, SERVER, SYMBOL)]:
            raise ValueError("One-shot journal belongs to another account or symbol.")
        return db
    except BaseException:
        db.close()
        raise


def arm_once(db: sqlite3.Connection, side: str, now: int, levels=None) -> str:
    if side not in ("buy", "sell") or type(now) is not int:
        raise ValueError("Arm requires an operator side and UTC timestamp.")
    arm_id = secrets.token_hex(8)
    with db:
        previous = _attempt(db)
        if previous is not None and previous["state"] not in ("closed", "disarmed"):
            raise ValueError("The previous demo attempt is not resolved.")
        db.execute("INSERT INTO attempts (id, side, armed_at, expires_at, state, phase, plan_json) "
                   "VALUES (?, ?, ?, ?, 'armed', 'entry', ?)",
                   (arm_id, side, now, now + 900, json.dumps(levels) if levels else None))
    return arm_id


def _attempt(db):
    return db.execute("SELECT * FROM attempts ORDER BY rowid DESC LIMIT 1").fetchone()


def _update(db, **fields):
    with db:
        db.execute("UPDATE attempts SET " + ", ".join(f"{key}=?" for key in fields) + " WHERE id=?",
                   (*fields.values(), _attempt(db)["id"]))


def _status(db, now):
    row = _attempt(db) if db is not None else None
    if row is None:
        return {"mode": "one-shot-demo", "status": "disarmed", "updated_at": now,
                "side": None, "volume": None, "opened_at": None, "closed_at": None,
                "close_reason": None, "realized_net_usd": None,
                "entry_price": None, "sl": None, "tp": None}
    request = json.loads(row["request_json"]) if row["request_json"] else None
    return {"mode": "one-shot-demo", "status": row["state"], "updated_at": now,
            "side": row["side"], "volume": row["volume"], "opened_at": row["opened_at"],
            "closed_at": row["closed_at"], "close_reason": row["close_reason"],
            "realized_net_usd": row["realized_net_usd"],
            "entry_price": request.get("price") if request else None,
            "sl": request.get("sl") if request else None,
            "tp": request.get("tp") if request else None}


def _broker_state(mt5, row, now, login):
    account = mt5.account_info()
    terminal = mt5.terminal_info()
    if (account is None or terminal is None or not terminal.connected
            or account.trade_mode != 0
            or account.login != login
            or account.server != SERVER):
        raise ValueError("Pinned demo identity is unavailable during reconciliation.")
    positions = mt5.positions_get(symbol=SYMBOL)
    orders = mt5.orders_get(symbol=SYMBOL)
    offset = _server_offset()
    start = datetime.fromtimestamp(row["armed_at"] - 120 + offset, timezone.utc)
    end = datetime.fromtimestamp(now + 60 + offset, timezone.utc)
    deals = mt5.history_deals_get(start, end)
    if positions is None or orders is None or deals is None:
        raise ValueError("Broker reconciliation data unavailable.")
    request = json.loads(row["request_json"])
    all_positions = tuple(positions)
    candidates = [position for position in all_positions
                  if getattr(position, "symbol", None) == SYMBOL
                  and getattr(position, "magic", None) == MAGIC
                  and (getattr(position, "comment", None) == request["comment"]
                       or getattr(position, "ticket", None) == row["order_id"]
                       or getattr(position, "ticket", None) == row["position_ticket"])]
    anchored_entries = [deal for deal in deals
                        if getattr(deal, "symbol", None) == SYMBOL
                        and getattr(deal, "entry", None) == 0
                        and getattr(deal, "magic", None) == MAGIC
                        and (getattr(deal, "comment", None) == request["comment"]
                             or row["order_id"] and getattr(deal, "order", None) == row["order_id"]
                             or row["deal_id"] and getattr(deal, "ticket", None) == row["deal_id"])]
    position_ids = {position_id for deal in anchored_entries
                    if type(position_id := getattr(deal, "position_id", None)) is int
                    and position_id > 0}
    if row["position_ticket"]:
        position_ids.add(row["position_ticket"])
    matching_deals = [deal for deal in deals if getattr(deal, "symbol", None) == SYMBOL
                      and getattr(deal, "position_id", None) in position_ids]
    return candidates, all_positions, tuple(orders), matching_deals


def _protected(mt5, position, request, entry_equity):
    info = mt5.symbol_info(SYMBOL)
    tick_size = _positive(getattr(info, "trade_tick_size", None), "tick size")
    volume = _positive(getattr(position, "volume", None), "filled volume")
    price = _positive(getattr(position, "price_open", None), "fill price")
    sl = _positive(getattr(position, "sl", None), "server stop")
    tp = _positive(getattr(position, "tp", None), "server target")
    direction = _direction_type(mt5, request)
    if (volume > request["volume"] + 1e-8 or getattr(position, "type", None) != direction
            or abs(sl - request["sl"]) > tick_size / 2
            or abs(tp - request["tp"]) > tick_size / 2
            or (direction == mt5.ORDER_TYPE_BUY and not sl < price < tp)
            or (direction == mt5.ORDER_TYPE_SELL and not tp < price < sl)):
        raise ValueError("Filled position is not the requested protected volume and side.")
    account = mt5.account_info()
    if account is None or account.trade_mode != 0 or account.server != SERVER:
        raise ValueError("Pinned demo identity changed during reconciliation.")
    profit = mt5.order_calc_profit(direction, SYMBOL, volume, price, sl)
    if (type(profit) not in (int, float) or not math.isfinite(profit)
            or profit >= 0 or -profit > _positive(entry_equity, "entry equity") * .001):
        raise ValueError("Actual filled stop exposure exceeds the demo risk ceiling.")
    return volume


def _close_evidence(deals, ticket, request, mt5):
    position_deals = [deal for deal in deals if getattr(deal, "position_id", None) == ticket]
    entries = [deal for deal in position_deals if getattr(deal, "entry", None) == 0]
    exits = [deal for deal in position_deals if getattr(deal, "entry", None) == 1]
    if not entries or not exits or len(entries) + len(exits) != len(position_deals):
        return None
    direction = _direction_type(mt5, request)
    reverse = mt5.ORDER_TYPE_SELL if direction == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    if (any(getattr(deal, "magic", None) != MAGIC or
            getattr(deal, "type", None) != direction for deal in entries)
            or any(getattr(deal, "type", None) != reverse for deal in exits)):
        return None
    entry_volumes = [getattr(deal, "volume", None) for deal in entries]
    exit_volumes = [getattr(deal, "volume", None) for deal in exits]
    if (any(type(volume) not in (int, float) or not math.isfinite(volume) or volume <= 0
            for volume in entry_volumes + exit_volumes)
            or sum(entry_volumes) > request["volume"] + 1e-8
            or not math.isclose(sum(entry_volumes), sum(exit_volumes), abs_tol=1e-8)):
        return None
    total = 0.0
    for deal in position_deals:
        for field in ("profit", "commission", "swap", "fee"):
            value = getattr(deal, field, None)
            if type(value) not in (int, float) or not math.isfinite(value):
                return None
            total += value
    closed_at = max(getattr(deal, "time", 0) for deal in exits)
    if type(closed_at) not in (int, float) or not math.isfinite(closed_at) or closed_at <= 0:
        return None
    return closed_at, round(total, 2), sum(entry_volumes),


def _protective_exit_reason(mt5, exits):
    reasons = {getattr(deal, "reason", None) for deal in exits}
    if not reasons or not reasons.issubset({mt5.DEAL_REASON_SL, mt5.DEAL_REASON_TP}):
        return None
    return "stop loss" if reasons == {mt5.DEAL_REASON_SL} else (
        "take profit" if reasons == {mt5.DEAL_REASON_TP} else "broker protection")


def _close_cause(mt5, row, exits):
    protection = _protective_exit_reason(mt5, exits)
    if protection is not None:
        return protection
    order_id, deal_id = row["close_order_id"], row["close_deal_id"]
    if ((type(order_id) is int and order_id > 0
         and all(getattr(deal, "order", None) == order_id for deal in exits))
            or (type(deal_id) is int and deal_id > 0 and len(exits) == 1
                and getattr(exits[0], "ticket", None) == deal_id)):
        return "timed"
    return "unknown close cause"


def _historical_protection(mt5, row, request, deals, ticket):
    """Prove broker-held stops when an entry closed before a position read."""
    entries = [deal for deal in deals if getattr(deal, "position_id", None) == ticket
               and getattr(deal, "entry", None) == 0]
    exits = [deal for deal in deals if getattr(deal, "position_id", None) == ticket
             and getattr(deal, "entry", None) == 1]
    order_id = row["order_id"] or getattr(entries[0], "order", None)
    if type(order_id) is not int or order_id <= 0:
        return None
    orders = mt5.history_orders_get(ticket=order_id)
    if orders is None or len(orders) != 1:
        return None
    order = orders[0]
    info = mt5.symbol_info(SYMBOL)
    tick_size = _positive(getattr(info, "trade_tick_size", None), "tick size")
    if (getattr(order, "ticket", None) != order_id
            or getattr(order, "position_id", None) != ticket
            or getattr(order, "symbol", None) != SYMBOL
            or getattr(order, "magic", None) != MAGIC
            or getattr(order, "type", None) != request["type"]
            or getattr(order, "volume_initial", None) != request["volume"]
            or abs(float(getattr(order, "sl", 0)) - request["sl"]) > tick_size / 2
            or abs(float(getattr(order, "tp", 0)) - request["tp"]) > tick_size / 2):
        return None
    reason = _protective_exit_reason(mt5, exits)
    if reason is None:
        return None
    equity = _positive(row["entry_equity"], "entry equity")
    exposure = 0.0
    for deal in entries:
        price = _positive(getattr(deal, "price", None), "filled price")
        profit = mt5.order_calc_profit(_direction_type(mt5, request), SYMBOL,
                                      deal.volume, price, request["sl"])
        if type(profit) not in (int, float) or not math.isfinite(profit) or profit >= 0:
            return None
        exposure -= profit
    if exposure > equity * .001:
        return None
    return reason


def _reconcile(mt5, db, row, now):
    try:
        login = db.execute("SELECT login FROM metadata").fetchone()[0]
        positions, all_positions, orders, deals = _broker_state(mt5, row, now, login)
        request = json.loads(row["request_json"])
        pending_request = request.get("action") == mt5.TRADE_ACTION_PENDING
        own_orders = [order for order in orders if getattr(order, "symbol", None) == SYMBOL
                      and getattr(order, "ticket", None) == row["order_id"]
                      and getattr(order, "magic", None) == MAGIC
                      and getattr(order, "type", None) == request["type"]
                      and getattr(order, "volume_initial", None) == request["volume"]
                      and getattr(order, "price_open", None) == request["price"]
                      and getattr(order, "sl", None) == request["sl"]
                      and getattr(order, "tp", None) == request["tp"]]
        if (len(positions) > 1 or len(all_positions) != len(positions)
                or len(orders) != len(own_orders) or len(own_orders) > 1):
            raise ValueError("Gold order or multiple positions need operator reconciliation.")
        if own_orders and not positions and pending_request:
            _update(db, state="pending", volume=request["volume"])
            return
        if own_orders and positions:
            raise ValueError("Partially filled pending order needs operator reconciliation.")
        entry_positions = {getattr(deal, "position_id", None) for deal in deals
                           if getattr(deal, "entry", None) == 0}
        if len(entry_positions) > 1:
            raise ValueError("Multiple position identifiers require operator reconciliation.")
        if positions:
            position = positions[0]
            ticket = getattr(position, "ticket", None)
            if type(ticket) is not int or ticket <= 0:
                raise ValueError("Broker position ticket is missing.")
            volume = _protected(mt5, position, request, row["entry_equity"])
            if row["phase"] == "close":
                _update(db, state="needs_attention", position_ticket=ticket, volume=volume)
            else:
                _update(db, state="open", phase="entry", position_ticket=ticket,
                        volume=volume, opened_at=row["opened_at"] or now)
            return
        ticket = row["position_ticket"]
        if ticket is None:
            entry = next((deal for deal in deals if getattr(deal, "entry", None) == 0), None)
            ticket = getattr(entry, "position_id", None)
        closed = _close_evidence(deals, ticket, request, mt5) if ticket else None
        if closed:
            if row["opened_at"] is None:
                close_reason = _historical_protection(mt5, row, request, deals, ticket)
                if close_reason is None:
                    raise ValueError("Broker-held protection was not verified before the close.")
            elif row["phase"] == "entry":
                exits = [deal for deal in deals if getattr(deal, "position_id", None) == ticket
                         and getattr(deal, "entry", None) == 1]
                close_reason = _protective_exit_reason(mt5, exits)
                if close_reason is None:
                    raise ValueError("Early close was not caused by broker protection.")
            else:
                exits = [deal for deal in deals if getattr(deal, "position_id", None) == ticket
                         and getattr(deal, "entry", None) == 1]
                close_reason = _close_cause(mt5, row, exits)
            offset = _server_offset()
            _update(db, state="closed", position_ticket=ticket, closed_at=closed[0] - offset,
                    volume=closed[2], opened_at=row["opened_at"] or
                    min(getattr(deal, "time") for deal in deals if getattr(deal, "entry", None) == 0) - offset,
                    close_reason=close_reason,
                    realized_net_usd=closed[1])
        else:
            if (pending_request and row["state"] == "submitting" and row["order_id"]
                    and now - row["armed_at"] < 30):
                return  # The accepted pending order may not appear in MT5 immediately.
            if pending_request and row["order_id"] and not deals:
                history = mt5.history_orders_get(ticket=row["order_id"])
                if (history is not None and len(history) == 1
                        and getattr(history[0], "symbol", None) == SYMBOL
                        and getattr(history[0], "magic", None) == MAGIC
                        and getattr(history[0], "state", None) == mt5.ORDER_STATE_CANCELED):
                    _update(db, state="disarmed", close_reason="pending order cancelled in MT5")
                    return
            _update(db, state="needs_attention")
    except (ValueError, TypeError, OverflowError):
        _update(db, state="needs_attention")


def _server_offset():
    value = os.environ.get("MT5_SERVER_OFFSET_SECONDS")
    if value not in ("0", "7200", "10800"):
        raise ValueError("Current verified MT5 server offset is required.")
    return int(value)


def _final_entry_guard(mt5, login, request):
    account = mt5.account_info()
    validate_account(account, mt5.terminal_info(), login, execution=True)
    tick = mt5.symbol_info_tick(SYMBOL)
    validate_tick(tick, time.time(), server_offset_seconds=_server_offset())
    info = mt5.symbol_info(SYMBOL)
    positions, orders = mt5.positions_get(symbol=SYMBOL), mt5.orders_get(symbol=SYMBOL)
    if positions is None or orders is None or positions or orders:
        raise ValueError("Gold position/order state changed before entry.")
    pending_request = request["action"] == mt5.TRADE_ACTION_PENDING
    fill_flag = (FILLING_FOK_FLAG if request["type_filling"] == mt5.ORDER_FILLING_FOK
                 else FILLING_IOC_FLAG)
    filling = getattr(info, "filling_mode", None)
    order_mode = getattr(info, "order_mode", None)
    if (getattr(info, "name", None) != SYMBOL
            or getattr(info, "trade_mode", None) != mt5.SYMBOL_TRADE_MODE_FULL
            or getattr(info, "trade_exemode", None) not in (0, 1, 2, 3)
            or type(filling) is not int or (not pending_request and not filling & fill_flag)
            or type(order_mode) is not int or order_mode & 49 != 49
            or getattr(info, "volume_min", None) != request["volume"]):
        raise ValueError("Gold trading conditions changed before entry.")
    point = _positive(getattr(info, "point", None), "point")
    tick_size = _positive(getattr(info, "trade_tick_size", None), "tick size")
    if any(abs(price / tick_size - round(price / tick_size)) > 1e-7
           for price in (request["price"], request["sl"], request["tp"])):
        raise ValueError("Gold tick size changed before entry.")
    stops = getattr(info, "trade_stops_level", None)
    freeze = getattr(info, "trade_freeze_level", None)
    if type(stops) is not int or type(freeze) is not int or stops < 0 or freeze < 0:
        raise ValueError("Broker stop distance changed.")
    distance = max(stops, freeze) * point
    bid, ask = float(tick.bid), float(tick.ask)
    direction = _direction_type(mt5, request)
    current_price = ask if direction == mt5.ORDER_TYPE_BUY else bid
    if not pending_request and abs(current_price - request["price"]) > request["deviation"] * point:
        raise ValueError("Gold price moved beyond the checked entry deviation.")
    if pending_request:
        kind = (mt5.ORDER_TYPE_BUY_LIMIT if direction == mt5.ORDER_TYPE_BUY and request["price"] < ask
                else mt5.ORDER_TYPE_BUY_STOP if direction == mt5.ORDER_TYPE_BUY
                else mt5.ORDER_TYPE_SELL_LIMIT if request["price"] > bid
                else mt5.ORDER_TYPE_SELL_STOP)
        flag = 2 if kind in (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT) else 4
        valid = (kind == request["type"] and order_mode & flag == flag
                 and abs(request["price"] - current_price) >= distance + tick_size
                 and min(abs(request["price"] - request["sl"]),
                         abs(request["price"] - request["tp"])) >= distance
                 and (request["sl"] < request["price"] < request["tp"] if direction == mt5.ORDER_TYPE_BUY
                      else request["tp"] < request["price"] < request["sl"]))
    elif direction == mt5.ORDER_TYPE_BUY:
        valid = bid - request["sl"] >= distance and request["tp"] - bid >= distance
    else:
        valid = request["sl"] - ask >= distance and ask - request["tp"] >= distance
    if not valid:
        raise ValueError("Gold stop distance changed before entry.")
    profit = mt5.order_calc_profit(direction, SYMBOL, request["volume"],
                                   request["price"] if pending_request else current_price, request["sl"])
    if (type(profit) not in (int, float) or not math.isfinite(profit)
            or profit >= 0 or -profit > _positive(getattr(account, "equity", None), "equity") * .001):
        raise ValueError("Gold stop exposure changed before entry.")
    return account.equity


def process_once(mt5, db: sqlite3.Connection, now: float, *, allow_entry=True) -> dict:
    """Advance one journal state; only a fresh arm may submit an entry."""
    row = _attempt(db)
    if row is None:
        return _status(db, now)
    if row["state"] in ("closed", "disarmed"):
        return _status(db, now)
    if row["state"] == "armed":
        if not allow_entry or now > row["expires_at"]:
            _update(db, state="disarmed", close_reason="arm expired or process restarted")
            return _status(db, now)
        login = db.execute("SELECT login FROM metadata").fetchone()[0]
        try:
            levels = json.loads(row["plan_json"]) if row["plan_json"] else None
            request = build_entry_request(mt5, login, row["side"], now,
                                          _server_offset(), execution=True, levels=levels)
            check = mt5.order_check(request)
            if check is None or getattr(check, "retcode", None) != 0:
                raise ValueError("Broker rejected protected entry check.")
        except (ValueError, TypeError, OverflowError) as exc:
            _update(db, state="disarmed", close_reason=str(exc))
            return _status(db, now)
        try:
            entry_equity = _final_entry_guard(mt5, login, request)
        except ValueError as exc:
            _update(db, state="disarmed", close_reason=str(exc))
            return _status(db, now)
        _update(db, state="submitting", request_json=json.dumps(request, allow_nan=False),
                entry_equity=entry_equity)
        try:
            result = mt5.order_send(request)
        except Exception:
            result = None
        _update(db, result_code=getattr(result, "retcode", None),
                order_id=getattr(result, "order", None), deal_id=getattr(result, "deal", None))
        _reconcile(mt5, db, _attempt(db), now)
        code = getattr(result, "retcode", None)
        if type(code) is int and code not in (10008, 10009, 10010):
            try:
                positions, all_positions, orders, deals = _broker_state(mt5, _attempt(db), now, login)
                if not positions and not all_positions and not orders and not deals:
                    _update(db, state="disarmed", close_reason="broker rejected entry")
            except ValueError:
                pass
    elif row["state"] in ("submitting", "pending", "closing", "needs_attention"):
        if row["request_json"] is not None:
            _reconcile(mt5, db, row, now)
    elif row["state"] == "open":
        _reconcile(mt5, db, row, now)
    return _status(db, now)


def write_snapshot(path: Path, status: dict) -> None:
    """Publish the allowlisted execution state atomically to the private volume."""
    payload = {key: status.get(key) for key in
               ("mode", "status", "updated_at", "side", "volume", "opened_at",
                "closed_at", "close_reason", "realized_net_usd", "entry_price", "sl", "tp")}
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


@contextmanager
def _exclusive(path: Path):
    """Hold one OS lock across commits and broker calls in a CLI process."""
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            if not lock.read(1):
                lock.write(b"1")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "arm", "resume"):
        command = commands.add_parser(name)
        command.add_argument("--state", required=True, type=Path)
        if name != "resume":
            command.add_argument("--side", required=True, choices=("buy", "sell"))
            for level in ("entry", "sl", "tp"):
                command.add_argument(f"--{level}", required=True, type=float)
        if name == "arm":
            command.add_argument("--enable-demo-execution", action="store_true")
    args = parser.parse_args()
    path = args.state.resolve()
    if path != (Path.home() / "gold-one-shot.sqlite3").resolve() or not path.parent.is_dir():
        parser.error("--state must name the fixed one-shot journal in the persistent MT5 home")
    if args.command == "arm" and not args.enable_demo_execution:
        parser.error("arm requires --enable-demo-execution")
    if args.command == "resume" and not path.exists():
        write_snapshot(SNAPSHOT, _status(None, time.time()))
        return
    login_text = os.environ.get("MT5_DEMO_LOGIN", "")
    if not login_text.isdecimal() or not int(login_text):
        parser.error("MT5_DEMO_LOGIN is required")
    login = int(login_text)
    offset = _server_offset()
    import MetaTrader5 as mt5
    if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=10000):
        raise SystemExit(f"MT5 attach failed: {mt5.last_error()}")
    try:
        if args.command == "preview":
            now = time.time()
            levels = {key: getattr(args, key) for key in ("entry", "sl", "tp")}
            try:
                request = build_entry_request(mt5, login, args.side, now, offset,
                                              execution=False, levels=levels)
            except ValueError as exc:
                print(json.dumps({"error": str(exc)[:160]}))
                return
            profit = mt5.order_calc_profit(_direction_type(mt5, request), SYMBOL, request["volume"],
                                           request["price"], request["sl"])
            equity = _positive(getattr(mt5.account_info(), "equity", None), "equity")
            kind = {mt5.ORDER_TYPE_BUY_LIMIT: "Buy limit", mt5.ORDER_TYPE_BUY_STOP: "Buy stop",
                    mt5.ORDER_TYPE_SELL_LIMIT: "Sell limit", mt5.ORDER_TYPE_SELL_STOP: "Sell stop"}[request["type"]]
            print(json.dumps({"mode": "private-demo-preview", "side": args.side,
                              "symbol": SYMBOL, "volume": request["volume"],
                              "quote_reference": request["price"], "sl": request["sl"],
                              "tp": request["tp"], "modeled_stop_usd": -profit,
                              "modeled_stop_pct_of_equity": -profit / equity * 100,
                              "order_kind": kind, "pending_until_cancelled": True,
                              "previewed_at": now,
                              "new_preflight_required_before_arm": True,
                              "order_check_passed": False, "order_sent": False}, allow_nan=False))
            return
        with _exclusive(path):
            db = open_journal(path, login)
            try:
                if args.command == "arm":
                    arm_once(db, args.side, int(time.time()),
                             {key: getattr(args, key) for key in ("entry", "sl", "tp")})
                previous_status = None
                while True:
                    result = process_once(mt5, db, time.time(),
                                          allow_entry=args.command == "arm")
                    write_snapshot(SNAPSHOT, result)
                    if result["status"] != previous_status:
                        print(json.dumps(result, allow_nan=False), flush=True)
                        previous_status = result["status"]
                    if result["status"] not in ("pending", "open", "closing", "submitting", "needs_attention"):
                        break
                    time.sleep(5)
            finally:
                db.close()
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
