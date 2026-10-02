"""Bounded read-only diagnostic follower; never qualifies data or starts MT5."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import subprocess
import time

from review_observer_log import observer_frames, observer_records

MAX_FRAME = 1024 * 1024
MAX_BYTES = 64 * 1024 * 1024
NUMBERS = ('sampled_at', 'tick_time', 'tick_time_msc', 'quote_age_seconds',
           'bid', 'ask', 'spread_price', 'bar_time', 'bars_count', 'latest_bar_time')
STATES = ('unknown', 'missing', 'invalid', 'fresh', 'stale', 'connected',
          'disconnected', 'guard_failed', 'ready', 'blocked')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def selected(record):
    health = record.get('health', {})
    result = {'status': record.get('status'), 'signal': record.get('signal')}
    if (record.get('symbol') != 'XAUUSD-VIP'
            or result['status'] not in ('blocked', 'duplicate', 'baseline', 'observed')
            or result['signal'] not in ('none', 'buy', 'sell')):
        raise ValueError('Unexpected observer state')
    result['health'] = {k: health[k] for k in NUMBERS if k in health
        and type(health[k]) in (int, float) and math.isfinite(health[k])}
    for key in ('terminal', 'quote', 'history'):
        if health.get(key) in STATES:
            result['health'][key] = health[key]
    if type(record.get('bar_time')) is int:
        result['bar_time'] = record['bar_time']
    # Free text and arbitrary fields can contain credentials; retain hashes only.
    result['record_sha256'] = hashlib.sha256(encoded(record)).hexdigest()
    result['reason_sha256'] = hashlib.sha256(encoded(record.get('reason'))).hexdigest()
    return result


def capture(chunks, target, *, mode, max_bytes=MAX_BYTES):
    if mode not in ('synthetic_fixture', 'docker_follow') or type(max_bytes) is not int or not 1 <= max_bytes <= MAX_BYTES:
        raise ValueError('Invalid capture settings')
    target = Path(target)
    target.mkdir(mode=0o700)  # Exclusive run identity; failed runs stay intact.
    digest = hashlib.sha256()
    count = gaps = size = discarded = rejected = 0
    previous = None
    buffer = b''
    reason = 'stream_ended'
    started = time.time()
    with (target / 'diagnostics.jsonl').open('xb') as output:
        def write(value):
            nonlocal size
            raw = encoded(value)
            if size + len(raw) > max_bytes:
                raise OverflowError('Capture output limit')
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
            digest.update(raw)
            size += len(raw)
        try:
            write({'kind': 'start', 'received_at': started, 'mode': mode})
            for chunk in chunks:
                buffer += chunk
                if len(buffer) > MAX_FRAME:
                    reason = 'frame_limit'
                    break
                records = list(observer_records(buffer))
                if not records:
                    continue
                for record, frame in observer_frames(buffer):
                    if not list(observer_records(frame.encode())):
                        write({'kind': 'rejected_frame', 'bytes': len(frame.encode()),
                               'sha256': hashlib.sha256(frame.encode()).hexdigest()})
                        rejected += 1
                        continue
                    sample = selected(record)
                    stamp = sample['health']['sampled_at']
                    if previous is not None and (stamp <= previous or stamp - previous > 30):
                        write({'kind': 'sample_gap', 'previous': previous, 'current': stamp})
                        gaps += 1
                    write({'kind': 'sample', 'received_at': time.time(), **sample})
                    previous = stamp
                    count += 1
                # Input is physical log lines; preserve PTY-wrapped records across lines.
                buffer = b''
            if buffer and reason == 'stream_ended':
                reason = 'incomplete_frame'
                discarded = len(buffer)
        except OverflowError:
            reason = 'output_limit'
        except TimeoutError:
            reason = 'timeout'
        except KeyboardInterrupt:
            reason = 'interrupted'
        except (ValueError, KeyError, TypeError, RuntimeError):
            reason = 'invalid_sample_or_source_failure'
    discarded = len(buffer)  # Preserve tail evidence on timeout/failure as well.
    receipt = {'mode': mode, 'started_at': started, 'ended_at': time.time(),
        'stop_reason': reason, 'sample_count': count, 'gap_count': gaps,
        'rejected_frame_count': rejected,
        'trailing_unparsed_bytes': discarded, 'bytes': size, 'sha256': digest.hexdigest(),
        'trailing_unparsed_sha256': hashlib.sha256(buffer).hexdigest() if buffer else None,
        'completeness_verified': False, 'qualification': 'unqualified', 'observed_days': 0,
        'model_requests': 0, 'promotion_status': 'blocked',
        'code_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ('capture-observer.py', 'review_observer_log.py')}}
    with (target / 'receipt.json').open('xb') as output:
        output.write(encoded(receipt))
        output.flush()
        os.fsync(output.fileno())
    return receipt


def docker_lines(seconds):
    deadline = time.monotonic() + seconds
    since = str(int(time.time()))
    process = subprocess.Popen(['docker', 'logs', '--follow', '--since', since,
                                'kwg-mt5-desktop'], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)
    pending = b''
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while time.monotonic() < deadline:
                if not selector.select(min(1, max(0, deadline - time.monotonic()))):
                    continue
                chunk = os.read(process.stdout.fileno(), 8192)
                if not chunk:
                    if pending:
                        yield pending
                    if process.wait(timeout=2) != 0:
                        raise RuntimeError('Docker log source failed')
                    return
                pending += chunk
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    yield line + b'\n'
                if len(pending) > MAX_FRAME:
                    yield pending
                    return
            if pending:
                yield pending
            raise TimeoutError('Bounded capture ended')
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        process.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--seconds', type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 86400:
        parser.error('Capture duration must be 1–86400 seconds')
    if not args.fixture and os.name != 'posix':
        parser.error('Live Docker follower requires the Linux VPS')
    os.umask(0o077)
    try:
        if args.fixture:
            with args.fixture.open('rb') as source:
                result = capture(iter(lambda: source.readline(MAX_FRAME + 1), b''), args.output,
                                 mode='synthetic_fixture')
        else:
            chunks = docker_lines(args.seconds)
            try:
                result = capture(chunks, args.output, mode='docker_follow')
            finally:
                chunks.close()
    except (OSError, ValueError):
        parser.exit(2, 'Capture refused input or output; preserve any partial run.\n')
    print(json.dumps({k: result[k] for k in ('mode', 'stop_reason', 'sample_count', 'gap_count', 'sha256')}))


if __name__ == '__main__':
    main()
