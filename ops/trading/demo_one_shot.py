"""One supervised gold demo attempt; no strategy signal chooses its side."""
import math
import secrets

from gold_signal import evaluate
from mt5_data import SERVER, SYMBOL, read_gold, validate_account

MAGIC = 20260929


def _positive(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"Invalid broker {name}.")
    return float(value)


def build_entry_request(mt5, login: int, side: str, now: float,
                        server_offset_seconds: int, *, execution: bool) -> dict:
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
    if filling & mt5.SYMBOL_FILLING_FOK:
        fill_type = mt5.ORDER_FILLING_FOK
    elif filling & mt5.SYMBOL_FILLING_IOC:
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
    return {"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": minimum,
            "type": order_type, "price": price, "sl": sl, "tp": tp,
            "deviation": 10, "magic": MAGIC,
            "comment": f"kwg-demo-{secrets.token_hex(4)}",
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": fill_type}
