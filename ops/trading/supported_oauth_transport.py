"""Fixed Responses core; fake harness and separately gated isolated worker entry."""
import time
import os
import sys

from batch3_runner import MAX_BYTES
from trusted_oauth_transport import strict_json

URL = 'https://api.openai.com/v1/responses'
MODEL = 'gpt-6-astra'
MAX_STREAM = 262144
MAX_EVENT = 65536


def parse_stream(chunks):
    pending = bytearray()
    received = 0
    text = ''
    completed = None
    response_id = None
    sequence = -1
    started = time.monotonic()
    for chunk in chunks:
        if not isinstance(chunk, bytes) or len(chunk) > MAX_EVENT or time.monotonic()-started > 120:
            raise ValueError('Stream limit')
        received += len(chunk)
        if received > MAX_STREAM:
            raise ValueError('Stream limit')
        pending.extend(chunk)
        while b'\n\n' in pending or b'\r\n\r\n' in pending:
            lf, crlf = pending.find(b'\n\n'), pending.find(b'\r\n\r\n')
            end, width = (crlf, 4) if crlf >= 0 and (lf < 0 or crlf < lf) else (lf, 2)
            if end > MAX_EVENT:
                raise ValueError('Event limit')
            frame = bytes(pending[:end]).decode('utf-8')
            del pending[:end+width]
            data, label = [], None
            for line in frame.splitlines():
                if not line or line.startswith(':'):
                    continue
                field, sep, value = line.partition(':')
                if not sep or field not in ('event', 'data'):
                    raise ValueError('Invalid SSE field')
                value = value.removeprefix(' ')
                if field == 'data': data.append(value)
                elif label is None: label = value
                else: raise ValueError('Duplicate SSE event')
            if not data:
                continue
            if completed is not None:
                raise ValueError('Data after terminal event')
            event = strict_json('\n'.join(data))
            if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                raise ValueError('Invalid event')
            kind = event['type']
            if label is not None and label != kind:
                raise ValueError('Event identity mismatch')
            if 'sequence_number' in event:
                n = event['sequence_number']
                if type(n) is not int or n <= sequence:
                    raise ValueError('Invalid event sequence')
                sequence = n
            if kind in ('response.created', 'response.in_progress', 'response.completed'):
                response = event.get('response')
                if (not isinstance(response, dict) or not isinstance(response.get('id'), str)
                        or not response['id'] or response.get('model') != MODEL):
                    raise ValueError('Response identity mismatch')
                if response_id is not None and response_id != response['id']:
                    raise ValueError('Response identity mismatch')
                response_id = response['id']
                if kind == 'response.completed':
                    if response.get('status') != 'completed' or response.get('error') is not None:
                        raise ValueError('Incomplete response')
                    completed = response
            elif kind == 'response.output_text.delta':
                if not isinstance(event.get('delta'), str):
                    raise ValueError('Invalid delta')
                text += event['delta']
                if len(text.encode()) > MAX_BYTES:
                    raise ValueError('Proposal limit')
            elif kind == 'response.output_text.done':
                if event.get('text') != text:
                    raise ValueError('Text mismatch')
            elif kind in ('response.output_item.added', 'response.output_item.done'):
                item = event.get('item')
                if not isinstance(item, dict) or item.get('type') not in ('message', 'reasoning'):
                    raise ValueError('Tools or invalid item')
            elif kind in ('response.content_part.added', 'response.content_part.done'):
                part = event.get('part')
                if not isinstance(part, dict) or part.get('type') != 'output_text':
                    raise ValueError('Invalid content')
            elif kind not in ('response.reasoning_summary_part.added', 'response.reasoning_summary_part.done',
                              'response.reasoning_summary_text.delta', 'response.reasoning_summary_text.done'):
                # Includes failed/incomplete/error and plan-sharing usage errors after partial output.
                raise ValueError('Unexpected or failed event')
        if len(pending) > MAX_EVENT:
            raise ValueError('Event limit')
    if pending or completed is None or time.monotonic()-started > 120:
        raise ValueError('Truncated stream')
    output = completed.get('output')
    if not isinstance(output, list) or not output:
        raise ValueError('Missing completed output')
    terminal_text = ''
    for item in output:
        if not isinstance(item, dict):
            raise ValueError('Invalid output')
        if item.get('type') == 'reasoning':
            continue
        if item.get('type') != 'message' or item.get('role') != 'assistant' or item.get('status') != 'completed':
            raise ValueError('Tools or incomplete output')
        content = item.get('content')
        if not isinstance(content, list):
            raise ValueError('Invalid output content')
        for part in content:
            if not isinstance(part, dict) or part.get('type') != 'output_text' or not isinstance(part.get('text'), str):
                raise ValueError('Invalid output content')
            terminal_text += part['text']
    if terminal_text != text or len(terminal_text.encode()) > MAX_BYTES:
        raise ValueError('Completed text mismatch')
    usage = completed.get('usage')
    if (not isinstance(usage, dict) or not {'input_tokens', 'output_tokens', 'total_tokens'} <= usage.keys()
            or not usage.keys() <= {'input_tokens', 'output_tokens', 'total_tokens',
                                    'input_tokens_details', 'output_tokens_details'}
            or any(type(usage[k]) is not int or usage[k] < 0 for k in ('input_tokens', 'output_tokens', 'total_tokens'))
            or usage['total_tokens'] != usage['input_tokens']+usage['output_tokens']):
        raise ValueError('Invalid usage')
    for key, field, total in (('input_tokens_details', 'cached_tokens', 'input_tokens'),
                              ('output_tokens_details', 'reasoning_tokens', 'output_tokens')):
        if key in usage:
            details = usage[key]
            if (not isinstance(details, dict) or set(details) != {field} or type(details[field]) is not int
                    or not 0 <= details[field] <= usage[total]):
                raise ValueError('Invalid usage details')
    # Proposal validation runs later in a separate credential-free, network-none process.
    return {'text': text, 'usage': usage,
            'model': MODEL, 'reasoning_effort': 'medium', 'promotion_status': 'blocked'}


