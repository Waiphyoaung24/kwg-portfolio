"""Pinned OAuth state machine with fake storage/refresh; no secrets, sockets or login."""
import importlib.util
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location('fake_codex_guard', Path(__file__).with_name('check-vibe-codex-guard.py'))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
SOURCE = Path(__file__).resolve().parents[2] / '.batch3-vibe/upstream/agent/src/providers/openai_codex.py'
FIXTURE = {'response': 'synthetic', 'tool_calls': [], 'delay_seconds': 0,
           'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}
REQUEST = {'model': 'openai-codex/gpt-6.1-sol', 'prompt': 'Synthetic credential-boundary check'}


from batch3_auth_fixture import fake_auth


class AuthBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = guard.prepare_source(SOURCE, Path(__file__).with_name('vibe-codex-one-request.patch'))

    def test_fresh_and_expired_success_one_inference(self):
        for expired in (False, True):
            headers, refresh, cleared = fake_auth(self.source, expired=expired)
            audit = []
            result = guard.invoke_fixture(self.source, REQUEST, FIXTURE, fake_header_factory=headers, audit=audit)
            self.assertEqual(result['fake_requests'], 1)
            self.assertEqual(result['model_requests'], 0)
            self.assertEqual(refresh, ['fake_refresh'] if expired else [])
            self.assertEqual(len(audit), 1)
            self.assertEqual(cleared, [])
            self.assertNotIn('CANARY', str(result) + str(audit))

    def test_refresh_failure_or_stale_token_prevents_inference(self):
        for failure in ('permanent', 'timeout', 'stale'):
            headers, refresh, cleared = fake_auth(self.source, expired=True, refresh=failure)
            audit = []
            with self.assertRaises(RuntimeError) as error:
                guard.invoke_fixture(self.source, REQUEST, FIXTURE, fake_header_factory=headers, audit=audit)
            self.assertEqual(refresh, ['fake_refresh'])
            self.assertEqual(audit, [])
            self.assertEqual(cleared, ['fake_clear'] if failure in ('permanent', 'stale') else [])
            self.assertNotIn('CANARY', str(error.exception))

    def test_401_never_refreshes_or_redispatches_after_inference(self):
        headers, refresh, _ = fake_auth(self.source)
        audit = []
        with self.assertRaises(RuntimeError):
            guard.invoke_fixture(self.source, REQUEST, {**FIXTURE, 'http_status': 401},
                                 fake_header_factory=headers, audit=audit)
        self.assertEqual(refresh, [])
        self.assertEqual(audit, [{'kind': 'fake_inference', 'status': 401}])

    def test_parent_deadline_stops_delayed_auth_before_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'inference-started'
            script = (
                "import sys; from pathlib import Path; sys.path.insert(0,sys.argv[1]); "
                "from test_batch3_auth_boundary import fake_auth; "
                "headers,_,_=fake_auth(Path(sys.argv[2]).read_bytes(),expired=True,refresh='delay'); "
                "headers(); Path(sys.argv[3]).write_text('fake inference would start here')")
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run([sys.executable, '-I', '-S', '-B', '-c', script,
                                str(Path(__file__).parent), str(SOURCE), str(marker)],
                               capture_output=True, timeout=.2)
            self.assertLess(time.monotonic() - started, 2)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
