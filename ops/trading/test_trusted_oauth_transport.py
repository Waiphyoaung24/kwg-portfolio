import base64
import json
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from trusted_oauth_transport import binding_metadata, dispatch, invoke_bound
from batch3_runner import provider_fixture_module
from test_batch3_rehearsal import GOOD


def token(account='fake-account', claim='fake-account', expires=None):
    claims={'exp':expires or time.time()+3600,'https://api.openai.com/auth':{'chatgpt_account_id':claim}}
    payload=base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    return {'account_id':account,'access':'FAKE_CANARY.'+payload+'.FAKE_CANARY','refresh':'FAKE_REFRESH_CANARY','expires':1}


class TrustedTransportTest(unittest.TestCase):
    def test_bound_headers_single_post_and_fail_closed_responses(self):
        provider=provider_fixture_module()
        frozen=Path(__file__).resolve().parent.parent/'inputs/provider.py'
        source=frozen.read_bytes() if frozen.is_file() else provider.prepare_source(
            Path(__file__).resolve().parents[2]/'.batch3-vibe/upstream/agent/src/providers/openai_codex.py',
            Path(__file__).with_name('vibe-codex-one-request.patch'))
        credential=token()
        account_sha=binding_metadata(credential)['account_sha256']
        calls=[]
        result_model='gpt-6.1-sol'
        usage=dict(GOOD['usage'])
        status=200
        completion='completed'
        tools=False
        test=self
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            @property
            def status_code(self): return status
            def iter_bytes(self,**kwargs):
                events=[{'type':'response.output_text.delta','delta':GOOD['response']},
                    {'type':'response.completed','response':{'status':completion,'model':result_model,'usage':usage}}]
                if completion is None:
                    events[-1]['response'].pop('status')
                if tools:
                    events.insert(0,{'type':'response.output_item.done','item':{'type':'function_call','call_id':'fake','name':'forbidden','arguments':'{}'}})
                yield ''.join('data: '+json.dumps(event)+'\n\n' for event in events).encode()
        class Client:
            def __init__(self,**options):
                test.assertEqual(options,{'timeout':120,'follow_redirects':False,'trust_env':False})
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def stream(self,method,url,**options):
                test.assertEqual(method,'POST')
                test.assertEqual(url,'https://chatgpt.com/backend-api/codex/responses')
                test.assertEqual(options['headers']['chatgpt-account-id'],credential['account_id'])
                test.assertEqual(options['headers']['Authorization'],'Bearer '+credential['access'])
                body=options['json']
                test.assertEqual(body['model'],'gpt-6.1-sol')
                test.assertEqual(body['reasoning'],{'effort':'medium'})
                test.assertEqual(body['max_output_tokens'],2048)
                test.assertEqual(body['tool_choice'],'none')
                test.assertFalse(body['parallel_tool_calls'])
                test.assertNotIn('tools',body)
                calls.append(1)
                return Response()
        http=SimpleNamespace(Client=Client)
        result=invoke_bound(source,'fake prompt',credential,account_sha,http)
        self.assertEqual(len(calls),1)
        self.assertEqual(result['usage'],GOOD['usage'])
        self.assertNotIn('CANARY',json.dumps(result))
        self.assertEqual(result['promotion_status'],'blocked')
        for failure in ('401','model','usage','tools','missing_status','in_progress','unexpected'):
            calls.clear()
            status=401 if failure=='401' else 200
            result_model='wrong' if failure=='model' else 'gpt-6.1-sol'
            usage=None if failure=='usage' else dict(GOOD['usage'])
            tools=failure=='tools'
            completion=None if failure=='missing_status' else failure if failure in ('in_progress','unexpected') else 'completed'
            with self.assertRaises(ValueError) as error:
                invoke_bound(source,'fake prompt',credential,account_sha,http)
            self.assertNotIn('CANARY',str(error.exception))
            self.assertEqual(len(calls),1)
        calls.clear()
        for raw,cred,bound in ((source+b' ',credential,account_sha),(source,credential,'wrong'),
                (source,token(expires=time.time()-1),account_sha)):
            with self.assertRaises(ValueError):
                invoke_bound(raw,'fake prompt',cred,bound,http)
        self.assertEqual(calls,[])

    def test_binding_local_only_and_no_secret_output(self):
        result=binding_metadata(token())
        self.assertTrue(result['local_account_binding_verified'])
        self.assertFalse(result['jwt_signature_verified'])
        self.assertFalse(result['server_account_verified'])
        self.assertTrue(result['token_fresh'])
        self.assertNotIn('fake-account',json.dumps(result))
        self.assertNotIn('CANARY',json.dumps(result))
        self.assertFalse(binding_metadata(token(expires=time.time()-1))['token_fresh'])
        for value in (token(claim='other'),token(account=''),{'access':'FAKE_CANARY'}):
            with self.assertRaises(ValueError) as error:
                binding_metadata(value)
            self.assertNotIn('CANARY',str(error.exception))

    def test_dispatch_blocked_before_credentials_or_network(self):
        with patch('pathlib.Path.open',side_effect=AssertionError('No credential reads')):
            with self.assertRaisesRegex(ValueError,'billing enforcement'):
                dispatch(None,None,None)
