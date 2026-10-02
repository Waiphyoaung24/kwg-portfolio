import json
import time
import unittest

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
import gold_account as account


class AccountCryptoTest(unittest.TestCase):
    def test_real_signature_expiry_issuer_audience_and_refresh_binding(self):
        private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        key=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()));key['kid']='fake'
        keys={'keys':[key]}
        now=int(time.time())
        base=dict(iss=account.ISSUER,sub='subject',aud='oaiapp_test',iat=now,exp=now+3600,nonce='original')
        def signed(claims,signer=private): return jwt.encode(claims,signer,algorithm='RS256',headers={'kid':'fake'})
        old_identity=signed({**base,'iat':now-7200,'exp':now-3600})
        access={**base,'aud':account.RESOURCE,'client_id':'oaiapp_test','scope':' '.join(sorted(account.SCOPES))}
        previous=dict(client_id='oaiapp_test',subject='subject',issuer=account.ISSUER,
            ext_agent_host_id='host',dispatch_status='blocked',billing_ceiling_verified=False,
            model_requests=0,scopes=sorted(account.SCOPES),id_token=old_identity,
            access_token=signed({**access,'iat':now-7200,'exp':now-3600}),expires_at=now-3600)
        prior=account.validate_saved(previous,keys,{'client_id':'oaiapp_test'},{'id':'host'})
        tokens=dict(token_type='Bearer',expires_in=3600,scope=access['scope'],
            id_token=signed(base),access_token=signed(access),refresh_token='FAKE_CANARY_REPLACEMENT')
        result=account.renewed_record(tokens,keys,previous,prior)
        self.assertEqual(result['subject'],'subject')
        for update in ({'iss':'https://evil.invalid'},{'sub':'wrong'},{'aud':'wrong'},{'exp':0},{'nonce':'wrong'}):
            with self.assertRaises((ValueError,jwt.PyJWTError)):
                account.renewed_record({**tokens,'id_token':signed({**base,**update})},keys,previous,prior)
        other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        with self.assertRaises(jwt.InvalidSignatureError):
            account.renewed_record({**tokens,'id_token':signed(base,other)},keys,previous,prior)
        with self.assertRaises(ValueError):
            account.renewed_record(tokens,{'keys':[key,key]},previous,prior)
        with self.assertRaises(jwt.ExpiredSignatureError):
            account.jwt_claims(old_identity,keys,'oaiapp_test')


if __name__=='__main__': unittest.main()
