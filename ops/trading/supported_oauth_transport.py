"""Fixed Responses core; fake harness and separately gated isolated worker entry."""
import time
import os
import sys

from batch3_runner import MAX_BYTES
from trusted_oauth_transport import strict_json

URL = 'https://api.openai.com/v1/responses'
MODEL = 'gpt-5.6-sol'
MAX_STREAM = 262144
MAX_EVENT = 65536
STREAM_SECONDS = 120


def checked_failure(value):
    """Only fixed labels cross the credential-bearing worker boundary."""
    codes = {'transport': ('exception',), 'http': ('refused',),
        'stream': ('limit', 'malformed', 'identity', 'usage', 'truncated', 'tools', 'provider', 'exception'),
        'worker': ('initialization', 'reply'), 'controller': ('exception',), 'cleanup': ('unverified',)}
    if (not isinstance(value, dict) or not isinstance(value.get('stage'), str)
            or value['stage'] not in codes or value.get('code') not in codes[value['stage']]):
        raise ValueError('Invalid diagnostic')
    fields = {'stage', 'code'}
    if (value['stage'], value['code']) == ('http', 'refused'):
        fields.add('http_status')
        if type(value.get('http_status')) is not int or not 100 <= value['http_status'] <= 599:
            raise ValueError('Invalid diagnostic')
    if (value['stage'], value['code']) == ('stream', 'provider'):
        fields.add('provider_code')
        if value.get('provider_code') not in ('subscription_sharing_usage_limit_exceeded',
                'subscription_sharing_usage_unavailable', 'unknown'):
            raise ValueError('Invalid diagnostic')
    if set(value) != fields: raise ValueError('Invalid diagnostic')
    return dict(value)


class ProposalFailure(ValueError):
    def __init__(self, stage, code, **metadata):
        self.diagnostic = checked_failure(dict(stage=stage, code=code, **metadata))
        super().__init__('Proposal refused: '+stage+'/'+code)


def request_body(prompt):
    return {'model': MODEL, 'reasoning': {'effort': 'medium'},
            'input': [{'role': 'user', 'content': prompt}], 'store': False, 'stream': True}


