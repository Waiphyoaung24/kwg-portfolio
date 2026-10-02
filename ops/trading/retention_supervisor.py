"""Bounded operations follower supervision; evidence always remains unqualified."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

MAX_BYTES = 64 * 1024 * 1024


def encode(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=unique)
    if not isinstance(value,dict):
        raise ValueError('JSON object required')
    encode(value)
    return value


def write_once(path,value):
    with path.open('xb') as output:
        output.write(encode(value))
        output.flush()
        os.fsync(output.fileno())


def source_hashes():
    return {name: sha(Path(__file__).with_name(name).read_bytes())
            for name in ('capture-observer.py', 'review_observer_log.py')}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def bounded(path, limit):
    if path.is_symlink():
        raise ValueError('Symlink artifact')
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Artifact limit')
    return raw


def review(folders, start, end, *, mode='docker_follow'):
    if not finite(start) or not finite(end) or start >= end or mode not in ('docker_follow','synthetic_fixture'):
        raise ValueError('Review window invalid')
    if len({Path(f).resolve() for f in folders}) != len(folders):
        raise ValueError('Duplicate segment identity')
    blockers, index, previous = set(), {}, None
    for folder in folders:
        try:
            folder = Path(folder)
            if folder.is_symlink():
                raise ValueError('Symlink segment')
            receipt = load(bounded(folder/'receipt.json', 1024*1024))
            if any(type(receipt[k]) is not int or receipt[k] < 0 for k in
                   ('bytes','sample_count','gap_count','rejected_frame_count','trailing_unparsed_bytes')):
                raise ValueError('Receipt counter type')
            raw = bounded(folder/'diagnostics.jsonl', MAX_BYTES)
            if (receipt['sha256'] != sha(raw) or receipt['bytes'] != len(raw)
                    or receipt['mode'] != mode or receipt['code_sha256'] != source_hashes()
                    or receipt['qualification'] != 'unqualified' or receipt['promotion_status'] != 'blocked'
                    or receipt['completeness_verified'] is not False
                    or any(type(receipt[k]) is not int or receipt[k] != 0 for k in ('observed_days','model_requests'))):
                raise ValueError('Receipt identity')
            if (not finite(receipt['started_at']) or not finite(receipt['ended_at'])
                    or receipt['ended_at'] <= receipt['started_at']):
                raise ValueError('Receipt clock')
            rows = [load(line) for line in raw.splitlines()]
            samples = [row for row in rows if row.get('kind') == 'sample']
            stamps = [row['health']['sampled_at'] for row in samples]
            if not all(finite(t) for t in stamps):
                raise ValueError('Sample clock')
            gaps = sum(b <= a or b-a > 30 for a,b in zip(stamps,stamps[1:]))
            rejects = sum(row.get('kind') == 'rejected_frame' for row in rows)
            if (len(samples) != receipt['sample_count'] or gaps != receipt['gap_count']
                    or rejects != receipt['rejected_frame_count']):
                raise ValueError('Receipt count')
            if gaps:
                blockers.add('segment_sample_gap')
            if receipt['stop_reason'] != 'timeout' or receipt['trailing_unparsed_bytes'] or rejects:
                blockers.add('segment_diagnostics_incomplete')
            current = {}
            received_times=[]
            for row in samples:
                stamp, received, identity = row['health']['sampled_at'], row['received_at'], row['record_sha256']
                if (not finite(received) or not isinstance(identity,str) or len(identity) != 64
                        or any(c not in '0123456789abcdef' for c in identity)):
                    raise ValueError('Sample identity')
                if not receipt['started_at'] <= received <= receipt['ended_at']:
                    raise ValueError('Receipt/sample boundary')
                received_times.append(received)
                if received-stamp < 0 or received-stamp > 30:
                    blockers.add('sample_clock_or_delivery_gap')
                if stamp in index and index[stamp] != identity:
                    blockers.add('conflicting_sample')
                index[stamp] = current[stamp] = identity
            if (not received_times or received_times[0]-receipt['started_at'] > 30
                    or receipt['ended_at']-received_times[-1] > 30
                    or any(b <= a or b-a > 30 for a,b in zip(received_times,received_times[1:]))):
                blockers.add('segment_receive_boundary_or_clock_gap')
            if previous is not None and not set(previous).intersection(current):
                blockers.add('missing_overlap')
            previous = current
        except (OSError, ValueError, KeyError, TypeError):
            blockers.add('segment_integrity_failed')
    stamps = sorted(t for t in index if start <= t <= end)
    if not stamps or stamps[0]-start > 30:
        blockers.add('start_boundary_gap')
    if not stamps or end-stamps[-1] > 30:
        blockers.add('end_boundary_gap')
    if any(b-a > 30 for a,b in zip(stamps,stamps[1:])):
        blockers.add('sample_gap')
    return {'mode': 'retention_review', 'evidence_mode': mode, 'blockers': sorted(blockers),
        'unique_samples':len(stamps),'qualification':'unqualified','observed_days':0,
        'model_requests':0,'promotion_status':'blocked','completeness_verified':False}


def last_received(folder):
    try:
        with (folder/'diagnostics.jsonl').open('rb') as source:
            source.seek(0,2)
            source.seek(max(0,source.tell()-8192))
            raw=source.read(8192)
        lines=raw.split(b'\n')[:-1]
        for line in reversed(lines):
            try:
                row=load(line)
                if row.get('kind')=='sample' and finite(row.get('received_at')):
                    return row['received_at']
            except ValueError:
                continue
    except OSError:
        pass
    return None


def stop_owned(process):
    owned_group=getattr(process,'_retention_group',False) is True
    code=process.poll()
    if owned_group:
        try:
            os.killpg(process.pid,signal.SIGTERM)
            if code is None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            # Leader exit does not imply that its Docker client has exited.
            os.killpg(process.pid,0)
            os.killpg(process.pid,getattr(signal,'SIGKILL',9))
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        process._retention_group=False
    elif code is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def supervise(target, seconds, segment_seconds, overlap_seconds, reserve_bytes, *,
              launch=None, clock=time.monotonic, wall=time.time, sleep=time.sleep, space=None,
              evidence_mode='docker_follow'):
    if (any(type(v) is not int for v in (seconds,segment_seconds,overlap_seconds,reserve_bytes))
            or not 1 <= seconds <= 172800 or not 0 < overlap_seconds < segment_seconds <= 86400
            or reserve_bytes < 1 or math.ceil(seconds/(segment_seconds-overlap_seconds)) > 4
            or evidence_mode not in ('docker_follow','synthetic_fixture')
            or (evidence_mode=='synthetic_fixture' and launch is None)):
        raise ValueError('Supervisor bounds invalid')
    target=Path(target)
    target.mkdir(mode=0o700)
    space=space or (lambda:shutil.disk_usage(target).free)
    def default_launch(folder,duration):
        process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).with_name('capture-observer.py')),
            '--seconds',str(duration),'--output',str(folder)],stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,start_new_session=True)
        process._retention_group=True
        return process
    launch=launch or default_launch
    active, folders, blockers=[],[],[]
    finished=set()
    initial=clock()
    started=wall()
    deadline=initial+seconds
    next_start=initial
    with (target/'events.jsonl').open('xb') as events:
        def event(kind):
            events.write(encode({'kind':kind,'received_at':wall()}))
            events.flush()
            os.fsync(events.fileno())
        try:
            event('supervisor_started')
            while True:
                now=clock()
                for process,folder,began,expected_end in active:
                    code=process.poll()
                    if code not in (None,0):
                        blockers.append('follower_failed')
                    if code==0 and folder not in finished:
                        if wall()+1 < expected_end:
                            blockers.append('follower_ended_early')
                        checked=review([folder],began,expected_end,mode=evidence_mode)
                        blockers.extend(checked['blockers'])
                        stop_owned(process)
                        finished.add(folder)
                    if code is None:
                        last=last_received(folder)
                        age=wall()-(last if last is not None else began)
                        if age < 0 or age > 30:
                            blockers.append('writer_stale')
                if blockers or now >= deadline:
                    break
                if now >= next_start:
                    if space() < reserve_bytes:
                        blockers.append('disk_reserve_unavailable')
                        break
                    if sum(p.poll() is None for p,_,_,_ in active) >= 2:
                        blockers.append('handoff_overdue')
                        break
                    folder=target/('segment-%02d' % len(folders))
                    duration=min(segment_seconds,max(1,math.ceil(deadline-now)))
                    began=wall()
                    process=launch(folder,duration)
                    active.append((process,folder,began,began+duration))
                    folders.append(folder)
                    event('follower_started')
                    next_start=deadline if now+duration>=deadline else now+segment_seconds-overlap_seconds
                sleep(min(10,max(0.01,next_start-clock()),max(0.01,deadline-clock())))
            if not blockers:
                for process,_,_,_ in active:
                    try:
                        if process.wait(timeout=5) != 0:
                            blockers.append('follower_failed')
                    except subprocess.TimeoutExpired:
                        blockers.append('follower_unfinalized')
        except KeyboardInterrupt:
            blockers.append('supervisor_interrupted')
        except (OSError, ValueError, RuntimeError):
            blockers.append('supervisor_failed')
        finally:
            for process,_,_,_ in active:
                try:
                    stop_owned(process)
                except (OSError,subprocess.TimeoutExpired):
                    blockers.append('cleanup_failed')
            try:
                event('supervisor_stopped')
            except OSError:
                blockers.append('event_write_failed')
    ended=wall()
    checked=review(folders,started,ended,mode=evidence_mode) if ended>started else {
        'blockers':['empty_capture_window'],'qualification':'unqualified'}
    result={'mode':'bounded_supervision','evidence_mode':evidence_mode,'started_at':started,'ended_at':ended,
        'review':checked,
        'segments':[str(f) for f in folders],'blockers':sorted(set(blockers+checked['blockers'])),
        'qualification':'unqualified','observed_days':0,'model_requests':0,'promotion_status':'blocked',
        'code_sha256':source_hashes(),'supervisor_sha256':sha(Path(__file__).read_bytes())}
    write_once(target/'supervisor.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    route=parser.add_mutually_exclusive_group(required=True)
    route.add_argument('--run',action='store_true')
    route.add_argument('--review',nargs='+',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seconds',type=int)
    parser.add_argument('--segment-seconds',type=int,default=86400)
    parser.add_argument('--overlap-seconds',type=int,default=300)
    parser.add_argument('--reserve-bytes',type=int)
    parser.add_argument('--start',type=float)
    parser.add_argument('--end',type=float)
    parser.add_argument('--mode',choices=('docker_follow','synthetic_fixture'),default='docker_follow')
    args=parser.parse_args()
    os.umask(0o077)
    try:
        if args.run:
            if os.name != 'posix' or args.seconds is None or args.reserve_bytes is None:
                parser.error('Live supervision needs Linux, explicit duration and disk reserve')
            segments=math.ceil(args.seconds/(args.segment_seconds-args.overlap_seconds))
            if args.reserve_bytes < 2*segments*MAX_BYTES:
                parser.error('Reserve must cover twice the full bounded diagnostic budget; add journal/export budget')
            result=supervise(args.output,args.seconds,args.segment_seconds,args.overlap_seconds,args.reserve_bytes)
        else:
            result=review(args.review,args.start,args.end,mode=args.mode)
            write_once(args.output,result)
    except (OSError,ValueError,TypeError,ZeroDivisionError):
        parser.exit(2,'Retention operation refused; preserve any partial attempt.\n')
    print(encode({k:result[k] for k in ('mode','blockers','qualification','observed_days','model_requests')}).decode().strip())
    if result['blockers']:
        raise SystemExit(2)


if __name__=='__main__':
    main()
