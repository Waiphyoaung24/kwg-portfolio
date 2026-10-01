"""Synthetic adapter check: no provider imports, credentials, network or source writes."""
import argparse
import ast
import hashlib
from pathlib import Path
import subprocess
import tempfile
import json
import sys
from dataclasses import dataclass, field
from types import SimpleNamespace, ModuleType
from urllib.parse import urlparse


def prepare_source(source: Path, patch: Path) -> bytes:
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != '19a23404ae7cdbe404c28b157fd2fc6766f7deec2a0db0423879601bb1fdd4f0':
        raise ValueError('Pinned provider source mismatch')
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        copied = root / 'agent/src/providers/openai_codex.py'
        copied.parent.mkdir(parents=True)
        copied.write_bytes(raw)
        subprocess.run(['git', 'apply', str(patch.resolve())], cwd=root, check=True, capture_output=True)
        return copied.read_bytes()


def invoke_fixture(source: bytes, request: dict, fixture: dict, *, fake_header_factory=None, audit=None) -> dict:
    """Real pinned request/SSE definitions, fake HTTP only; no auth definitions."""
    names = {'CodexToolCall', 'CodexAIMessage', 'OpenAICodexLLM', 'validate_codex_base_url',
        '_strip_model_prefix', '_prompt_cache_key', '_convert_user_message', '_split_tool_call_id',
        '_convert_messages', '_convert_tools', '_decode_tool_args', '_map_finish_reason',
        '_events_from_lines', '_message_chunks_from_events'}
    tree = ast.parse(source.decode('utf-8'))
    definitions = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    if {node.name for node in definitions} != names:
        raise ValueError('Provider definitions missing')
    module = ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')], level=0), *definitions], type_ignores=[])
    events = [{'type': 'response.output_text.delta', 'delta': fixture['response']},
        {'type': 'response.completed', 'response': {'status': 'completed', 'model': 'gpt-6.1-sol',
                                                  'usage': fixture['usage']}}]
    if fixture['tool_calls']:
        events.insert(0, {'type': 'response.output_item.done', 'item': {
            'type': 'function_call', 'call_id': 'synthetic', 'name': 'forbidden', 'arguments': '{}'}})
    wire = ''.join('data: ' + json.dumps(event) + '\n\n' for event in events).encode()
    calls = []

    class Response:
        status_code = fixture.get('http_status', 200)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_bytes(self, *, chunk_size):
            for index in range(0, len(wire), chunk_size):
                yield wire[index:index + chunk_size]

    class Client:
        def __init__(self, **options):
            if options != {'timeout': 120, 'follow_redirects': False, 'trust_env': False}:
                raise ValueError('Unsafe HTTP options')
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def stream(self, method, url, **options):
            if calls or method != 'POST' or url != 'https://chatgpt.com/backend-api/codex/responses':
                raise ValueError('Unexpected request or redispatch')
            body = options['json']
            if (body['model'] != 'gpt-6.1-sol' or body['reasoning'] != {'effort': 'medium'}
                    or body['max_output_tokens'] != 2048 or body['tool_choice'] != 'none'
                    or body['parallel_tool_calls'] or 'tools' in body
                    or body['input'] != [{'role': 'user', 'content': [{'type': 'input_text', 'text': request['prompt']}]}]):
                raise ValueError('Provider request mismatch')
            calls.append(body)
            if audit is not None:
                audit.append({'kind': 'fake_inference', 'status': fixture.get('http_status', 200)})
            return Response()

    # Register a private module for dataclass annotation resolution, not a provider import.
    loaded = ModuleType('batch3_synthetic_provider')
    namespace = loaded.__dict__
    namespace.update(httpx=SimpleNamespace(Client=Client), dataclass=dataclass, field=field,
        json=json, hashlib=hashlib, urlparse=urlparse, CodexStreamError=RuntimeError)
    sys.modules[loaded.__name__] = loaded
    try:
        exec(compile(ast.fix_missing_locations(module), '<pinned-fake-provider>', 'exec'), namespace)
        adapter = namespace['OpenAICodexLLM'](model=request['model'], reasoning_effort='medium',
            timeout=120, codex_url='https://chatgpt.com/backend-api/codex/responses', max_requests=1)
        # Optional in-memory fake auth seam; never import a credential store here.
        adapter._headers = fake_header_factory or (lambda **kwargs: {})
        message = adapter.invoke([{'role': 'user', 'content': request['prompt']}])
        if (len(calls) != 1 or message.tool_calls or message.response_metadata.get('finish_reason') != 'stop'
                or message.response_metadata.get('model_name') != 'gpt-6.1-sol'):
            raise ValueError('Invalid provider completion')
        return {'response': message.content, 'usage': message.usage_metadata,
                'fake_requests': len(calls), 'model_requests': 0}
    finally:
        sys.modules.pop(loaded.__name__, None)


