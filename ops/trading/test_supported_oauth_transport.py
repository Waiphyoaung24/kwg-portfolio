import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import supported_oauth_transport as transport


TEXT = json.dumps({'kind': 'ema20_slope_filter', 'lookback_bars': 3, 'hypothesis': 'Synthetic supported-route fixture'})


def events():
    return [{'type': 'response.created', 'response': {'id': 'fake-response', 'model': transport.MODEL}},
            {'type': 'response.output_text.delta', 'delta': TEXT},
            {'type': 'response.completed', 'response': {'id': 'fake-response', 'model': transport.MODEL,
                'status': 'completed', 'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                    'content': [{'type': 'output_text', 'text': TEXT}]}],
                'usage': {'input_tokens': 10, 'output_tokens': 3000, 'total_tokens': 3010,
                    'output_tokens_details': {'reasoning_tokens': 2900}}}}]


def wire(values, separator='\n'):
    return ''.join('event: '+value['type']+separator+'data: '+json.dumps(value)+separator*2 for value in values).encode()


class SupportedTransportTest(unittest.TestCase):
    def test_completed_stream_and_failure_matrix(self):
        raw = wire(events())
        for separator in ('\n', '\r\n'):
            data = wire(events(), separator)
            for size in (1, 7, 4096):
                result = transport.parse_stream(data[i:i+size] for i in range(0, len(data), size))
                self.assertEqual(result['usage']['output_tokens'], 3000)  # No legacy server cap claim.
                self.assertNotIn('FAKE_CANARY', json.dumps(result))
        failures = [raw[:-1], wire(events()[:-1]), raw+wire([events()[-1]]),
                    b'data: {broken}\n\n', b'data: {"type":"error","type":"response.created"}\n\n',
                    b'event: wrong\n'+raw, b'data: '+b'x'*(transport.MAX_EVENT+1),
                    wire([{'type': 'response.output_text.delta', 'delta': 'x'*(transport.MAX_BYTES+1)}]),
                    wire([{'type': 'response.output_item.added', 'item': {'type': 'function_call'}}])]
        for code in ('subscription_sharing_usage_limit_exceeded', 'subscription_sharing_usage_unavailable'):
            failures.append(wire(events()[:-1]+[{'type': 'response.failed', 'response': {'error': {'code': code}}}]))
        for field, value in [('model', 'wrong'), ('id', 'wrong'), ('status', 'incomplete'), ('usage', None),
                              ('output', []), ('error', {'code': 'unavailable'})]:
            values = events()
            values[-1]['response'][field] = value
            failures.append(wire(values))
        for usage in ({'input_tokens': True, 'output_tokens': 2, 'total_tokens': 3},
                      {'input_tokens': 1, 'output_tokens': -1, 'total_tokens': 0},
                      {'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 4},
                      {'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 3, 'secret': 'FAKE_CANARY'},
                      {'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 3,
                       'output_tokens_details': {'reasoning_tokens': 3}}):
            values = events()
            values[-1]['response']['usage'] = usage
            failures.append(wire(values))
        values = events()
        values[-1]['response']['output'][0]['content'][0]['text'] = 'different'
        failures.append(wire(values))
        values = events()
        values[0]['sequence_number'] = 2
        values[1]['sequence_number'] = 1
        failures.append(wire(values))
        for raw in failures:
            with self.subTest(raw=raw[:80]), self.assertRaises((ValueError, UnicodeError)):
                transport.parse_stream([raw])
        with self.assertRaisesRegex(ValueError, 'stream/limit'):
            transport.parse_stream([b': heartbeat\n\n']*(transport.MAX_STREAM//13+1))
        with patch.object(transport.time, 'monotonic', side_effect=[0, 121]):
            with self.assertRaises(ValueError): transport.parse_stream([wire(events())])

    def test_exact_request_one_post_failures_and_dispatch_refusal(self):
        calls = []
        options = []
        status = 200
        headers = {'content-type': 'text/event-stream'}
        test = self
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            @property
            def status_code(self): return status
            @property
            def headers(self): return headers
            def iter_raw(self, **kwargs):
                test.assertEqual(kwargs, {'chunk_size': 4096})
                yield wire(events())
        class Client:
            def __init__(self, **kwargs): options.append(kwargs)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def stream(self, *args, **kwargs):
                calls.append((args, kwargs))
                return Response()
        http = SimpleNamespace(Client=Client, Timeout=lambda **kwargs: kwargs)
        result = transport.invoke_fake('fake prompt', 'FAKE_CANARY_ACCESS', http, 'http://fixed-proxy:3128')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], (('POST', transport.URL), {'headers': {
            'Authorization': 'Bearer FAKE_CANARY_ACCESS', 'Accept': 'text/event-stream', 'Accept-Encoding': 'identity'},
            'json': {'model': transport.MODEL, 'reasoning': {'effort': 'medium'},
                     'input': [{'role': 'user', 'content': 'fake prompt'}], 'store': False, 'stream': True}}))
        self.assertEqual(options[0], {'timeout': {'connect': 10, 'read': 30, 'write': 10, 'pool': 10},
            'trust_env': False, 'follow_redirects': False, 'verify': True, 'proxy': 'http://fixed-proxy:3128'})
        for status, headers in ((401, headers), (302, headers), (200, {'content-type': 'application/json'}),
                                (200, {'content-type': 'text/event-stream', 'content-encoding': 'gzip'})):
            calls.clear()
            with self.assertRaises(ValueError) as error:
                transport.invoke_fake('fake prompt', 'FAKE_CANARY_ACCESS', http, 'http://fixed-proxy:3128')
            self.assertEqual(len(calls), 1)
            self.assertNotIn('FAKE_CANARY', str(error.exception))
        calls.clear()
        for prompt, token in (('x'*(transport.MAX_BYTES+1), 'FAKE_CANARY_ACCESS'), ('x', 'real'),
                              ('x', 'FAKE_CANARY_\r\nInjected')):
            with self.assertRaises(ValueError): transport.invoke_fake(prompt, token, http, None)
        self.assertEqual(calls, [])
        with patch.object(Path, 'open', side_effect=AssertionError('No credential reads')):
            with self.assertRaisesRegex(ValueError, 'Live dispatch disabled'): transport.dispatch(None)


if __name__ == '__main__':
    unittest.main()