def parse_stream(chunks):
    pending = bytearray()
    received = 0
    text = ''
    completed = None
    response_id = None
    sequence = -1
    started = time.monotonic()
    for chunk in chunks:
        if not isinstance(chunk, bytes) or len(chunk) > MAX_EVENT or time.monotonic()-started > STREAM_SECONDS:
            raise ProposalFailure('stream', 'limit')
        received += len(chunk)
        if received > MAX_STREAM:
            raise ProposalFailure('stream', 'limit')
        pending.extend(chunk)
        while b'\n\n' in pending or b'\r\n\r\n' in pending:
            lf, crlf = pending.find(b'\n\n'), pending.find(b'\r\n\r\n')
            end, width = (crlf, 4) if crlf >= 0 and (lf < 0 or crlf < lf) else (lf, 2)
            if end > MAX_EVENT:
                raise ProposalFailure('stream', 'limit')
            frame = bytes(pending[:end]).decode('utf-8')
            del pending[:end+width]
            data, label = [], None
            for line in frame.splitlines():
                if not line or line.startswith(':'):
                    continue
                field, sep, value = line.partition(':')
                if not sep or field not in ('event', 'data'):
                    raise ProposalFailure('stream', 'malformed')
                value = value.removeprefix(' ')
                if field == 'data': data.append(value)
                elif label is None: label = value
                else: raise ProposalFailure('stream', 'malformed')
            if not data:
                continue
            if completed is not None:
                raise ProposalFailure('stream', 'malformed')
            event = strict_json('\n'.join(data))
            if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                raise ProposalFailure('stream', 'malformed')
            kind = event['type']
            if label is not None and label != kind:
                raise ProposalFailure('stream', 'identity')
            if 'sequence_number' in event:
                n = event['sequence_number']
                if type(n) is not int or n <= sequence:
                    raise ProposalFailure('stream', 'malformed')
                sequence = n
            if kind in ('response.created', 'response.in_progress', 'response.completed'):
                response = event.get('response')
                if (not isinstance(response, dict) or not isinstance(response.get('id'), str)
                        or not response['id'] or response.get('model') != MODEL):
                    raise ProposalFailure('stream', 'identity')
                if response_id is not None and response_id != response['id']:
                    raise ProposalFailure('stream', 'identity')
                response_id = response['id']
                if kind == 'response.completed':
                    if response.get('status') != 'completed' or response.get('error') is not None:
                        raise ProposalFailure('stream', 'truncated')
                    completed = response
            elif kind == 'response.output_text.delta':
                if not isinstance(event.get('delta'), str):
                    raise ProposalFailure('stream', 'malformed')
                text += event['delta']
                if len(text.encode()) > MAX_BYTES:
                    raise ProposalFailure('stream', 'limit')
            elif kind == 'response.output_text.done':
                if event.get('text') != text:
                    raise ProposalFailure('stream', 'malformed')
            elif kind in ('response.output_item.added', 'response.output_item.done'):
                item = event.get('item')
                if not isinstance(item, dict) or item.get('type') not in ('message', 'reasoning'):
                    raise ProposalFailure('stream', 'tools')
            elif kind in ('response.content_part.added', 'response.content_part.done'):
                part = event.get('part')
                if not isinstance(part, dict) or part.get('type') != 'output_text':
                    raise ProposalFailure('stream', 'malformed')
            elif kind in ('response.failed', 'response.incomplete', 'error'):
                response = event.get('response')
                error = response.get('error') if isinstance(response, dict) else event.get('error')
                code = error.get('code') if isinstance(error, dict) else None
                if code not in ('subscription_sharing_usage_limit_exceeded', 'subscription_sharing_usage_unavailable'):
                    code = 'unknown'
                raise ProposalFailure('stream', 'provider', provider_code=code)
            elif kind not in ('response.reasoning_summary_part.added', 'response.reasoning_summary_part.done',
                              'response.reasoning_summary_text.delta', 'response.reasoning_summary_text.done'):
                # Includes failed/incomplete/error and plan-sharing usage errors after partial output.
                raise ProposalFailure('stream', 'malformed')
        if len(pending) > MAX_EVENT:
            raise ProposalFailure('stream', 'limit')
    if pending or completed is None or time.monotonic()-started > STREAM_SECONDS:
        raise ProposalFailure('stream', 'truncated')
    output = completed.get('output')
    if not isinstance(output, list) or not output:
        raise ProposalFailure('stream', 'malformed')
    terminal_text = ''
    for item in output:
        if not isinstance(item, dict):
            raise ProposalFailure('stream', 'malformed')
        if item.get('type') == 'reasoning':
            continue
        if item.get('type') != 'message' or item.get('role') != 'assistant' or item.get('status') != 'completed':
            raise ProposalFailure('stream', 'tools')
        content = item.get('content')
        if not isinstance(content, list):
            raise ProposalFailure('stream', 'malformed')
        for part in content:
            if not isinstance(part, dict) or part.get('type') != 'output_text' or not isinstance(part.get('text'), str):
                raise ProposalFailure('stream', 'malformed')
            terminal_text += part['text']
    if terminal_text != text or len(terminal_text.encode()) > MAX_BYTES:
        raise ProposalFailure('stream', 'malformed')
    usage = completed.get('usage')
    if (not isinstance(usage, dict) or not {'input_tokens', 'output_tokens', 'total_tokens'} <= usage.keys()
            or not usage.keys() <= {'input_tokens', 'output_tokens', 'total_tokens',
                                    'input_tokens_details', 'output_tokens_details'}
            or any(type(usage[k]) is not int or usage[k] < 0 for k in ('input_tokens', 'output_tokens', 'total_tokens'))
            or usage['total_tokens'] != usage['input_tokens']+usage['output_tokens']):
        raise ProposalFailure('stream', 'usage')
    for key, field, total in (('input_tokens_details', 'cached_tokens', 'input_tokens'),
                              ('output_tokens_details', 'reasoning_tokens', 'output_tokens')):
        if key in usage:
            details = usage[key]
            if (not isinstance(details, dict) or set(details) != {field} or type(details[field]) is not int
                    or not 0 <= details[field] <= usage[total]):
                raise ProposalFailure('stream', 'usage')
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
    stage = 'transport'
    try:
        with http_module.Client(timeout=http_module.Timeout(connect=10, read=30, write=10, pool=10),
                trust_env=False, follow_redirects=False, verify=True, proxy=proxy) as client:
            with client.stream('POST', URL, headers={'Authorization': 'Bearer '+access_token,
                    'Accept': 'text/event-stream', 'Accept-Encoding': 'identity'},
                    json=request_body(prompt)) as response:
                if (response.status_code != 200
                        or response.headers.get('content-type', '').split(';')[0] != 'text/event-stream'
                        or response.headers.get('content-encoding', 'identity') != 'identity'):
                    raise ProposalFailure('http', 'refused', http_status=response.status_code)
                stage = 'stream'
                return parse_stream(response.iter_raw(chunk_size=4096))
    except ProposalFailure:
        raise
    except Exception:
        raise ProposalFailure(stage, 'exception') from None


def dispatch(*args, **kwargs):
    raise ValueError('Live dispatch disabled: production isolation, account and billing gates unverified')
