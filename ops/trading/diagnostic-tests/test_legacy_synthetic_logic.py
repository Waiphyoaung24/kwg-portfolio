"""Synthetic legacy equivalents; no provider authenticity or process-isolation proof.

Provider preparation and child execution are dependency fakes. Hash constants,
identity verifiers, runtime source and the checker's audit guard are never patched.
"""
import copy
from contextlib import chdir
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import batch3_runner as runner
import supported_gateway as supported
import supported_oauth_transport as transport
import trusted_gateway as trusted
import trusted_oauth_transport as legacy_transport
from test_batch3_rehearsal import GOOD, rehearse
from test_proposal_diagnostics import fake_http
from test_research_gold import packet_fixture

FAKE_SOURCE = b'SYNTHETIC_DEPENDENCY_BYTES_NOT_A_PINNED_PROVIDER'


def child_reply(*, audit=None, response=None):
    value = dict(response=GOOD['response'] if response is None else response,
        usage=dict(GOOD['usage']), fake_requests=1, model_requests=0, isolation_probe_passed=False)
    if audit is not None: value['auth_audit'] = audit
    return subprocess.CompletedProcess(['FAKE_CHILD'], 0, json.dumps(value).encode(), b'')


class LegacyLogicTest(unittest.TestCase):
    def dependencies(self, reply):
        supplier = SimpleNamespace(prepare_source=Mock(return_value=FAKE_SOURCE))
        return supplier, patch.object(runner, 'provider_fixture_module', return_value=supplier), \
            patch.object(runner.subprocess, 'run', return_value=reply)

    def test_audit_guard_blocks_real_network_child_and_private_open(self):
        with self.assertRaisesRegex(RuntimeError, 'Live IO forbidden'):
            socket.getaddrinfo('synthetic.invalid', 443)
        with socket.socket() as connection:
            with self.assertRaisesRegex(RuntimeError, 'Live IO forbidden'):
                connection.connect(('192.0.2.1', 443))
            with self.assertRaisesRegex(RuntimeError, 'Live IO forbidden'):
                connection.bind(('127.0.0.1', 0))
        with self.assertRaisesRegex(RuntimeError, 'Live IO forbidden'):
            runner.os.system('echo MUST_NOT_EXECUTE')
        with self.assertRaisesRegex(RuntimeError, 'Live IO forbidden'):
            subprocess.Popen([sys.executable, '-c', 'raise SystemExit(99)'])
        private = Path(runner.__file__).resolve().parents[2]/'.batch3-vibe/DO_NOT_READ'
        with self.assertRaisesRegex(RuntimeError, 'Private runtime forbidden'):
            private.read_bytes()

    def test_real_provider_identity_guards_refuse_synthetic_source_before_execution(self):
        self.assertEqual(legacy_transport.PROVIDER_SHA,
            '64e257725e04ff0b1d8e7a56061d67aa190113d60340850b45bc821de74e867e')
        http, calls = fake_http()
        with self.assertRaisesRegex(ValueError, 'Trusted provider identity mismatch'):
            legacy_transport.invoke_bound(FAKE_SOURCE, 'FAKE_PROMPT', None, 'a'*64, http)
        self.assertEqual(calls, [])
        with tempfile.TemporaryDirectory(prefix='FAKE-legacy-identity-') as folder:
            root = Path(folder); (root/'code').mkdir(); (root/'inputs').mkdir()
            (root/'inputs/provider.py').write_bytes(FAKE_SOURCE)
            raw = json.dumps([dict(path='inputs/provider.py', sha256=runner.hashlib.sha256(FAKE_SOURCE).hexdigest())]).encode()
            (root/'manifest.json').write_bytes(raw)
            manifest_sha = runner.hashlib.sha256(raw).hexdigest()
            with patch.object(trusted, '__file__', str(root/'code/trusted_gateway.py')), \
                    patch.object(trusted.subprocess, 'run') as command:
                with self.assertRaisesRegex(ValueError, 'Pinned provider mismatch'):
                    trusted.rehearse(root/'FAKE-registry', packet_fixture(), manifest_sha, 'success')
                command.assert_not_called()
                self.assertFalse((root/'FAKE-registry').exists())
            supplier = runner.provider_fixture_module()
            with self.assertRaises(FileNotFoundError):
                supplier.prepare_source(root/'MISSING_PUBLIC_PROVIDER.py', Path(runner.__file__).with_name('vibe-codex-one-request.patch'))
            with self.assertRaisesRegex(ValueError, 'Pinned provider source mismatch'):
                supplier.prepare_source(root/'inputs/provider.py', Path(runner.__file__).with_name('vibe-codex-one-request.patch'))

    def test_supported_fake_http_single_post_401_no_retry_and_no_secret_receipt(self):
        for status in (200, 401, 302, 429, 500):
            http, calls = fake_http(status=status)
            with self.subTest(status=status):
                if status == 200:
                    value = transport.invoke_fake('FAKE_PROMPT', 'FAKE_CANARY_ACCESS', http, None)
                    self.assertEqual(value['model'], transport.MODEL)
                    self.assertEqual(value['promotion_status'], 'blocked')
                    self.assertNotIn('CANARY', json.dumps(value))
                else:
                    with self.assertRaises(ValueError) as error:
                        transport.invoke_fake('FAKE_PROMPT', 'FAKE_CANARY_ACCESS', http, None)
                    self.assertNotIn('CANARY', str(error.exception))
                self.assertEqual(len(calls), 1)

    def test_supported_inspector_refuses_unsafe_configuration_without_start(self):
        mount = dict(Source='C:/FAKE/fixture.py', Destination='/snapshot/code/fixture.py', Type='bind', RW=False)
        host = dict(NetworkMode='FAKE-isolated', ReadonlyRootfs=True, Privileged=False, CapDrop=['ALL'],
            SecurityOpt=['no-new-privileges'], PidsLimit=32, Memory=134217728, NanoCpus=1000000000,
            ExtraHosts=[], Dns=['127.0.0.1'], PortBindings={},
            Mounts=[dict(Source=mount['Source'], Target=mount['Destination'], Type='bind', ReadOnly=True)])
        state = dict(Image=supported.SANDBOX_IMAGE, Config=dict(User='65534:65534',
            Entrypoint=[supported.PYTHON], Cmd=['-I', '-B']), HostConfig=host, Mounts=[mount])
        args = (supported.SANDBOX_IMAGE, 'FAKE-isolated', supported.PYTHON, ['-I', '-B'],
            [(Path(mount['Source']), mount['Destination'])], {'dns': ['127.0.0.1']})
        supported.inspect_container(state, *args)
        with patch.object(supported.subprocess, 'run') as run:
            for key, value in (('NetworkMode', 'bridge'), ('Privileged', True), ('ReadonlyRootfs', False),
                               ('Dns', ['8.8.8.8']), ('PidsLimit', 0)):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    supported.inspect_container({**state, 'HostConfig': {**host, key: value}}, *args)
            with self.assertRaises(ValueError):
                supported.inspect_container({**state, 'Mounts': [{**mount, 'RW': True}]}, *args)
            run.assert_not_called()

    def test_auth_fixture_and_audit_receipt_logic_without_refresh_or_provider(self):
        supplier, source, child = self.dependencies(child_reply(audit=dict(refreshes=1, clears=0, inference_posts=1)))
        with tempfile.TemporaryDirectory(prefix='FAKE-auth-protocol-') as folder, source, child as execute:
            root = Path(folder)
            result = runner.run_fixture(packet_fixture(), GOOD, root/'success',
                auth_fixture=dict(expired=True, refresh='success'))
            self.assertEqual(result['auth_audit'], dict(refreshes=1, clears=0, inference_posts=1))
            self.assertEqual(result['model_requests'], 0); self.assertFalse(result['os_sandbox'])
            self.assertEqual(json.loads((root/'success/auth-fixture.json').read_bytes()), dict(expired=True, refresh='success'))
            supplier.prepare_source.reset_mock(); execute.reset_mock()
            for bad in ({'expired': 1, 'refresh': 'success'}, {'expired': False, 'refresh': 'real'},
                        {'expired': False, 'refresh': 'success', 'token': 'FAKE_FORBIDDEN'}):
                with self.assertRaises(ValueError): runner.run_fixture(packet_fixture(), GOOD, root/'invalid', auth_fixture=bad)
            supplier.prepare_source.assert_not_called(); execute.assert_not_called()
            for bad in ({'refreshes': True, 'clears': 0, 'inference_posts': 1},
                        {'refreshes': 2, 'clears': 0, 'inference_posts': 1}):
                execute.return_value = child_reply(audit=bad)
                failed = runner.run_fixture(packet_fixture(), GOOD, root/('bad-'+str(bad['refreshes'])),
                    auth_fixture=dict(expired=True, refresh='success'))
                self.assertEqual(failed['status'], 'worker_failed')

    def test_direct_worker_binding_and_usage_checks_with_fake_provider_dependency(self):
        supplier = SimpleNamespace(invoke_fixture=Mock(return_value=copy.deepcopy(GOOD)))
        with tempfile.TemporaryDirectory(prefix='FAKE-direct-worker-') as folder, chdir(folder):
            Path('provider.py').write_bytes(FAKE_SOURCE)
            request = dict(tools=[], provider_source_sha256=runner.hashlib.sha256(FAKE_SOURCE).hexdigest(), sandbox_expected=False)
            for usage in (GOOD['usage'], None, {'input_tokens': 1, 'output_tokens': 2049, 'total_tokens': 2050}):
                payload = dict(request=request, fixture=GOOD)
                supplier.invoke_fixture.return_value = dict(response=GOOD['response'], usage=usage, fake_requests=1, model_requests=0)
                output = io.StringIO()
                with patch.object(runner, 'provider_fixture_module', return_value=supplier), \
                        patch.dict(runner.os.environ, {}, clear=True), \
                        patch.object(runner.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))), \
                        patch.object(runner.sys, 'stdout', output):
                    if usage is GOOD['usage']:
                        runner.worker(); self.assertFalse(json.loads(output.getvalue())['isolation_probe_passed'])
                    else:
                        with self.assertRaisesRegex(ValueError, 'Usage missing or invalid'): runner.worker()
                        self.assertEqual(output.getvalue(), '')
            supplier.invoke_fixture.reset_mock()
            payload['request'] = {**request, 'provider_source_sha256': 'f'*64}
            with patch.object(runner, 'provider_fixture_module', return_value=supplier), \
                    patch.dict(runner.os.environ, {}, clear=True), \
                    patch.object(runner.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))):
                with self.assertRaisesRegex(ValueError, 'Worker provider source mismatch'): runner.worker()
                supplier.invoke_fixture.assert_not_called()

    def test_controller_success_exclusive_reservation_and_redacted_child_failure(self):
        supplier, source, child = self.dependencies(child_reply())
        with tempfile.TemporaryDirectory(prefix='FAKE-controller-') as folder, source, child as execute:
            root = Path(folder); target = root/'success'
            result = runner.run_fixture(packet_fixture(), GOOD, target)
            self.assertEqual(result['status'], 'parsed_synthetic')
            self.assertEqual((result['fake_requests'], result['model_requests']), (1, 0))
            self.assertFalse(result['os_sandbox']); self.assertEqual(result['promotion_status'], 'blocked')
            before = (target/'attempt.json').read_bytes()
            with self.assertRaises(FileExistsError): runner.run_fixture(packet_fixture(), GOOD, target)
            self.assertEqual((target/'attempt.json').read_bytes(), before); self.assertEqual(execute.call_count, 1)
            execute.side_effect = subprocess.CalledProcessError(2, 'FAKE_CHILD', output=b'FAKE_SECRET', stderr=b'FAKE_SECRET')
            failed = runner.run_fixture(packet_fixture(), GOOD, root/'failed')
            self.assertEqual(failed['status'], 'worker_failed')
            self.assertNotIn(b'FAKE_SECRET', (root/'failed/result.json').read_bytes())
            self.assertFalse((root/'failed/proposal.json').exists())

    def test_controller_bad_reply_and_mock_timeout_preserve_consumption(self):
        supplier, source, child = self.dependencies(child_reply())
        with tempfile.TemporaryDirectory(prefix='FAKE-refusal-') as folder, source, child as execute:
            root = Path(folder)
            for index, text in enumerate(('x'*16385, '{"token":"FAKE_NEVER_PERSIST"}', 'not-json')):
                execute.return_value = child_reply(response=text)
                result = runner.run_fixture(packet_fixture(), GOOD, root/str(index))
                self.assertEqual(result['status'], 'worker_failed')
                self.assertFalse((root/str(index)/'proposal.json').exists())
                self.assertFalse((root/str(index)/'response.json').exists())
                self.assertNotIn(b'FAKE_NEVER_PERSIST', (root/str(index)/'result.json').read_bytes())
            execute.side_effect = subprocess.TimeoutExpired('FAKE_CHILD', .1)
            target = root/'timeout'; result = runner.run_fixture(packet_fixture(), GOOD, target, deadline=.1)
            self.assertEqual(result['status'], 'deadline_exceeded')
            self.assertFalse(result['os_sandbox'])
            before = (target/'attempt.json').read_bytes()
            with self.assertRaises(FileExistsError): runner.run_fixture(packet_fixture(), GOOD, target, deadline=.1)
            self.assertEqual((target/'attempt.json').read_bytes(), before)

    def test_synthetic_comparison_repeatability_through_real_controller_fake_child(self):
        supplier, source, child = self.dependencies(child_reply())
        with tempfile.TemporaryDirectory(prefix='FAKE-comparison-') as folder, source, child:
            root = Path(folder)
            first = rehearse.rehearsal(root/'first'); second = rehearse.rehearsal(root/'second')
            self.assertEqual(first, second)
            for file in ('comparison.json', 'comparison.csv', 'baseline.json', 'candidate.json'):
                self.assertEqual((root/'first'/file).read_bytes(), (root/'second'/file).read_bytes())
            self.assertEqual(first['qualification'], 'unqualified'); self.assertEqual(first['promotion_status'], 'blocked')
            self.assertEqual(first['model_requests'], 0)
            self.assertEqual(first['gate_verdict']['decision'], 'inconclusive')
            self.assertFalse(json.loads((root/'first/attempt/result.json').read_bytes())['os_sandbox'])


if __name__ == '__main__': unittest.main()
