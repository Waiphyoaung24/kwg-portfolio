"""Memory-only authentication fixture; never imports real storage or opens sockets."""
import ast
from contextlib import nullcontext
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


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
