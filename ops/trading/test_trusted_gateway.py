import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from trusted_gateway import reserve, validate_response, verify_seal
from test_research_gold import packet_fixture


class GatewayTest(unittest.TestCase):
    def test_readiness_uses_fixed_fake_registry_and_cannot_claim_live_readiness(self):
        import trusted_gateway as gateway
        from batch3_runner import write_once
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'.batch3-vibe'
            sealed=root/('sealed-gateway-readiness-'+'a'*12)
            (sealed/'code').mkdir(parents=True)
            production=root/'production-attempts'; production.mkdir()
            metadata={'mode':'fake_readiness_only','git_commit':'a'*40,
                'production_registry':str(production),'registry_acl_checked':True,
                'production_dispatch':'blocked','billing_ceiling_verified':False,
                'server_account_verified':False,'production_isolation_verified':False}
            write_once(sealed/'readiness.json',metadata)
            cases=[]
            def fake(registry,packet,seal_sha,case,deadline):
                cases.append(case)
                self.assertEqual(registry,root/'gateway-readiness/attempts')
                attempt=reserve(registry,packet,seal_sha,case)
                result={'status':'parsed_synthetic' if case=='success' else 'deadline_exceeded' if case=='timeout' else 'provider_failed',
                    'configuration_verified':True,'cleanup_verified':case!='bad_usage',
                    'response':{'fake_requests':1},'model_requests':0}
                write_once(attempt/'receipt.json',result)
                return result
            with patch.object(gateway,'__file__',str(sealed/'code/trusted_gateway.py')), \
                    patch.object(gateway,'verify_seal'),patch.object(gateway,'rehearse',side_effect=fake):
                result=gateway.readiness('b'*64)
                self.assertEqual(cases,sorted(gateway.CASES))
                self.assertFalse(result['offline_checks_passed'])
                self.assertTrue(all(row['replay_refused'] for row in result['cases']))
                self.assertEqual(result['model_requests'],0)
                self.assertEqual(result['dispatch_status'],'blocked')
                self.assertTrue(result['human_approval_required'])
                for flag in ('production_isolation_verified','server_account_verified','billing_ceiling_verified'):
                    self.assertFalse(result[flag])
                self.assertEqual(list(production.iterdir()),[])
                with self.assertRaises(FileExistsError): gateway.readiness('b'*64)
                self.assertEqual(len(cases),5)
                for key,value in [('production_registry',str(root/'replacement')),
                    ('billing_ceiling_verified',True),('production_dispatch','enabled')]:
                    changed={**metadata,key:value}
                    (sealed/'readiness.json').write_text(json.dumps(changed))
                    with self.assertRaises(ValueError): gateway.readiness('c'*64)
                self.assertEqual(len(cases),5)

    def test_worker_refuses_oversized_frame_before_parsing(self):
        import io
        from types import SimpleNamespace
        import trusted_gateway as gateway
        raw=json.dumps({'case':'success','prompt':'fixture'}).encode().ljust(gateway.MAX_BYTES+1,b' ')
        with patch.object(gateway.sys,'flags',SimpleNamespace(isolated=1,no_site=1)), \
                patch.object(gateway.os,'getuid',return_value=65534,create=True), \
                patch.object(gateway.signal,'alarm',create=True), \
                patch.object(gateway.signal,'signal'),patch.object(gateway.signal,'SIGALRM',14,create=True), \
                patch.object(gateway.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(raw))), \
                patch.object(gateway,'strict_json',side_effect=AssertionError('Oversized frame reached parser')):
            with self.assertRaisesRegex(ValueError,'input limit'):
                gateway.worker()

    def test_unsafe_container_never_receives_input_and_errors_are_not_saved(self):
        import subprocess
        import trusted_gateway as gateway
        frozen=Path(__file__).resolve().parent.parent/'inputs/provider.py'
        provider=(frozen if frozen.is_file() else Path(__file__).resolve().parents[2]/'.batch3-vibe/sealed-trusted-transport-20261002/inputs/provider.py').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            sealed=Path(folder)/'sealed'
            (sealed/'code').mkdir(parents=True)
            (sealed/'inputs').mkdir()
            (sealed/'inputs/provider.py').write_bytes(provider)
            for mode in ('unsafe_network','create_error'):
                commands=[]
                def run(command,**kwargs):
                    commands.append(command)
                    self.assertNotIn('input',kwargs)
                    if 'create' in command and mode=='create_error':
                        raise subprocess.CalledProcessError(1,command,output=b'FAKE_SECRET_CANARY')
                    if 'inspect' in command:
                        return subprocess.CompletedProcess(command,0,json.dumps([{
                            'HostConfig':{'Mounts':[],'NetworkMode':'bridge'}}]).encode())
                    self.assertNotIn('start',command)
                    return subprocess.CompletedProcess(command,0,b'')
                with patch.object(gateway,'__file__',str(sealed/'code/trusted_gateway.py')), \
                        patch.object(gateway,'verify_seal'),patch.object(gateway.subprocess,'run',side_effect=run):
                    result=gateway.rehearse(Path(folder)/mode,packet_fixture(),'a'*64,'success')
                self.assertEqual(result['status'],'controller_failed')
                self.assertFalse(result['configuration_verified'])
                self.assertTrue(result['cleanup_verified'])
                self.assertTrue(any('rm' in command for command in commands))
                for path in (Path(folder)/mode).rglob('*.json'):
                    self.assertNotIn('FAKE_SECRET_CANARY',path.read_text())

    def test_reservation_survives_failure_and_concurrent_retry(self):
        packet=packet_fixture()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def attempt(_):
                try: return reserve(root,packet,'a'*64,'success')
                except FileExistsError: return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                attempts=list(pool.map(attempt,range(2)))
            self.assertEqual(sum(p is not None for p in attempts),1)
            saved=next(p for p in attempts if p is not None)
            before=(saved/'attempt.json').read_bytes()
            packet['experiment_id']='renamed-same-manifest'
            packet['development']['last_close']=101.5
            with self.assertRaises(FileExistsError):
                reserve(root,packet,'b'*64,'401')
            self.assertEqual((saved/'attempt.json').read_bytes(),before)

    def test_seal_rejects_tampering_extra_files_and_traversal(self):
        import hashlib
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'code').mkdir()
            raw=b'harmless'
            (root/'code/a.py').write_bytes(raw)
            manifest=[{'path':'code/a.py','sha256':hashlib.sha256(raw).hexdigest()}]
            def manifest_hash():
                encoded=json.dumps(manifest).encode()
                (root/'manifest.json').write_bytes(encoded)
                return hashlib.sha256(encoded).hexdigest()
            expected=manifest_hash()
            verify_seal(root,expected)
            (root/'code/a.py').write_bytes(b'changed')
            with self.assertRaises(ValueError): verify_seal(root,expected)
            (root/'code/a.py').write_bytes(raw)
            (root/'extra').write_bytes(raw)
            with self.assertRaises(ValueError): verify_seal(root,expected)
            (root/'extra').unlink()
            manifest[0]['path']='../outside'
            with self.assertRaises(ValueError): verify_seal(root,manifest_hash())

    def test_response_requires_account_usage_and_exact_shape(self):
        from trusted_gateway import FAKE_ACCOUNT_SHA
        value={'status':'parsed_synthetic','fake_requests':1,'model_requests':0,
            'result':{'proposal':{'kind':'ema20_slope_filter','lookback_bars':3,'hypothesis':'fixture'},
                'usage':{'input_tokens':1,'output_tokens':2,'total_tokens':3},
                'account_sha256':FAKE_ACCOUNT_SHA,'model':'gpt-6.1-sol',
                'reasoning_effort':'medium','promotion_status':'blocked'}}
        validate_response(value)
        for field,changed in [('account_sha256','f'*64),('model','other'),
                ('usage',{'input_tokens':1,'output_tokens':2,'total_tokens':4})]:
            altered=json.loads(json.dumps(value)); altered['result'][field]=changed
            with self.assertRaises(ValueError): validate_response(altered)
        value['token']='FAKE_SECRET_CANARY'
        with self.assertRaises(ValueError): validate_response(value)
