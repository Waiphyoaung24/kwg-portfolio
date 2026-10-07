import json
from pathlib import Path
import tempfile
import time
import unittest
from urllib.parse import urlencode, parse_qs, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from register_gold_oauth import (ISSUER, RESOURCE, SCOPES, create_transaction,
    consume_callback, verify_tokens, read_json, write_new)


class RegistrationTest(unittest.TestCase):
    def test_pkce_callback_expiry_and_single_use(self):
        tx = create_transaction('urn:uuid:test')
        params = parse_qs(urlsplit(tx['url']).query)
        self.assertEqual(params['resource'], [RESOURCE])
        self.assertEqual(params['client_id'], ['dynamic_agent_client'])
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertNotEqual(params['code_challenge'][0], tx['verifier'])
        callback = '/auth/callback?' + urlencode(dict(state=tx['state'], code='fake', client_id='oaiapp_test'))
        with self.assertRaises(ValueError):
            consume_callback(callback + '&state=duplicate', tx)
        self.assertEqual(consume_callback(callback, tx), ('oaiapp_test', 'fake'))
        with self.assertRaises(ValueError):
            consume_callback(callback, tx)
        for field, value in [('state', 'wrong'), ('expires', 0)]:
            tx = create_transaction('host')
            callback = '/auth/callback?' + urlencode(dict(state=tx['state'], code='fake', client_id='oaiapp_test'))
            tx[field] = value
            with self.assertRaises(ValueError):
                consume_callback(callback, tx)
        tx = create_transaction('host', {'client_id': 'oaiapp_saved'})
        self.assertNotIn('agent_name_hint', parse_qs(urlsplit(tx['url']).query))
        with self.assertRaises(ValueError):
            consume_callback('/auth/callback?' + urlencode(dict(state=tx['state'], code='fake', client_id='oaiapp_other')), tx)

    def test_signed_identity_and_scopes(self):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
        public['kid'] = 'fixture'
        keys = {'keys': [public]}
        claims = dict(iss=ISSUER, sub='fake-account', aud='oaiapp_test',
                      exp=int(time.time()) + 300, iat=int(time.time()), nonce='nonce')
        def tokens(updates=None):
            identity = jwt.encode(dict(claims, **(updates or {})), private,
                                  algorithm='RS256', headers={'kid': 'fixture'})
            return dict(id_token=identity, access_token='FAKE', refresh_token='FAKE',
                        token_type='Bearer', scope=SCOPES, expires_in=300)
        good = tokens()
        result = verify_tokens(good, keys, 'oaiapp_test', 'nonce')
        self.assertEqual(result['model_requests'], 0)
        self.assertEqual(result['dispatch_status'], 'blocked')
        for update in ({'nonce': 'wrong'}, {'aud': 'other'}, {'iss': 'https://other.invalid'}, {'exp': 1}):
            with self.assertRaises((ValueError, jwt.PyJWTError)):
                verify_tokens(tokens(update), keys, 'oaiapp_test', 'nonce')
        with self.assertRaises(ValueError):
            verify_tokens(dict(good, scope='openid'), keys, 'oaiapp_test', 'nonce')
        with self.assertRaises(ValueError):
            verify_tokens(good, keys, 'oaiapp_test', 'nonce', {'subject': 'other', 'client_id': 'oaiapp_test'})
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        bad = dict(good, id_token=jwt.encode(claims, other, algorithm='RS256', headers={'kid': 'fixture'}))
        with self.assertRaises(jwt.InvalidSignatureError):
            verify_tokens(bad, keys, 'oaiapp_test', 'nonce')

    def test_no_inference_and_no_overwrite(self):
        with self.assertRaises(ValueError):
            read_json(None, 'POST', RESOURCE + '/responses')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'record.json'
            write_new(path, {'fake': 1})
            with self.assertRaises(FileExistsError):
                write_new(path, {'fake': 2})
            self.assertEqual(json.loads(path.read_text()), {'fake': 1})


if __name__ == '__main__':
    unittest.main()
