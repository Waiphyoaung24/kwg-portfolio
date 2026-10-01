"""Pinned OAuth state machine with fake storage/refresh; no secrets, sockets or login."""
import ast
from contextlib import nullcontext
import importlib.util
from pathlib import Path
import sys
import subprocess
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fake_codex_guard', Path(__file__).with_name('check-vibe-codex-guard.py'))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
SOURCE = Path(__file__).resolve().parents[2] / '.batch3-vibe/upstream/agent/src/providers/openai_codex.py'
FIXTURE = {'response': 'synthetic', 'tool_calls': [], 'delay_seconds': 0,
           'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}
REQUEST = {'model': 'openai-codex/gpt-6.1-sol', 'prompt': 'Synthetic credential-boundary check'}


def fake_auth(source, *, expired=False, refresh='success'):
    names = {'CodexStreamError', 'CodexAuthenticationError', '_CodexRefreshError',
             '_refresh_codex_token', '_missing_codex_login_error', '_get_codex_token', '_build_headers'}
    definitions = [n for n in ast.parse(source.decode()).body
                   if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    if {n.name for n in definitions} != names:
        raise ValueError('Pinned auth definitions missing')
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
                              *definitions], type_ignores=[])
    token = SimpleNamespace(access='FAKE_ACCESS_CANARY', refresh='FAKE_REFRESH_CANARY',
                            account_id='synthetic-account', expires=0 if expired else 1000000)
    calls = []
    cleared = []
    storage = SimpleNamespace(load=lambda: token)
    sdk = ModuleType('oauth_cli_kit')

    def get_token(**kwargs):
        assert kwargs['storage'] is storage and kwargs['min_ttl_seconds'] == 2147483647
        calls.append('fake_refresh')
        if refresh == 'permanent':
            raise RuntimeError('invalid_grant FAKE_REFRESH_CANARY')
        if refresh == 'timeout':
            raise TimeoutError('FAKE_REFRESH_CANARY')
        if refresh == 'stale':
            return token
        if refresh == 'delay':
            time.sleep(2)
        return SimpleNamespace(access='FAKE_REPLACEMENT_CANARY', account_id='synthetic-account')

    sdk.get_token = get_token
    ns = {'time': SimpleNamespace(time=lambda: 0), '_build_codex_token_storage': lambda: storage,
          '_codex_refresh_lock': lambda s: nullcontext(), '_token_expiry_ms': lambda t: t.expires,
          '_clear_codex_token': lambda s: cleared.append('fake_clear'),
          '_load_codex_oauth_provider': lambda: 'synthetic-provider',
          '_CODEX_REFRESH_MARGIN_SECONDS': 300, '_CODEX_FORCE_REFRESH_TTL_SECONDS': 2147483647,
          '_CODEX_LOGIN_COMMAND': 'vibe-trading provider login openai-codex',
          '_PERMANENT_REFRESH_ERROR_CODES': {'invalid_grant'}, 'DEFAULT_ORIGINATOR': 'vibe-trading'}
    exec(compile(ast.fix_missing_locations(module), '<pinned-fake-auth>', 'exec'), ns)

    def headers(**kwargs):
        with patch.dict(sys.modules, {'oauth_cli_kit': sdk}):
            result = ns['_get_codex_token'](**kwargs)
        return ns['_build_headers'](result.account_id, result.access)

    return headers, calls, cleared


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