def invoke_fake(prompt, access_token, http_module, proxy):
    """Dependency-injected test core; not connected to a credential store or live entry."""
    if (not isinstance(prompt, str) or len(prompt.encode()) > MAX_BYTES
            or not isinstance(access_token, str) or not access_token.startswith('FAKE_CANARY_')
            or any(c in access_token for c in '\r\n')):
        raise ValueError('Fake credential and bounded prompt required')
    return _invoke(prompt, access_token, http_module, proxy)


def invoke_isolated(prompt, access_token):
    """Fixed worker entry; only the separately sealed controller transfers auth."""
    if (os.name != 'posix' or not sys.flags.isolated or os.getuid() != 65534
            or not isinstance(prompt, str) or not 0 < len(prompt.encode()) <= MAX_BYTES
            or not isinstance(access_token, str) or not 0 < len(access_token) <= 16384
            or any(c in access_token for c in '\r\n')):
        raise ValueError('Isolated worker and bounded access input required')
    import httpx
    return _invoke(prompt, access_token, httpx, 'http://kwg-egress:3128')


def _invoke(prompt, access_token, http_module, proxy):
    try:
        with http_module.Client(timeout=http_module.Timeout(connect=10, read=30, write=10, pool=10),
                trust_env=False, follow_redirects=False, verify=True, proxy=proxy) as client:
            with client.stream('POST', URL, headers={'Authorization': 'Bearer '+access_token,
                    'Accept': 'text/event-stream', 'Accept-Encoding': 'identity'},
                    json={'model': MODEL, 'reasoning': {'effort': 'medium'},
                          'input': [{'role': 'user', 'content': prompt}], 'store': False, 'stream': True}) as response:
                if (response.status_code != 200
                        or response.headers.get('content-type', '').split(';')[0] != 'text/event-stream'
                        or response.headers.get('content-encoding', 'identity') != 'identity'):
                    raise ValueError('Invalid HTTP response')
                return parse_stream(response.iter_raw(chunk_size=4096))
    except Exception:
        raise ValueError('Supported request failed; no retry or sensitive details recorded') from None


def dispatch(*args, **kwargs):
    raise ValueError('Live dispatch disabled: production isolation, account and billing gates unverified')
