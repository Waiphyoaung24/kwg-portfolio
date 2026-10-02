import concurrent.futures
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import supported_gateway as gateway
from test_research_gold import packet_fixture
from trusted_gateway import reserve


class SupportedGatewayTest(unittest.TestCase):
    def test_synthetic_binding_refuses_real_expired_wrong_and_missing_records(self):
        good = {**gateway.BINDING, 'access_token': 'FAKE_CANARY_ACCESS', 'expires_at': time.time()+3600}
        self.assertEqual(gateway.fake_binding(good), gateway.BINDING_SHA)
        for record in (None, {**good, 'expires_at': 0}, {**good, 'expires_at': float('nan')},
                       {**good, 'client_id': 'other'}, {**good, 'subject': 'other'},
                       {**good, 'access_token': 'real'}, {**good, 'refresh_token': 'FAKE'}):
            with self.assertRaises(ValueError): gateway.fake_binding(record)

    def test_supported_reservation_is_exclusive_and_never_relaxes_synthetic_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            packet = packet_fixture()
            def attempt(_):
                try: return reserve(root, packet, 'a'*64, 'crash', supported=True)
                except FileExistsError: return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(attempt, range(2)))
            self.assertEqual(sum(p is not None for p in results), 1)
            saved = next(p for p in results if p is not None)
            before = (saved/'attempt.json').read_bytes()
            packet['experiment_id'] = 'renamed-consumed-attempt'
            with self.assertRaises(FileExistsError): reserve(root, packet, 'b'*64, 'success', supported=True)
            self.assertEqual((saved/'attempt.json').read_bytes(), before)
            with self.assertRaises(ValueError): reserve(root, packet, 'a'*64, 'crash')
            packet['limitations'] = ['historical_costs_unverified']
            with self.assertRaises(ValueError): reserve(root, packet, 'a'*64, 'success', supported=True)

    def test_config_refuses_extra_mounts_wrong_runtime_network_and_command(self):
        mount = {'Source': 'C:/fixture.py', 'Destination': '/snapshot/code/fixture.py', 'Type': 'bind', 'RW': False}
        host = {'NetworkMode': 'isolated', 'ReadonlyRootfs': True, 'Privileged': False, 'CapDrop': ['ALL'],
                'SecurityOpt': ['no-new-privileges'], 'PidsLimit': 32, 'Memory': 134217728,
                'NanoCpus': 1000000000, 'ExtraHosts': [], 'Dns': ['127.0.0.1'], 'PortBindings': {},
                'Mounts': [{'Source': mount['Source'], 'Target': mount['Destination'], 'Type': 'bind', 'ReadOnly': True}]}
        state = {'Image': gateway.SANDBOX_IMAGE, 'Config': {'User': '65534:65534', 'Entrypoint': [gateway.PYTHON],
                 'Cmd': ['-I', '-B']}, 'HostConfig': host, 'Mounts': [mount]}
        args = (gateway.SANDBOX_IMAGE, 'isolated', gateway.PYTHON, ['-I', '-B'], [(Path('C:/fixture.py'), mount['Destination'])], {'dns': ['127.0.0.1']})
        gateway.inspect_container(state, *args)
        alterations = [('Image', 'sha256:wrong'), ('Mounts', [mount, {**mount, 'Destination': '/var/run/docker.sock'}])]
        for key, value in alterations:
            with self.assertRaises(ValueError): gateway.inspect_container({**state, key: value}, *args)
        for key, value in [('NetworkMode', 'bridge'), ('ReadonlyRootfs', False), ('Dns', ['8.8.8.8']), ('Privileged', True)]:
            with self.assertRaises(ValueError): gateway.inspect_container({**state, 'HostConfig': {**host, key: value}}, *args)
        with self.assertRaises(ValueError): gateway.inspect_container({**state, 'Mounts': [{**mount, 'RW': True}]}, *args)

    def test_readiness_fixed_registry_flags_replay_and_stop_on_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)/'.batch3-vibe'
            sealed = root/('sealed-supported-'+'a'*12)
            (sealed/'code').mkdir(parents=True)
            production = root/'production-attempts'; production.mkdir()
            review = root/'supported-readiness'; review.mkdir()
            metadata = {'mode': 'supported_fake_only', 'git_commit': 'a'*40, 'production_registry': str(production),
                'registry_acl_checked': True, 'policy': gateway.POLICY, 'production_dispatch': 'blocked',
                'production_isolation_verified': False, 'server_account_verified': False, 'billing_ceiling_verified': False}
            (sealed/'readiness.json').write_text(json.dumps(metadata))
            calls = []
            def fake(sealed, sha, registry, packet, case):
                calls.append(case)
                self.assertEqual(registry, review/'attempts')
                attempt = reserve(registry, packet, sha, case, supported=True)
                result = {'state': 'binding_refused', 'cleanup_verified': True, 'configuration_verified': False}
                gateway.write_once(attempt/'receipt.json', result)
                return result
            with patch.object(gateway, '__file__', str(sealed/'code/supported_gateway.py')), \
                    patch.object(gateway, 'verify_seal'), patch.object(gateway, 'rehearse', side_effect=fake):
                result = gateway.readiness('b'*64)
                self.assertFalse(result['offline_checks_passed'])
                self.assertTrue(all(r['replay_refused'] for r in result['cases']))
                self.assertEqual(result['model_requests'], 0)
                self.assertEqual(result['dispatch_status'], 'blocked')
                self.assertEqual(list(production.iterdir()), [])
                for key in ('production_isolation_verified', 'server_account_verified', 'billing_ceiling_verified'):
                    self.assertFalse(result[key])
                before = len(calls)
                with self.assertRaises(FileExistsError): gateway.readiness('b'*64)
                self.assertEqual(len(calls), before)
                for key, value in [('policy', {}), ('server_account_verified', True), ('production_dispatch', 'enabled')]:
                    (sealed/'readiness.json').write_text(json.dumps({**metadata, key: value}))
                    with self.assertRaises(ValueError): gateway.readiness('c'*64)
                self.assertEqual(len(calls), before)


if __name__ == '__main__':
    unittest.main()
