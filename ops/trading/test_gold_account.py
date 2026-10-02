import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import gold_account as account


class AccountTest(unittest.TestCase):
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
        response.headers={'content-encoding':'gzip'}
        with self.assertRaises(ValueError): account.request(client,'keys')

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
