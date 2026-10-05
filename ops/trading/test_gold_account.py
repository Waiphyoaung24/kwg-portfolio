import copy
import gzip
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import gold_account as account


class AccountTest(unittest.TestCase):
    def test_controller_preflight_failure_and_round_replay_precede_reservation_or_auth(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'.batch3-vibe';root.mkdir()
            sealed=root/('sealed-account-'+'c'*12);sealed.mkdir()
            (sealed/'code').mkdir();review=root/'account-readiness';review.mkdir()
            metadata=dict(policy=account.POLICY,mode='gold_account_only',git_commit='c'*40,
                production_registry=str(root/'production-attempts'),production_dispatch='blocked',
                production_isolation_verified=False,server_account_verified=False,billing_ceiling_verified=False)
            (sealed/'readiness.json').write_text(json.dumps(metadata))
            for mode in ('boundary','termination'):
                attempt=review/('a'*64+'.'+mode);attempt.mkdir()
                (attempt/'receipt.json').write_text(json.dumps(dict(passed=True,cleanup_verified=True,
                    seal_sha256='a'*64,model_requests=0,forced_termination_verified=True)))
            with patch.object(account,'__file__',str(sealed/'code/gold_account.py')), \
                    patch.object(account,'verify_seal'),patch.object(account,'private_acl'), \
                    patch.object(account,'account_preflight',side_effect=ValueError('Engine unavailable')) as preflight, \
                    patch.object(account.subprocess,'run') as command,patch.object(account.subprocess,'Popen') as guard:
                with self.assertRaises(ValueError): account.run('a'*64,'accept','b'*32)
                path=review/account.acceptance_name('a'*64,'b'*32)
                self.assertFalse(path.exists());self.assertFalse((root/'gold-plan-auth').exists())
                path.mkdir();preflight.reset_mock()
                with self.assertRaises(FileExistsError): account.run('a'*64,'accept','b'*32)
                preflight.assert_not_called();command.assert_not_called();guard.assert_not_called()

    def test_explicit_verification_ids_preserve_each_consumed_round(self):
        with tempfile.TemporaryDirectory() as folder:
            review=Path(folder)
            old=review/('a'*64+'.accept');old.mkdir();(old/'receipt.json').write_bytes(b'failed')
            for verification in ('b'*32,'c'*32):
                attempt=review/account.acceptance_name('a'*64,verification)
                attempt.mkdir()
                with self.assertRaises(FileExistsError): attempt.mkdir()
            self.assertEqual((old/'receipt.json').read_bytes(),b'failed')
            self.assertEqual(len(list(review.iterdir())),3)
        for unsafe in (None,'','B'*32,'../'+'b'*32,'b'*31,False):
            with self.assertRaises(ValueError): account.acceptance_name('a'*64,unsafe)

    def test_preflight_requires_images_and_current_absence_without_rewriting_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);review=root/'account-readiness';review.mkdir()
            snapshot=root/'sealed-account-old';snapshot.mkdir()
            manifest=b'[]';(snapshot/'manifest.json').write_bytes(manifest)
            old_sha=account.hashlib.sha256(manifest).hexdigest()
            old=review/(old_sha+'.accept');old.mkdir()
            prefix='kwg-account-'+'b'*32+'-'
            # Old ownership policy is validated against its own seal, not the new policy.
            policy={'historical_fixture':True}
            owned=dict(policy=policy,containers={role:prefix+role for role in (
                'proxy','probe','keys','refresh','catalog','control','peer','peer-control')},
                networks={role:prefix+role for role in ('inner','outer')})
            (snapshot/'readiness.json').write_text(json.dumps({'policy':policy}))
            receipt=json.dumps(dict(mode='accept',seal_sha256=old_sha,passed=False,
                cleanup_verified=False,model_requests=0,dispatch_status='blocked')).encode()
            (old/'receipt.json').write_bytes(receipt)
            (old/'owned.json').write_text(json.dumps(owned))
            (old/'finished.json').write_text('{"finished":true}')
            fault=None;calls=[]
            def docker(args,**kwargs):
                nonlocal fault
                calls.append(args)
                action=args[5:]
                if action[0]=='info':
                    return account.subprocess.CompletedProcess(args,1 if fault=='engine' else 0,b'linux',b'')
                if action[0]=='image':
                    pin=action[-1]
                    image=dict(Id=account.SANDBOX_IMAGE,RepoDigests=[account.SQUID_IMAGE])
                    if fault=='image': image['RepoDigests']=[]
                    return account.subprocess.CompletedProcess(args,0,json.dumps(image).encode(),b'')
                return account.subprocess.CompletedProcess(args,1 if fault=='inventory' else 0,
                    (prefix+'proxy').encode() if fault=='remaining' else b'',b'')
            def private(path):
                # Fresh child directories intentionally inherit the protected private review parent.
                if path in (old,review/'docker-preflight'): raise ValueError('Inherited child, not protected root')
            with patch.object(account,'private_acl',side_effect=private),patch.object(account,'verify_seal') as seal, \
                    patch.object(account.subprocess,'run',side_effect=docker):
                result=account.account_preflight(root)
                self.assertEqual(result['predecessors'],[dict(attempt=old.name,resources_absent=True)])
                seal.assert_called_with(snapshot,old_sha)
                for fault in ('engine','image','inventory','remaining'):
                    with self.subTest(fault=fault),self.assertRaises(ValueError): account.account_preflight(root)
                fault=None
                bad={**owned,'containers':{**owned['containers'],'proxy':'unrelated'}}
                (old/'owned.json').write_text(json.dumps(bad))
                with self.assertRaises(ValueError): account.account_preflight(root)
                (old/'owned.json').write_text(json.dumps(owned))
                with patch.object(account,'verify_seal',side_effect=ValueError('Changed old seal')):
                    with self.assertRaises(ValueError): account.account_preflight(root)
                (old/'receipt.json').unlink()
                with self.assertRaises(FileNotFoundError): account.account_preflight(root)
                (old/'receipt.json').write_bytes(receipt)
            self.assertEqual((old/'receipt.json').read_bytes(),receipt)
            self.assertFalse(any('-'+('c'*32) in path.name for path in review.iterdir()))
            self.assertTrue(all(args[5] in ('info','image','ps','network') for args in calls))
            self.assertTrue(all('rm' not in args and 'pull' not in args and 'start' not in args for args in calls))
            self.assertEqual(list((review/'docker-preflight').iterdir()),[])

    def test_guardian_scope_and_unknown_renewal_survive_new_round_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);review=root/'account-readiness';review.mkdir()
            for mode in ('boundary','termination'):
                account.validate_guard_path(root,review/('a'*64+'.'+mode),'a'*64,None)
            for verification in ('b'*32,'c'*32):
                path=review/account.acceptance_name('a'*64,verification)
                account.validate_guard_path(root,path,'a'*64,verification)
                for unsafe,other in ((root/path.name,verification),(path,'d'*32),
                        (review/('a'*64+'.accept'),verification),(review/('a'*64+'.boundary'),verification)):
                    with self.assertRaises(ValueError): account.validate_guard_path(root,unsafe,'a'*64,other)
            raw=b'FAKE_CANARY_REGISTRATION';identity,marker=account.unconsumed_renewal(root,raw)
            self.assertEqual(identity,account.hashlib.sha256(raw).hexdigest())
            marker.write_bytes(b'{"state":"outcome_unknown"}')
            for verification in ('b'*32,'c'*32):
                account.acceptance_name('a'*64,verification)
                with self.assertRaises(ValueError): account.unconsumed_renewal(root,raw)
            self.assertEqual(marker.read_bytes(),b'{"state":"outcome_unknown"}')

    def test_fixed_requests_bounds_errors_no_inference_or_retry(self):
        calls=[]
        class Response:
            status_code=200
            headers={}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def iter_raw(self,chunk_size):
                self.chunk_size=chunk_size
                yield b'{"keys":[]}'
        class Client:
            def stream(self,*args,**kwargs): calls.append((args,kwargs));return response
        response=Response();client=Client()
        account.request(client,'keys')
        value={'client_id':'oaiapp_test','refresh_token':'FAKE_CANARY_REFRESH'}
        account.request(client,'refresh',value)
        account.request(client,'catalog','FAKE_CANARY_ACCESS')
        self.assertEqual([c[0] for c in calls],[('GET',account.JWKS),('POST',account.TOKEN),('GET',account.MODELS)])
        self.assertEqual(calls[1][1]['data'],{**value,'grant_type':'refresh_token','resource':account.RESOURCE})
        self.assertNotIn('scope',calls[1][1]['data'])
        for operation in ('inference','responses','https://evil.invalid'):
            with self.assertRaises(ValueError): account.request(client,operation,value)
        self.assertEqual(len(calls),3)
        for status in (302,401,429,500):
            response.status_code=status
            before=len(calls)
            with self.assertRaises(ValueError): account.request(client,'refresh',value)
            self.assertEqual(len(calls),before+1)
        response.status_code=200
        response.iter_raw=lambda **kwargs: iter([b'x'*(account.BOUND+1)])
        with self.assertRaises(ValueError): account.request(client,'keys')
        response.iter_raw=lambda **kwargs: iter([b'{"keys":[],"keys":[]}'])
        with self.assertRaises(ValueError): account.request(client,'keys')
        response.headers={'content-encoding':'br'}
        with self.assertRaises(ValueError): account.request(client,'keys')
        response.headers={'content-encoding':'gzip'}
        response.iter_raw=lambda **kwargs: iter([gzip.compress(b'{"keys":[]}')])
        self.assertEqual(account.request(client,'keys'),{'keys':[]})
        response.iter_raw=lambda **kwargs: iter([gzip.compress(b'x'*(account.BOUND+1))])
        with self.assertRaises(account.AccountResponseError): account.request(client,'keys')
        response.iter_raw=lambda **kwargs: iter([gzip.compress(b'{"keys":[]}')[:-2]])
        with self.assertRaises(account.AccountResponseError): account.request(client,'keys')
        large=json.dumps({'models':[{'slug':account.MODEL,'metadata':'x'*(account.BOUND+1)}]}).encode()
        response.iter_raw=lambda **kwargs: iter([gzip.compress(large)])
        self.assertTrue(account.catalog_matches(account.request(client,'catalog','FAKE_CANARY_ACCESS')))

    def test_signed_identity_binding_and_nonce_validation_contract(self):
        previous=dict(client_id='oaiapp_test',subject='subject',issuer=account.ISSUER,
            ext_agent_host_id='host',dispatch_status='blocked',billing_ceiling_verified=False,
            model_requests=0,scopes=sorted(account.SCOPES),id_token='OLD_ID',access_token='OLD_ACCESS',expires_at=int(time.time())+3600)
        identity=dict(sub='subject',aud='oaiapp_test',nonce='original')
        access=dict(sub='subject',client_id='oaiapp_test',aud=account.RESOURCE,
            scope=' '.join(sorted(account.SCOPES)),exp=int(time.time())+3600)
        tokens=dict(token_type='Bearer',expires_in=3600,scope=access['scope'],
            id_token='NEW_ID',access_token='NEW_ACCESS',refresh_token='NEW_REFRESH')
        def claims(token,*args,**kwargs): return identity if token in ('OLD_ID','NEW_ID') else access
        with patch.object(account,'jwt_claims',side_effect=claims):
            self.assertEqual(account.validate_saved(previous,{}, {'client_id':'oaiapp_test'},{'id':'host'}),identity)
            result=account.renewed_record(tokens,{},previous,identity)
            self.assertEqual(result['client_id'],previous['client_id'])
            self.assertEqual(result['model_requests'],0)
            self.assertFalse(result['billing_ceiling_verified'])
            for field,value in (('sub','other'),('nonce','invented'),('azp','other')):
                prior=copy.deepcopy(identity);identity[field]=value
                with self.assertRaises(ValueError): account.renewed_record(tokens,{},previous,prior)
                identity.clear();identity.update(prior)
            for field,value in (('client_id','other'),('exp',0),('scope','openid')):
                prior=copy.deepcopy(access);access[field]=value
                with self.assertRaises(ValueError): account.renewed_record(tokens,{},previous,identity)
                access.clear();access.update(prior)
            for update in ({'expires_in':True},{'expires_in':0},{'token_type':'other'}, {'scope':'openid'},{'refresh_token':''},{'id_token':None}):
                with self.assertRaises(ValueError): account.renewed_record({**tokens,**update},{},previous,identity)
            identity.pop('nonce')  # Refresh does not require a fabricated authorization nonce.
            account.renewed_record(tokens,{},previous,{'nonce':'original'})

    def test_atomic_publication_and_catalog_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'registration.json';path.write_bytes(b'original')
            with patch.object(account,'private_acl'):
                account.atomic_publish(path,b'original',{'fake':1})
                self.assertEqual(json.loads(path.read_bytes()),{'fake':1})
                with self.assertRaises(ValueError): account.atomic_publish(path,b'original',{'fake':2})
            with patch.object(account,'private_acl',side_effect=ValueError('ACL refused')):
                with self.assertRaises(ValueError): account.atomic_publish(path,path.read_bytes(),{'fake':3})
            self.assertEqual(json.loads(path.read_bytes()),{'fake':1})
        self.assertTrue(account.catalog_matches({'models':[{'slug':account.MODEL}]}))
        self.assertFalse(account.catalog_matches({'models':[{'slug':'other'}]}))
        for value in ({'data':[]},{'models':[{'id':account.MODEL}]},{'models':[{'slug':'same'},{'slug':'same'}]}):
            with self.assertRaises(ValueError): account.catalog_matches(value)


if __name__=='__main__': unittest.main()
