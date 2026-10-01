"""Read-only parser for Docker-timestamped, PTY-wrapped observer JSON."""
import json
import math
import re


def observer_records(raw):
    text = raw.decode('utf-8', errors='replace')
    text = re.sub(r'\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)', '', text)
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    text = re.sub(r'(?m)^\d{4}-\d{2}-\d{2}T[0-9:.]+Z ', '', text)
    text = ''.join(text.splitlines())
    decoder = json.JSONDecoder()
    index = 0
    while True:
        index = text.find('{', index)
        if index < 0:
            return
        try:
            item, end = decoder.raw_decode(text, index)
        except ValueError:
            index += 1
            continue
        index = end
        if not isinstance(item, dict) or item.get('mode') != 'signal-only':
            continue
        health = item.get('health')
        stamp = health.get('sampled_at') if isinstance(health, dict) else None
        if type(stamp) in (int, float) and math.isfinite(stamp):
            yield item


if __name__ == '__main__':
    # Synthetic regression: wrapping/timestamps, ANSI controls and incomplete records.
    record = {'mode': 'signal-only', 'status': 'blocked', 'reason': 'Synthetic stale quote',
              'health': {'sampled_at': 1000}}
    raw = json.dumps(record)
    wrapped = '\n'.join('2026-10-01T17:00:00.000000000Z ' + raw[i:i+29]
                        for i in range(0, len(raw), 29))
    assert list(observer_records(('\x1b[?25l' + wrapped + '\x1b[?25h').encode())) == [record]
    assert list(observer_records(b'{"mode":"signal-only","health":')) == []
    assert list(observer_records((raw + '\n' + raw).encode())) == [record, record]
    print('PASS: synthetic wrapped/plain/truncated observer log checks; no runtime data read.')