def check(source: Path, patch: Path):
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '19a23404ae7cdbe404c28b157fd2fc6766f7deec2a0db0423879601bb1fdd4f0', 'Pinned provider source mismatch'
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        copied = root / 'agent/src/providers/openai_codex.py'
        copied.parent.mkdir(parents=True)
        copied.write_bytes(raw)
        subprocess.run(['git', 'apply', str(patch.resolve())], cwd=root, check=True,
                       capture_output=True)
        tree = ast.parse(copied.read_text(encoding='utf-8'))
        # Exercise the actual patched class without importing OAuth/config modules.
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == 'OpenAICodexLLM')
        module = ast.Module(body=[ast.ImportFrom(module='__future__',
            names=[ast.alias(name='annotations')], level=0), cls], type_ignores=[])
        posts, clients = [], []
        statuses = []
        wire_parts, chunks = [], []

        class Response:
            def __init__(self, status): self.status_code = status
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'synthetic-private-error'
            def iter_lines(self): return iter(())
            def iter_bytes(self, **kwargs): return iter(wire_parts)

        class Client:
            def __init__(self, **kwargs): clients.append(kwargs)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def stream(self, *args, **kwargs):
                posts.append(1)
                return Response(statuses.pop(0))

        class Error(RuntimeError):
            def __init__(self, status, detail): self.status_code = status

        def message_chunks(events):
            for _ in events:
                pass
            yield from chunks

        namespace = {'httpx': SimpleNamespace(Client=Client),
                     'validate_codex_base_url': lambda url: url,
                     'CodexStreamError': Error,
                     '_events_from_lines': lambda lines: lines,
                     '_message_chunks_from_events': message_chunks,
                     '_convert_messages': lambda messages: ('synthetic', []),
                     '_strip_model_prefix': lambda model: model,
                     '_prompt_cache_key': lambda messages: 'synthetic',
                     '_convert_tools': lambda tools: tools}
        exec(compile(ast.fix_missing_locations(module), '<synthetic-adapter>', 'exec'), namespace)
        adapter_type = namespace['OpenAICodexLLM']
        body = adapter_type(model='synthetic', codex_url='https://synthetic.invalid',
                            max_requests=1)._body([], stream=True)
        assert body['max_output_tokens'] == 2048 and body['tool_choice'] == 'none'
        assert not body['parallel_tool_calls'] and 'tools' not in body
        for status in (200, 401, 302, 429, 500):
            posts.clear()
            clients.clear()
            statuses[:] = [status, 200]
            adapter = adapter_type(model='synthetic', codex_url='https://synthetic.invalid',
                                   max_requests=1)
            headers = []
            adapter._headers = lambda **kwargs: headers.append(kwargs) or {}
            adapter._body = lambda *args, **kwargs: {}
            try:
                list(adapter.stream([]))
                assert status == 200
            except Error as error:
                assert error.status_code == status and status != 200
            assert len(posts) == 1 and headers == [{}]
            assert clients == [{'timeout': 120, 'follow_redirects': False, 'trust_env': False}]
        for wire, chunk in (
                ([b'x' * 262145], None),
                ([], SimpleNamespace(content='x' * 16385, tool_calls=[], usage_metadata=None)),
                ([], SimpleNamespace(content='', tool_calls=[{}], usage_metadata=None)),
                ([], SimpleNamespace(content='', tool_calls=[], usage_metadata={'output_tokens': 2049}))):
            wire_parts[:] = wire
            chunks[:] = [] if chunk is None else [chunk]
            statuses[:] = [200]
            posts.clear()
            adapter = adapter_type(model='synthetic', codex_url='https://synthetic.invalid', max_requests=1)
            adapter._headers = lambda **kwargs: {}
            try:
                list(adapter.stream([]))
                raise AssertionError('Bound violation accepted')
            except ValueError:
                pass
            assert len(posts) == 1
        wire_parts.clear()
        chunks.clear()
        for timeout in (121, -1, True, float('nan')):
            posts.clear()
            adapter = adapter_type(model='synthetic', codex_url='https://synthetic.invalid', max_requests=1)
            adapter._headers = lambda **kwargs: {}
            try:
                list(adapter.stream([], config={'timeout': timeout}))
                raise AssertionError('Invalid timeout accepted')
            except ValueError:
                pass
            assert not posts
        adapter = adapter_type(model='synthetic', codex_url='https://synthetic.invalid',
                               max_requests=1)
        posts.clear()
        try:
            list(adapter.bind_tools([{'name': 'synthetic'}]).stream([]))
            raise AssertionError('Tools were accepted')
        except ValueError:
            pass
        assert not posts
        for invalid in (True, 0, 3, 1.0):
            try:
                adapter_type(model='synthetic', max_requests=invalid)
                raise AssertionError('Invalid budget was accepted')
            except ValueError:
                pass
        # Preserve the existing app behavior when the explicit mode is omitted.
        posts.clear()
        clients.clear()
        statuses[:] = [401, 200]
        adapter = adapter_type(model='synthetic', codex_url='https://synthetic.invalid')
        adapter._headers = lambda **kwargs: {}
        adapter._body = lambda *args, **kwargs: {}
        list(adapter.stream([]))
        assert len(posts) == 2
        assert clients[0]['follow_redirects'] and clients[0]['trust_env']
        assert adapter.bind_tools([]).max_requests == 2
        print('PASS: source pin, HTTP outcomes, tool/token/stream/response bounds and legacy behavior; actual network requests=0')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--patch', type=Path,
                        default=Path(__file__).with_name('vibe-codex-one-request.patch'))
    args = parser.parse_args()
    check(args.source, args.patch)
