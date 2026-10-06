"""Fake HTTP and worker boundaries only; never open real credentials or Docker."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import ExitStack

import gold_proposal as proposal
import supported_oauth_transport as transport
from test_supported_oauth_transport import events, wire


def fake_http(raw=None, status=200, crash=False):
    calls = []
    class Response:
        status_code = status
        headers = {'content-type': 'text/event-stream'}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def iter_raw(self, **kwargs):
            if crash: raise OSError('PRIVATE_TOKEN_AND_PROMPT')
            yield wire(events()) if raw is None else raw
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def stream(self, *args, **kwargs):
            calls.append((args, kwargs))
            return Response()
    return SimpleNamespace(Client=Client, Timeout=lambda **kwargs: kwargs), calls


class DiagnosticTest(unittest.TestCase):
    def test_http_stream_failures_are_classified_without_sensitive_text_or_retry(self):
        changed = events(); changed[-1]['response']['model'] = 'PRIVATE_MODEL'
        usage = events(); usage[-1]['response']['usage'] = {'secret': 'PRIVATE_TOKEN'}
        provider = events()[:-1] + [{'type': 'response.failed', 'response': {'error': {
            'code': 'subscription_sharing_usage_limit_exceeded', 'message': 'PRIVATE_TOKEN'}}}]
        unknown = events()[:-1] + [{'type': 'response.failed', 'response': {'error': {
            'code': 'PRIVATE_TOKEN', 'message': 'PRIVATE_PROMPT'}}}]
        for raw, status, crash, expected in (
            (None, 401, False, {'stage': 'http', 'code': 'refused', 'http_status': 401}),
            (wire(events()[:-1]), 200, False, {'stage': 'stream', 'code': 'truncated'}),
            (wire(changed), 200, False, {'stage': 'stream', 'code': 'identity'}),
            (wire(usage), 200, False, {'stage': 'stream', 'code': 'usage'}),
            (wire(provider), 200, False, {'stage': 'stream', 'code': 'provider',
                'provider_code': 'subscription_sharing_usage_limit_exceeded'}),
            (wire(unknown), 200, False, {'stage': 'stream', 'code': 'provider', 'provider_code': 'unknown'}),
            (None, 200, True, {'stage': 'stream', 'code': 'exception'}),
        ):
            http, calls = fake_http(raw, status, crash)
            with self.subTest(expected=expected), self.assertRaises(ValueError) as error:
                transport.invoke_fake('PRIVATE_PROMPT', 'FAKE_CANARY_ACCESS', http, None)
            self.assertEqual(getattr(error.exception, 'diagnostic', None), expected)
            self.assertEqual(len(calls), 1)
            self.assertNotIn('PRIVATE', str(error.exception) + json.dumps(error.exception.diagnostic))

    def test_worker_failure_envelope_is_bounded_and_strict(self):
        self.assertTrue(hasattr(proposal, 'decode_worker_response'), 'Worker diagnostic decoder missing')
        good = {'failure': {'stage': 'http', 'code': 'refused', 'http_status': 403}}
        with self.assertRaises(ValueError) as error:
            proposal.decode_worker_response(2, json.dumps(good).encode())
        self.assertEqual(error.exception.diagnostic, good['failure'])
        for value in (
            {'failure': {'stage': 'PRIVATE_TOKEN', 'code': 'exception'}},
            {'failure': {'stage': 'http', 'code': 'refused', 'http_status': True}},
            {'failure': {'stage': 'http', 'code': 'refused', 'http_status': 999}},
            {'failure': {'stage': 'stream', 'code': 'provider', 'provider_code': 'PRIVATE_TOKEN'}},
            {'failure': {'stage': 'http', 'code': 'refused', 'body': 'PRIVATE_TOKEN'}},
            {**good, 'secret': 'PRIVATE_TOKEN'},
        ):
            with self.subTest(value=value), self.assertRaises(ValueError) as error:
                proposal.decode_worker_response(2, json.dumps(value).encode())
            self.assertEqual(error.exception.diagnostic, {'stage': 'worker', 'code': 'reply'})
        for raw in (b'bad PRIVATE_TOKEN', b'x' * (proposal.BOUND + 1)):
            with self.assertRaises(ValueError) as error: proposal.decode_worker_response(2, raw)
            self.assertEqual(error.exception.diagnostic, {'stage': 'worker', 'code': 'reply'})
        with self.assertRaises(ValueError): proposal.decode_worker_response(0, json.dumps(good).encode())

    def worker_reply(self, *, initialize=False):
        http, calls = fake_http(status=401)
        output = io.BytesIO()
        payload = {'operation': 'proposal', 'value': {'prompt': 'PRIVATE_PROMPT', 'access_token': 'FAKE_CANARY_ACCESS'}}
        def invoke(prompt, token): return transport.invoke_fake(prompt, token, http, None)
        version = lambda name: 'wrong' if initialize else proposal.POLICY[name]
        with patch.object(proposal, 'watchdog'), patch.object(proposal.os, 'environ', {}), \
                patch.object(proposal.importlib.metadata, 'version', side_effect=version), \
                patch.object(proposal, 'invoke_isolated', side_effect=invoke), \
                patch.object(proposal.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))), \
                patch.object(proposal.sys, 'stdout', SimpleNamespace(buffer=output)):
            try:
                proposal.worker()
            except SystemExit as error:
                self.assertEqual(error.code, 2)
            except Exception:
                pass  # Old worker discards the diagnostic: the assertion below must fail.
        self.assertTrue(output.getvalue(), 'Worker discarded the safe failure envelope')
        self.assertNotIn(b'PRIVATE', output.getvalue())
        self.assertEqual(len(calls), 0 if initialize else 1)
        return output.getvalue()

    def test_worker_initialization_and_http_failure_reach_stdout_safely(self):
        self.assertEqual(json.loads(self.worker_reply(initialize=True)),
                         {'failure': {'stage': 'worker', 'code': 'initialization'}})
        self.assertEqual(json.loads(self.worker_reply()),
                         {'failure': {'stage': 'http', 'code': 'refused', 'http_status': 401}})

    def test_approval_review_matches_sent_request_and_old_or_wrong_text_is_refused(self):
        self.assertTrue(hasattr(proposal, 'request_review'), 'Concrete request review missing')
        http, calls = fake_http()
        transport.invoke_fake('fixture', 'FAKE_CANARY_ACCESS', http, None)
        review = json.loads(proposal.request_review())
        request = calls[0][1]['json']
        self.assertEqual(review['request'], {k: v for k, v in request.items() if k != 'input'})
        self.assertEqual(review['request'], {'model': 'gpt-5.6-sol', 'reasoning': {'effort': 'medium'},
                                           'stream': True, 'store': False})
        self.assertEqual(review['method'], 'POST')
        self.assertEqual(review['max_posts'], 1)
        self.assertEqual(review['additional_spend_usd'], 0)
        self.assertEqual(review['retries'], 0)
        self.assertFalse(review['tools'])
        self.assertFalse(review['trade_authority'])
        self.assertEqual(review['url'], transport.URL)
        self.assertEqual(review['local_bounds'], dict(proposal_bytes=16384, stream_bytes=262144,
            event_bytes=65536, stream_seconds=120, controller_seconds=180))
        self.assertNotIn('max_output_tokens', request)
        value = dict(mode='one_real_development_proposal', seal_sha256='a'*64, intent_sha256='b'*64,
            approved_at=1000, expires_at=2000, one_proposal_authorized=True, additional_spend_usd=0,
            account_seal_sha256='c'*64, account_verification_id='d'*32, account_receipt_sha256='e'*64,
            request_review_sha256=proposal.sha(proposal.request_review().encode()))
        proposal.approval_gate(value, 'a'*64, 'b'*64, 1100)
        old = dict(value); del old['request_review_sha256']
        with self.assertRaises(ValueError): proposal.approval_gate(old, 'a'*64, 'b'*64, 1100)
        wrong = proposal.request_review().replace('"stream": true', '"stream": false')
        self.assertNotEqual(wrong, proposal.request_review())
        with self.assertRaises(ValueError):
            proposal.approval_gate({**value, 'request_review_sha256': proposal.sha(wrong.encode())}, 'a'*64, 'b'*64, 1100)

    def test_controller_keeps_diagnostic_unknown_outcome_cleanup_failure_and_replay_guard(self):
        # Mock only external/private boundaries; real run/reservation/receipt logic executes.
        for cleanup_ok in (True, False):
            with self.subTest(cleanup_ok=cleanup_ok), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                sealed = root / 'sealed-proposal-fixture'; (sealed / 'inputs').mkdir(parents=True)
                (sealed / 'inputs/real-prompt.txt').write_text('FAKE_PROMPT')
                (root / 'proposal-readiness').mkdir(); (root / 'production-attempts').mkdir()
                auth = root / 'gold-plan-auth'; auth.mkdir(); (auth / 'registration.lock').write_bytes(b'0')
                attempt = root / 'production-attempts' / ('e'*64)
                calls = []; posts = []
                nets = {'inner': 'kwg-proposal-'+'f'*32+'-inner', 'outer': 'kwg-proposal-'+'f'*32+'-outer'}
                connected = False
                class Guard:
                    def __init__(self, *args, **kwargs):
                        (attempt / 'guard-ready.json').write_text('{}')
                    def poll(self):
                        if (attempt / 'finished.json').exists():
                            cleanup = attempt / 'cleanup.json'
                            if not cleanup.exists(): cleanup.write_text(json.dumps({'cleanup_verified': cleanup_ok}))
                            return 0
                        return None
                def command(argv, **kwargs):
                    nonlocal connected
                    args = argv[5:]; calls.append(args)
                    value = {}
                    if args[:2] == ['network', 'connect']: connected = True
                    if args[:2] == ['network', 'inspect']:
                        value = [{'Internal': args[2] == nets['inner'], 'EnableIPv6': True, 'Driver': 'bridge',
                            'Options': {'com.docker.network.bridge.gateway_mode_'+v: 'isolated' for v in ('ipv4','ipv6')}}]
                    if args[0] == 'inspect':
                        networks = nets.values() if args[1].endswith('-proxy') and connected else [nets['inner']]
                        value = [{'HostConfig': {'LogConfig': {'Type': 'none'}, 'CapAdd': None,
                            'RestartPolicy': {'Name': 'no'}}, 'NetworkSettings': {'Networks': dict.fromkeys(networks, {})}}]
                    if args[:3] == ['start', '-a', '-i']:
                        self.assertTrue(args[3].endswith('-request'))
                        posts.append(1)
                        return SimpleNamespace(returncode=2, stdout=self.worker_reply(), stderr=b'PRIVATE_STDERR')
                    return SimpleNamespace(returncode=0, stdout=json.dumps(value).encode(), stderr=b'')
                with ExitStack() as stack:
                    for name, replacement in (
                        ('location', lambda _: sealed), ('private_acl', lambda _: None),
                        ('verify_inputs', lambda *a: ({'experiment_sha256': 'e'*64}, 'b'*64)),
                        ('dispatch_prerequisites', lambda *a: ('c'*64, {})),
                        ('accepted_account', lambda *a: 'FAKE_CANARY_ACCESS'),
                        ('read_private', lambda *a: b'{}'), ('billing_gate', lambda *a: None),
                        ('inspect_container', lambda *a: None),
                    ): stack.enter_context(patch.object(proposal, name, replacement))
                    stack.enter_context(patch.object(proposal.uuid, 'uuid4', return_value=SimpleNamespace(hex='f'*32)))
                    stack.enter_context(patch.object(proposal.subprocess, 'Popen', Guard))
                    stack.enter_context(patch.object(proposal.subprocess, 'run', side_effect=command))
                    result = proposal.run('a'*64, 'dispatch')
                    self.assertEqual(result.get('failure'), {'stage': 'http', 'code': 'refused', 'http_status': 401})
                    self.assertEqual(result['model_requests'], 'outcome_unknown')
                    self.assertEqual(result['dispatch_status'], 'consumed_outcome_unknown')
                    self.assertFalse(result['passed']); self.assertEqual(result['cleanup_verified'], cleanup_ok)
                    self.assertEqual(len(posts), 1)
                    if not cleanup_ok:
                        self.assertEqual(result['cleanup_failure'], {'stage': 'cleanup', 'code': 'unverified'})
                    self.assertNotIn('PRIVATE', json.dumps(result))
                    self.assertFalse((attempt/'proposal.json').exists())
                    self.assertFalse((attempt/'usage.json').exists())
                    saved = {p.name: p.read_bytes() for p in attempt.iterdir() if p.is_file()}
                    before = len(calls)
                    with self.assertRaises(FileExistsError): proposal.run('a'*64, 'dispatch')
                    self.assertEqual(len(calls), before)
                    self.assertEqual(saved, {p.name: p.read_bytes() for p in attempt.iterdir() if p.is_file()})


if __name__ == '__main__': unittest.main()
