import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import signal

from retention_supervisor import review, supervise, stop_owned


def segment(path, stamps, hashes=None):
    path.mkdir()
    rows = [{'kind': 'sample', 'received_at': s, 'health': {'sampled_at': s},
             'record_sha256': (hashes or {}).get(s, hashlib.sha256(str(s).encode()).hexdigest())}
            for s in stamps]
    raw = b''.join((json.dumps(r)+'\n').encode() for r in rows)
    (path/'diagnostics.jsonl').write_bytes(raw)
    from retention_supervisor import source_hashes
    receipt = {'mode':'synthetic_fixture','stop_reason':'timeout','sample_count':len(stamps),
        'gap_count':0,'rejected_frame_count':0,'trailing_unparsed_bytes':0,
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'code_sha256':source_hashes(),
        'qualification':'unqualified','observed_days':0,'model_requests':0,
        'promotion_status':'blocked','completeness_verified':False,
        'started_at':stamps[0], 'ended_at':stamps[-1]}
    (path/'receipt.json').write_text(json.dumps(receipt))


class RetentionTest(unittest.TestCase):
    def test_malformed_receipt_and_duplicate_segment_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'segment'
            segment(path,[1000,1005])
            with self.assertRaises(ValueError):
                review([path,path],1000,1005,mode='synthetic_fixture')
            original=(path/'receipt.json').read_bytes()
            for raw in (b'[]', b'{"unused":1e999}', b'{"x":1,"x":2}'):
                (path/'receipt.json').write_bytes(raw)
                self.assertIn('segment_integrity_failed',review([path],1000,1005,mode='synthetic_fixture')['blockers'])
            changed=json.loads(original)
            changed['sample_count']=True
            (path/'receipt.json').write_text(json.dumps(changed))
            self.assertIn('segment_integrity_failed',review([path],1000,1005,mode='synthetic_fixture')['blockers'])

    def test_segment_clock_faults_are_blockers(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'segment'
            segment(path,[1000,1010,1005,1015])
            receipt=json.loads((path/'receipt.json').read_bytes())
            receipt['gap_count']=1
            (path/'receipt.json').write_text(json.dumps(receipt))
            self.assertIn('segment_sample_gap',review([path],1000,1015,mode='synthetic_fixture')['blockers'])
            receipt.update(started_at=5000,ended_at=4000)
            (path/'receipt.json').write_text(json.dumps(receipt))
            self.assertIn('segment_integrity_failed',review([path],1000,1015,mode='synthetic_fixture')['blockers'])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'segment'
            segment(path,[1000,1030])
            rows=[json.loads(line) for line in (path/'diagnostics.jsonl').read_bytes().splitlines()]
            rows[-1]['received_at']=1060
            raw=b''.join((json.dumps(row)+'\n').encode() for row in rows)
            (path/'diagnostics.jsonl').write_bytes(raw)
            receipt=json.loads((path/'receipt.json').read_bytes())
            receipt.update(ended_at=1060,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            (path/'receipt.json').write_text(json.dumps(receipt))
            self.assertIn('segment_receive_boundary_or_clock_gap',review([path],1000,1060,mode='synthetic_fixture')['blockers'])

    def test_owned_process_group_cleanup(self):
        class Process:
            pid=123
            _retention_group=True
            def poll(self): return None
            def wait(self,timeout):
                if not hasattr(self,'waited'):
                    self.waited=True
                    raise subprocess.TimeoutExpired('fake',timeout)
                return 0
        with patch('os.killpg',create=True) as kill:
            stop_owned(Process())
        self.assertEqual(kill.call_args_list[0].args,(123,signal.SIGTERM))
        self.assertEqual(kill.call_args_list[-1].args,(123,getattr(signal,'SIGKILL',9)))

    def test_exited_group_leader_does_not_leave_descendants(self):
        class Process:
            pid=123
            _retention_group=True
            def poll(self): return 0
            def wait(self,timeout): return 0
        with patch('os.killpg',create=True) as kill:
            stop_owned(Process())
        self.assertEqual(kill.call_args_list[-1].args,(123,getattr(signal,'SIGKILL',9)))

    def test_early_exit_and_cleanup_failure_are_recorded(self):
        for code,expected in [(0,'follower_ended_early'),(None,'cleanup_failed')]:
            with tempfile.TemporaryDirectory() as folder:
                class Clock:
                    value=0
                    def now(self): return self.value
                    def sleep(self,n): self.value+=n
                class Process:
                    def poll(self): return code
                    def terminate(self): raise OSError('Fake cleanup failure')
                    def wait(self,timeout): return code
                clock=Clock(); launched=[]
                def launch(*args):
                    launched.append(args)
                    return Process()
                result=supervise(Path(folder)/'run',40,40,5,1024,
                    launch=launch,clock=clock.now,wall=lambda:1000+clock.value,
                    sleep=clock.sleep,space=lambda:10**9)
                self.assertIn(expected,result['blockers'])
                self.assertEqual(len(launched),1)
                self.assertTrue((Path(folder)/'run'/'supervisor.json').exists())

    def test_supervisor_healthy_overlap_rehearsal(self):
        with tempfile.TemporaryDirectory() as folder:
            class Clock:
                value=0
                def now(self): return self.value
                def sleep(self,n): self.value+=n
            clock=Clock()
            class Process:
                def __init__(self,path,duration):
                    self.path,self.begin,self.duration=path,clock.value,duration
                    self.saved=False
                def poll(self):
                    if clock.value < self.begin+self.duration: return None
                    if not self.saved:
                        segment(self.path,list(range(1000+int(self.begin),1001+int(self.begin+self.duration),5)))
                        self.saved=True
                    return 0
                def wait(self,timeout): return self.poll()
            result=supervise(Path(folder)/'run',35,20,5,1024,
                launch=Process,clock=clock.now,wall=lambda:1000+clock.value,
                sleep=clock.sleep,space=lambda:10**9,evidence_mode='synthetic_fixture')
            self.assertEqual(result['blockers'],[])
            self.assertEqual(len(result['segments']),2)
            self.assertEqual(result['review']['unique_samples'],8)

    def test_overlap_conflict_boundaries_and_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b = Path(folder)/'a',Path(folder)/'b'
            segment(a,[1000,1005,1010]); segment(b,[1005,1010,1015,1020])
            result = review([a,b],1000,1020,mode='synthetic_fixture')
            self.assertEqual(result['blockers'], [])
            self.assertEqual(result['unique_samples'],5)
            self.assertEqual(result['observed_days'],0)
            self.assertIn('start_boundary_gap',review([a,b],900,1020,mode='synthetic_fixture')['blockers'])
            raw = (b/'diagnostics.jsonl').read_bytes()
            (b/'diagnostics.jsonl').write_bytes(raw+b'changed')
            self.assertIn('segment_integrity_failed',review([a,b],1000,1020,mode='synthetic_fixture')['blockers'])
        with tempfile.TemporaryDirectory() as folder:
            a,b = Path(folder)/'a',Path(folder)/'b'
            segment(a,[1000,1005]); segment(b,[1005,1010],{1005:'0'*64})
            self.assertIn('conflicting_sample',review([a,b],1000,1010,mode='synthetic_fixture')['blockers'])

    def test_no_overlap_and_silence(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b = Path(folder)/'a',Path(folder)/'b'
            segment(a,[1000,1005]); segment(b,[1040,1045])
            blockers=review([a,b],1000,1045,mode='synthetic_fixture')['blockers']
            self.assertIn('missing_overlap',blockers)
            self.assertIn('sample_gap',blockers)

    def test_low_disk_refuses_launch(self):
        with tempfile.TemporaryDirectory() as folder:
            launched=[]
            result=supervise(Path(folder)/'run',40,20,5,1024,
                launch=lambda *args: launched.append(args),space=lambda:0)
            self.assertEqual(launched,[])
            self.assertIn('disk_reserve_unavailable',result['blockers'])

    def test_silence_and_exit_stop_owned_followers(self):
        for exit_code,expected in [(None,'writer_stale'),(2,'follower_failed')]:
            with tempfile.TemporaryDirectory() as folder:
                class Clock:
                    value=0
                    def now(self): return self.value
                    def sleep(self,n): self.value+=n
                class Process:
                    stopped=False
                    def poll(self): return exit_code
                    def terminate(self): self.stopped=True
                    def wait(self,timeout): return 0
                clock=Clock(); process=Process()
                result=supervise(Path(folder)/'run',40,40,5,1024,
                    launch=lambda *args:process,clock=clock.now,wall=lambda:1000+clock.value,
                    sleep=clock.sleep,space=lambda:10**9)
                self.assertIn(expected,result['blockers'])
                if exit_code is None: self.assertTrue(process.stopped)


if __name__ == '__main__':
    unittest.main()
