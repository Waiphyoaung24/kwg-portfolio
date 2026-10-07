import copy
from contextlib import ExitStack
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gold_proposal as proposal
import supported_oauth_transport as transport
from test_supported_oauth_transport import events, wire


class ProposalTest(unittest.TestCase):
    def test_worker_failure_envelope_is_strict(self):
        self.assertTrue(callable(getattr(proposal, 'worker_entry', None)), 'Worker boundary is missing')
        success = transport.parse_stream([wire(events())])
        for payload, failure, expected in (
                ({'prompt': 'synthetic', 'access_token': 'FAKE_CANARY_ACCESS'}, None, success),
                ({'secret': 'FAKE_CANARY_SECRET'}, None, {'diagnostic': {'stage': 'worker_initialization'}}),
                ({'prompt': 'synthetic', 'access_token': 'FAKE_CANARY_ACCESS'},
                 transport.DiagnosticFailure({'stage': 'http_response', 'http_status': 401}),
                 {'diagnostic': {'stage': 'http_response', 'http_status': 401}}),
                ({'prompt': 'synthetic', 'access_token': 'FAKE_CANARY_ACCESS'}, RuntimeError('FAKE_CANARY_SECRET'),
                 {'diagnostic': {'stage': 'worker_initialization'}})):
            output = io.BytesIO()
            with patch.object(proposal.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(
                    {'operation': 'proposal', 'value': payload}).encode()))), \
                    patch.object(proposal.sys, 'stdout', SimpleNamespace(buffer=output)), \
                    patch.object(proposal, 'watchdog'), patch.object(proposal.os.environ, 'clear'), \
                    patch.object(proposal.importlib.metadata, 'version', side_effect=lambda name: proposal.POLICY[name]), \
                    patch.object(proposal, 'invoke_isolated', return_value=success, side_effect=failure):
                if 'diagnostic' in expected:
                    with self.assertRaises(SystemExit) as caught: proposal.worker_entry()
                    self.assertEqual(caught.exception.code, 2)
                    self.assertLessEqual(len(output.getvalue()), 256)
                else: proposal.worker_entry()
            self.assertEqual(json.loads(output.getvalue()), expected)
            self.assertNotIn('FAKE_CANARY', output.getvalue().decode())

    def test_worker_exchange_rejects_untrusted_diagnostics(self):
        self.assertTrue(callable(getattr(proposal, 'decode_worker_result', None)), 'Strict decoder is missing')
        success = transport.parse_stream([wire(events())])
        self.assertEqual(proposal.decode_worker_result('proposal', 0, json.dumps(success).encode()), success)
        self.assertEqual(proposal.decode_worker_result('probes', 0, b'{"public_tls_verified":true}'),
                         {'public_tls_verified': True})
        for stage in ('worker_initialization', 'http_request', 'http_response', 'response_stream'):
            record = {'stage': stage}
            if stage in ('http_response', 'response_stream'): record['http_status'] = 200
            with self.assertRaises(transport.DiagnosticFailure) as caught:
                proposal.decode_worker_result('proposal', 2, json.dumps({'diagnostic': record}).encode())
            self.assertEqual(caught.exception.diagnostic, record)
        invalid = [(2, b''), (2, b'FAKE_CANARY_STDERR'), (0, b'[]'), (0, b'{}'), (0, b'null'),
                   (0, b'3'), (0, b'"FAKE_CANARY_SECRET"'), (0, b'{' + b' ' * proposal.BOUND + b'}'),
                   (0, b'{"diagnostic":{"stage":"http_request"}}'), (3, json.dumps(success).encode()),
                   (3, b'{"diagnostic":{"stage":"http_request"}}'),
                   (2, b'{"diagnostic":{"stage":"http_request"},"secret":"FAKE_CANARY"}'),
                   (2, b'{"diagnostic":' + b' ' * 257 + b'{"stage":"http_request"}}'),
                   (2, b'{"diagnostic":{"stage":"http_request","stage":"response_stream"}}')]
        for diagnostic in ({'stage': 'FAKE_CANARY_SECRET'}, {'stage': 'proposal_parse'},
                {'stage': 'http_response', 'http_status': True}, {'stage': 'http_response', 'http_status': 600},
                {'stage': 'http_request', 'http_status': 200}, {'stage': 'http_request', 'secret': 'FAKE_CANARY'}):
            invalid.append((2, json.dumps({'diagnostic': diagnostic}).encode()))
        for change in ({'text': ['secret']}, {'text': 'x' * (transport.MAX_BYTES + 1)},
                {'model': 'wrong'}, {'reasoning_effort': 'high'}, {'promotion_status': 'ready'},
                {'secret': 'FAKE_CANARY'}, {'usage': {}},
                {'usage': {'input_tokens': True, 'output_tokens': 2, 'total_tokens': 3}},
                {'usage': {'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 4}},
                {'usage': {'input_tokens': 1, 'output_tokens': 2, 'total_tokens': 3,
                           'output_tokens_details': {'reasoning_tokens': 3}}}):
            invalid.append((0, json.dumps({**success, **change}).encode()))
        for code, raw in invalid:
            with self.subTest(code=code, size=len(raw)), self.assertRaises(transport.DiagnosticFailure) as caught:
                proposal.decode_worker_result('proposal', code, raw)
            self.assertEqual(caught.exception.diagnostic, {'stage': 'worker_exchange'})
            self.assertNotIn('FAKE_CANARY', str(caught.exception))
        for raw in (b'{}', b'{"check":false}', b'{"check":1}', b'{"":true}', b'{"diagnostic":true}',
                    b'{"diagnostic":{"stage":"http_response","http_status":401}}'):
            with self.assertRaises(transport.DiagnosticFailure) as caught:
                proposal.decode_worker_result('probes', 2 if b'"stage"' in raw else 0, raw)
            self.assertEqual(caught.exception.diagnostic, {'stage': 'worker_exchange'})

    def test_controller_diagnostics_preserve_outcome_and_cleanup(self):
        # Removing propagation/count validation or allowing negative cleanup to pass breaks this flow.
        cases = [('http', 'http_response', 'outcome_unknown'),
                 ('stream', 'response_stream', 'outcome_unknown'),
                 ('worker_create', 'worker_exchange', 'outcome_unknown'),
                 ('crash', 'worker_exchange', 'outcome_unknown'),
                 ('forgery', 'worker_exchange', 'outcome_unknown'),
                 ('invalid_success', 'worker_exchange', 'outcome_unknown'),
                 ('parser', 'proposal_parse', 1), ('artifact', 'artifact_write', 1),
                 ('configuration', 'controller_pre_dispatch', 0),
                 ('cleanup_negative', None, 1), ('cleanup_missing', None, 1),
                 ('cleanup_malformed', None, 1), ('success', None, 1),
                 ('setup_write', 'controller_pre_dispatch', 0),
                 ('guard_creation', 'controller_pre_dispatch', 0),
                 ('cleanup_scalar', None, 1), ('cleanup_claim', None, 1),
                 ('finished_write', None, 1)]
        for case, stage, count in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
                root = Path(folder); sealed = root/'sealed-proposal-fixture'
                (sealed/'inputs').mkdir(parents=True)
                (sealed/'inputs/real-prompt.txt').write_text('synthetic prompt')
                (root/'production-attempts').mkdir(); (root/'proposal-readiness').mkdir()
                (root/'gold-plan-auth').mkdir(); (root/'gold-plan-auth/registration.lock').write_bytes(b'0')
                attempt = root/'production-attempts'/('e'*64)
                intent = {'experiment_sha256': 'e'*64}
                containers, networks, operations, posts = {}, {}, [], []
                success = transport.parse_stream([wire(events())])
                def fake_guard(args, **kwargs):
                    self.assertIn('--guard', args)
                    if case == 'guard_creation': raise OSError('FAKE_CANARY_GUARD')
                    (attempt/'guard-ready.json').write_text('{}')
                    if case == 'cleanup_malformed': (attempt/'cleanup.json').write_bytes(b'FAKE_CANARY_CLEANUP')
                    elif case == 'cleanup_scalar': (attempt/'cleanup.json').write_text('null')
                    elif case == 'cleanup_claim':
                        (attempt/'cleanup.json').write_text(json.dumps({'cleanup_verified': True,
                            'failure_kind': 'FAKE_CANARY', 'failed_phase': 'FAKE_CANARY'}))
                    elif case != 'cleanup_missing':
                        cleanup = {'cleanup_verified': case != 'cleanup_negative'}
                        if case == 'cleanup_negative': cleanup.update(failure_kind='OSError', failed_phase='cleanup')
                        (attempt/'cleanup.json').write_text(json.dumps(cleanup))
                    return SimpleNamespace(poll=lambda: 0)
                class Response:
                    status_code = 401 if case == 'http' else 200
                    headers = {'content-type': 'text/event-stream', 'secret': 'FAKE_CANARY_HEADER'}
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def iter_raw(self, **kwargs):
                        yield wire(events())[:-1] if case == 'stream' else wire(events())
                class Client:
                    def __init__(self, **kwargs): pass
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def stream(self, *args, **kwargs):
                        posts.append((args, kwargs))
                        return Response()
                http = SimpleNamespace(Client=Client, Timeout=lambda **kwargs: kwargs)
                def fake_invoke(prompt, token):
                    return transport.invoke_fake(prompt, token, http, None)
                def fake_command(args, **kwargs):
                    self.assertEqual(args[:2], [str(proposal.DOCKER), '--config'])
                    cmd = args[5:]; output = b''; code = 0
                    if cmd[:2] == ['network', 'create']:
                        networks['inner' if '--internal' in cmd else 'outer'] = cmd[-1]
                    elif cmd[:2] == ['network', 'inspect']:
                        inner = cmd[-1] == networks['inner']
                        state = {'Internal': inner, 'EnableIPv6': True, 'Driver': 'bridge',
                                 'Options': {'com.docker.network.bridge.gateway_mode_'+v: 'isolated'
                                             for v in ('ipv4', 'ipv6')}}
                        if case == 'configuration' and not inner: state['Internal'] = True
                        output = json.dumps([state]).encode()
                    elif cmd[0] == 'create':
                        role = cmd[cmd.index('--name')+1].rsplit('-', 1)[-1]
                        if case == 'worker_create' and role == 'request': raise OSError('FAKE_CANARY_CREATE')
                        containers[role] = cmd
                    elif cmd[0] == 'inspect':
                        role = cmd[-1].rsplit('-', 1)[-1]
                        state = {'HostConfig': {'LogConfig': {'Type': 'none'}, 'RestartPolicy': {'Name': 'no'}},
                                 'NetworkSettings': {'Networks': {net: {} for net in
                                     (networks.values() if role == 'proxy' else [networks['inner']])}}}
                        output = json.dumps([state]).encode()
                    elif cmd[0] == 'start' and '-i' in cmd:
                        role = cmd[-1].rsplit('-', 1)[-1]
                        if role == 'parser':
                            if case == 'parser': raise proposal.subprocess.CalledProcessError(2, args, stderr=b'FAKE_CANARY')
                            output = b'{"kind":"ema20_slope_filter","lookback_bars":3,"hypothesis":"synthetic"}'
                        else:
                            self.assertEqual(role, 'request')
                            payload = json.loads(kwargs['input']); operations.append(payload['operation'])
                            self.assertEqual(payload['operation'], 'proposal')
                            if case == 'crash': code = 3
                            elif case == 'forgery': output = b'{"diagnostic":{"stage":"artifact_write"}}'; code = 2
                            elif case == 'invalid_success': output = b'{}'
                            else:
                                buffer = io.BytesIO()
                                with patch.object(proposal.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(kwargs['input']))), \
                                        patch.object(proposal.sys, 'stdout', SimpleNamespace(buffer=buffer)):
                                    try: proposal.worker_entry()
                                    except SystemExit as error: code = error.code
                                output = buffer.getvalue()
                    elif cmd[:2] != ['network', 'connect'] and cmd[0] != 'start':
                        raise AssertionError('Unexpected fake Docker operation')
                    return SimpleNamespace(stdout=output, stderr=b'FAKE_CANARY_PROCESS_STDERR', returncode=code)
                original_write = proposal.write_once
                def fake_write(path, value):
                    if case == 'artifact' and path.name == 'usage.json': raise OSError('FAKE_CANARY_ARTIFACT')
                    if case == 'finished_write' and path.name == 'finished.json': raise OSError('FAKE_CANARY_FINISHED')
                    return original_write(path, value)
                original_text = Path.write_text
                def fake_text(path, value, *args, **kwargs):
                    if case == 'setup_write' and path.name == 'squid.conf': raise OSError('FAKE_CANARY_SETUP')
                    return original_text(path, value, *args, **kwargs)
                import msvcrt, socket
                for target, name, options in (
                        (proposal, 'location', {'return_value': sealed}),
                        (proposal, 'verify_inputs', {'return_value': (intent, 'b'*64)}),
                        (proposal, 'dispatch_prerequisites', {'return_value': ('c'*64, {})}),
                        (proposal, 'private_acl', {}), (proposal, 'inspect_container', {}),
                        (proposal, 'read_private', {'return_value': b'{}'}),
                        (proposal, 'accepted_account', {'return_value': 'FAKE_CANARY_ACCESS'}),
                        (proposal, 'billing_gate', {}), (proposal, 'watchdog', {}),
                        (proposal, 'invoke_isolated', {'side_effect': fake_invoke}),
                        (proposal, 'write_once', {'side_effect': fake_write}),
                        (proposal.os.environ, 'clear', {}),
                        (proposal.importlib.metadata, 'version', {'side_effect': lambda name: proposal.POLICY[name]}),
                        (proposal.subprocess, 'run', {'side_effect': fake_command}),
                        (proposal.subprocess, 'Popen', {'side_effect': fake_guard}),
                        (proposal.time, 'time', {'return_value': 1000}),
                        (proposal.time, 'monotonic', {'return_value': 100}),
                        (proposal.time, 'sleep', {'side_effect': AssertionError('Unexpected wait')}),
                        (msvcrt, 'locking', {}), (Path, 'write_text', {'new': fake_text}),
                        (socket, 'socket', {'side_effect': AssertionError('No sockets')}),
                        (socket, 'create_connection', {'side_effect': AssertionError('No connections')})):
                    stack.enter_context(patch.object(target, name, **options))
                receipt = proposal.run('a'*64, 'dispatch')
                self.assertEqual(json.loads((attempt/'receipt.json').read_bytes()), receipt)
                self.assertEqual(receipt['model_requests'], count)
                self.assertEqual(receipt['promotion_status'], 'blocked')
                self.assertEqual(receipt['passed'], case == 'success')
                cleanup_failed = case in ('cleanup_negative', 'cleanup_missing', 'cleanup_malformed',
                    'cleanup_scalar', 'cleanup_claim', 'setup_write', 'guard_creation', 'finished_write')
                self.assertEqual(receipt['cleanup_verified'], not cleanup_failed)
                if stage:
                    expected = {'stage': stage}
                    if case in ('http', 'stream'): expected['http_status'] = 401 if case == 'http' else 200
                    self.assertEqual(receipt.get('failure_diagnostic'), expected)
                    self.assertEqual(receipt['dispatch_status'], 'consumed_outcome_unknown')
                else: self.assertNotIn('failure_diagnostic', receipt)
                if case == 'cleanup_negative':
                    self.assertEqual(receipt['cleanup_failure_kind'], 'OSError')
                    self.assertEqual(receipt['cleanup_failed_phase'], 'cleanup')
                self.assertNotIn('FAKE_CANARY', json.dumps(receipt))
                if cleanup_failed:
                    self.assertFalse(receipt['passed'])
                if case in ('setup_write', 'guard_creation'):
                    self.assertEqual(operations, []); self.assertEqual(posts, [])
                    self.assertEqual(containers, {}); self.assertEqual(networks, {})
                self.assertTrue((attempt/'started.json').exists())
                self.assertLessEqual(len(operations), 1); self.assertLessEqual(len(posts), 1)
                if case in ('artifact', 'cleanup_negative', 'cleanup_missing', 'cleanup_malformed', 'success'):
                    self.assertTrue((attempt/'proposal.json').exists())
                before = {p.name: p.read_bytes() for p in attempt.iterdir() if p.is_file()}
                with self.assertRaises(FileExistsError): proposal.run('a'*64, 'dispatch')
                self.assertEqual({p.name: p.read_bytes() for p in attempt.iterdir() if p.is_file()}, before)

    def test_concrete_approval_expires_and_cannot_authorize_credit_use(self):
        value=dict(mode='one_real_development_proposal',seal_sha256='a'*64,intent_sha256='b'*64,
            approved_at=1000,expires_at=2000,one_proposal_authorized=True,
            additional_spend_usd=0,account_seal_sha256='c'*64,
            account_verification_id='d'*32,account_receipt_sha256='e'*64)
        proposal.approval_gate(value,'a'*64,'b'*64,1100)
        for update in ({'additional_spend_usd':1},{'additional_spend_usd':False},
                {'one_proposal_authorized':1},{'expires_at':1100},{'expires_at':3000},
                {'approved_at':1200},{'approved_at':False},{'seal_sha256':'other'},
                {'intent_sha256':'other'},{'account_seal_sha256':'z'*64},{'extra':True},
                {'account_verification_id':'../bad'},{'account_receipt_sha256':'z'*64}):
            with self.subTest(update=update),self.assertRaises(ValueError):
                proposal.approval_gate({**value,**update},'a'*64,'b'*64,1100)
        with self.assertRaises(ValueError): proposal.approval_gate(value,'a'*64,'b'*64,3001)

    def test_forced_termination_records_bad_cleanup_without_passing(self):
        for cleanup in (b'FAKE_CANARY', b'null', b'{"cleanup_verified":false}',
                        b'{"cleanup_verified":true,"guard_independent":true,"resources_absent":true}'):
            with self.subTest(cleanup=cleanup), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);sealed=root/'sealed-proposal-fixture';sealed.mkdir()
                (root/'proposal-readiness').mkdir()
                attempt=root/'proposal-readiness'/('a'*64+'.termination')
                def launch(*args, **kwargs):
                    attempt.mkdir()
                    proposal.write_once(attempt/'kill-ready.json',dict(synthetic_input_transferred=True,
                        public_tls_verified=True,passed=False,model_requests=0,promotion_status='blocked'))
                    (attempt/'cleanup.json').write_bytes(cleanup)
                    return process
                process=SimpleNamespace(returncode=-1,poll=lambda: -1,
                    terminate=lambda: None,wait=lambda **kwargs: None)
                with patch.object(proposal,'location',return_value=sealed), \
                        patch.object(proposal.subprocess,'Popen',side_effect=launch), \
                        patch.object(proposal.subprocess,'run',side_effect=AssertionError('No commands')), \
                        patch.object(proposal.time,'sleep',side_effect=AssertionError('No wait')):
                    result=proposal.termination_check('a'*64)
                    self.assertEqual(result['passed'], b'true' in cleanup)
                    self.assertEqual(json.loads((attempt/'receipt.json').read_bytes()),result)
                    self.assertNotIn('FAKE_CANARY',json.dumps(result))
                    before=(attempt/'receipt.json').read_bytes()
                    with self.assertRaises(FileExistsError): proposal.termination_check('a'*64)
                    self.assertEqual((attempt/'receipt.json').read_bytes(),before)

    def test_fresh_billing_requires_exact_saved_provider_controls_and_binding(self):
        intent=dict(client_id_sha256='client',subject_sha256='subject')
        value=dict(saved_at=datetime.fromtimestamp(1000,timezone.utc).isoformat(),
            billing_ceiling_verified=True,**intent,observations=dict(app_name='KWG Gold Research',
                gold_app_entries=1,app_plan_usage_allowed=True,manage_usage_followed_from_gold_connection=True,
                apps_credit_use_allowed=False,automatic_reload_enabled=False,save_button_enabled=False))
        proposal.billing_gate(value,intent,1100)
        for field,changed in (('apps_credit_use_allowed',True),('automatic_reload_enabled',True),
                ('save_button_enabled',True),('app_plan_usage_allowed',False),('gold_app_entries',2),
                ('manage_usage_followed_from_gold_connection',False),('app_name','Other')):
            wrong=copy.deepcopy(value);wrong['observations'][field]=changed
            with self.assertRaises(ValueError): proposal.billing_gate(wrong,intent,1100)
        for update in ({'client_id_sha256':'other'},{'subject_sha256':'other'},{'billing_ceiling_verified':False}):
            with self.assertRaises(ValueError): proposal.billing_gate({**value,**update},intent,1100)
        with self.assertRaises(ValueError): proposal.billing_gate(value,intent,1301)

    def test_missing_approval_stops_before_auth_network_or_production_reservation(self):
        root=Path('FAKE_ROOT');sealed=root/'sealed-proposal-fixture'
        with patch.object(proposal,'read_private',side_effect=FileNotFoundError) as read, \
                patch.object(proposal,'verify_seal') as seal,patch.object(proposal,'reserve_production') as reserve, \
                patch.object(proposal.subprocess,'run') as command:
            with self.assertRaises(FileNotFoundError): proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64)
            self.assertEqual(read.call_args.args[0],root/'proposal-readiness'/('a'*64+'.approval.json'))
            self.assertEqual(read.call_count,1);seal.assert_not_called();reserve.assert_not_called();command.assert_not_called()

    def test_account_receipt_binds_exact_signed_accepted_registration_and_model(self):
        record=dict(issuer='https://auth.openai.com',client_id='oaiapp_fixture',subject='fixture',
            ext_agent_host_id='host',access_token='FAKE_CANARY_ACCESS',expires_at=5000,dispatch_status='blocked')
        raw=json.dumps(record).encode()
        intent={key:proposal.sha(record[field].encode()) for field,key in (
            ('client_id','client_id_sha256'),('subject','subject_sha256'),('ext_agent_host_id','host_id_sha256'))}
        receipt=dict(seal_sha256='c'*64,passed=True,cleanup_verified=True,required_model_present=True,
            server_account_verified=True,production_isolation_verified=True,registration_sha256=proposal.sha(raw),
            accepted_at=1000,available_models=[proposal.MODEL],model_requests=0,**intent)
        self.assertEqual(proposal.accepted_account(raw,receipt,intent,'c'*64,1100),'FAKE_CANARY_ACCESS')
        for update in ({'registration_sha256':'other'},{'accepted_at':0},{'accepted_at':True},
                {'available_models':['other']},{'cleanup_verified':False},{'subject_sha256':'other'},
                {'server_account_verified':False},{'seal_sha256':'other'},{'model_requests':1}):
            with self.assertRaises(ValueError): proposal.accepted_account(raw,{**receipt,**update},intent,'c'*64,1100)
        stale=json.dumps({**record,'expires_at':1300}).encode()
        with self.assertRaises(ValueError): proposal.accepted_account(stale,{**receipt,'registration_sha256':proposal.sha(stale)},intent,'c'*64,1100)

    def test_dispatch_uses_only_the_approved_verification_id_and_exact_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sealed=root/'sealed-proposal-fixture';sealed.mkdir()
            account_sealed=root/'sealed-account-fixture';account_sealed.mkdir()
            (sealed/'code').mkdir();(account_sealed/'code').mkdir()
            for name in proposal.ACCOUNT_FILES:
                (sealed/'code'/name).write_bytes(b'fake')
                (account_sealed/'code'/name).write_bytes(b'fake')
            from gold_account import POLICY
            (account_sealed/'readiness.json').write_text(json.dumps(dict(policy=POLICY)))
            now=proposal.time.time()
            receipt=dict(verification_id='d'*32,seal_sha256='c'*64)
            raw=json.dumps(receipt).encode()
            approval=dict(mode='one_real_development_proposal',seal_sha256='a'*64,intent_sha256='b'*64,
                approved_at=int(now),expires_at=int(now)+300,one_proposal_authorized=True,
                additional_spend_usd=0,account_seal_sha256='c'*64,account_verification_id='d'*32,
                account_receipt_sha256=proposal.sha(raw))
            seen=[]
            def read(path):
                seen.append(path)
                if path.name.endswith('.approval.json'): return json.dumps(approval).encode()
                if path.name.endswith('.coding-denial.json'):
                    return json.dumps(dict(seal_sha256='a'*64,actual_coding_token=True,checked_at=int(now),
                        registration_open_denied=True,canary_open_denied=True,credential_contents_read=False)).encode()
                if path.parent.parent==root/'account-readiness': return raw
                return json.dumps(dict(passed=True,cleanup_verified=True,model_requests=0,seal_sha256='a'*64)).encode()
            with patch.object(proposal,'read_private',side_effect=read),patch.object(proposal,'verify_seal'), \
                    patch.object(proposal,'billing_gate'),patch.object(proposal.subprocess,'run') as command:
                self.assertEqual(proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64),('c'*64,receipt))
                self.assertEqual(seen[-1],root/'account-readiness'/('c'*64+'.accept-'+'d'*32)/'receipt.json')
                approval['account_receipt_sha256']='e'*64
                with self.assertRaises(ValueError): proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64)
                approval['account_receipt_sha256']=proposal.sha(raw);approval['account_verification_id']='f'*32
                with self.assertRaises(ValueError): proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64)
                command.assert_not_called()

    def test_experiment_reservation_is_exclusive_across_seals_and_survives_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            attempt=proposal.reserve_production(root,'e'*64,'a'*64,'b'*64)
            self.assertEqual(json.loads((attempt/'started.json').read_bytes())['state'],'outcome_unknown')
            with self.assertRaises(FileExistsError): proposal.reserve_production(root,'e'*64,'c'*64,'d'*64)
            self.assertEqual(len(list(root.iterdir())),1)
            for identity in ('../escape','e'*63,'z'*64):
                with self.assertRaises(ValueError): proposal.reserve_production(root,identity,'a'*64,'b'*64)
            original=proposal.write_once
            def fail_started(path,value):
                if path.name=='started.json': raise OSError('FAKE_CANARY_START')
                return original(path,value)
            with patch.object(proposal,'write_once',side_effect=fail_started):
                with self.assertRaises(OSError): proposal.reserve_production(root,'f'*64,'a'*64,'b'*64)
            failed=json.loads((root/('f'*64)/'receipt.json').read_bytes())
            self.assertFalse(failed['passed']);self.assertEqual(failed['model_requests'],0)
            self.assertNotIn('FAKE_CANARY',json.dumps(failed))
            with self.assertRaises(FileExistsError): proposal.reserve_production(root,'f'*64,'c'*64,'d'*64)

    def test_live_entry_refuses_host_and_legacy_public_dispatch_stays_closed(self):
        with self.assertRaises(ValueError): transport.invoke_isolated('prompt','FAKE_CANARY_ACCESS')
        with self.assertRaises(ValueError): transport.dispatch('prompt','FAKE_CANARY_ACCESS')
        self.assertEqual(proposal.POLICY['max_posts'],1)
        self.assertEqual(proposal.POLICY['retries'],0)
        self.assertIn('acl approved dstdomain -n api.openai.com\n',proposal.PROXY)
        self.assertNotIn('auth.openai.com',proposal.PROXY)
        self.assertFalse(proposal.POLICY['tools']);self.assertFalse(proposal.POLICY['trade_authority'])


if __name__=='__main__': unittest.main()
