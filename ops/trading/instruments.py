"""The two reviewed demo instruments; no arbitrary broker symbols."""
GOLD = 'XAUUSD-VIP'
BTC = 'BTCUSD'
BTC_STRATEGY = 'btc-ema-v1-m15-trend-3'


def instrument(symbol):
    if symbol == GOLD:
        return dict(symbol=GOLD, stem='gold', snapshot='latest.json')
    if symbol == BTC:
        return dict(symbol=BTC, stem='btc', snapshot='btc.json')
    raise ValueError('Unsupported demo symbol')


def validate_market(symbol, seconds, trend):
    instrument(symbol)
    if symbol == BTC and (seconds != 900 or trend is not True):
        raise ValueError('BTC demo requires the reviewed M15 trend policy')
