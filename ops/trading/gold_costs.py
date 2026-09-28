"""Explicit, offline gold cost evidence. Unknown fees never become zero."""
import math


def _amount(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f'Invalid {name}')
    return float(value)


def validate_profile(profile: dict, start: int, end: int) -> dict:
    if not isinstance(profile, dict) or type(start) is not int or type(end) is not int or start >= end:
        raise ValueError('Invalid cost profile or window')
    blockers = []
    for part in ('commission', 'swap'):
        item = profile.get(part)
        if not isinstance(item, dict) or item.get('status') != 'verified_historical':
            blockers.append(f'{part}_unverified')
            continue
        source = item.get('source_sha256')
        if (not isinstance(source, str) or len(source) != 64
                or any(c not in '0123456789abcdef' for c in source.lower())
                or type(item.get('effective_from')) is not int
                or type(item.get('effective_to')) is not int):
            blockers.append(f'{part}_provenance_missing')
        elif not (item['effective_from'] <= start and end <= item['effective_to']):
            blockers.append(f'{part}_history_uncovered')
        if part == 'swap' and (not item.get('rollover_timezone') or not item.get('rollover_local_time')
                               or not isinstance(item.get('rollover_events'), list)):
            blockers.append('swap_schedule_missing')
    if profile.get('symbol') != 'XAUUSD-VIP':
        raise ValueError('Wrong symbol')
    return {'historical_coverage': not blockers, 'blockers': blockers}


def commission_usd(profile: dict, lots: float, side: str) -> float:
    if side not in ('entry', 'exit') or _amount(lots, 'lots') <= 0:
        raise ValueError('Invalid commission side or lots')
    fee = profile.get('commission', {})
    if fee.get('status') not in ('verified_current', 'verified_historical') or not fee.get('source_sha256'):
        raise ValueError('Commission is unverified')
    if fee.get('currency') != 'USD' or fee.get('basis') not in ('per_side_per_lot', 'round_trip_per_lot'):
        raise ValueError('Unsupported commission basis or currency')
    if fee.get('minimum') not in (None, 0):
        raise ValueError('Minimum commission schedule unsupported')
    value = _amount(fee.get('value'), 'commission')
    if value < 0:
        raise ValueError('Negative commission')
    return value * lots / (2 if fee['basis'] == 'round_trip_per_lot' else 1)


def rollover_cashflow_usd(profile: dict, direction: int, lots: float,
                          spec: dict, start: int, end: int) -> float:
    if direction not in (-1, 1) or _amount(lots, 'lots') <= 0 or start >= end:
        raise ValueError('Invalid rollover position or window')
    swap = profile.get('swap', {})
    if swap.get('status') not in ('verified_current', 'verified_historical') or not swap.get('source_sha256'):
        raise ValueError('Swap is unverified')
    mode = swap.get('mode')
    if mode == 'POINTS':
        if spec.get('currency_profit') != 'USD':
            raise ValueError('POINTS requires USD linear profit currency')
        factor = _amount(spec.get('point'), 'point') * _amount(spec.get('trade_contract_size'), 'contract size')
        if factor <= 0:
            raise ValueError('Invalid contract size or point')
    elif mode == 'USD_PER_LOT':
        if swap.get('currency') != 'USD':
            raise ValueError('Swap cash currency must be USD')
        factor = 1
    else:
        raise ValueError('Unsupported swap mode')
    total = 0.0
    previous = None
    for event in swap.get('rollover_events', []):
        at = event.get('at')
        if type(at) is not int or (previous is not None and at <= previous):
            raise ValueError('Unsorted rollover events')
        previous = at
        multiplier = _amount(event.get('multiplier'), 'rollover multiplier')
        if multiplier < 0:
            raise ValueError('Negative rollover multiplier')
        rate = _amount(event.get('rate_long' if direction == 1 else 'rate_short'), 'swap rate')
        if start < at <= end:
            total += rate * multiplier * factor * lots
    return total
