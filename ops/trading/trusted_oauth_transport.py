"""Trusted account-bound transport core; public live dispatch remains disabled."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import sys
import time

from batch3_runner import MODEL, MAX_BYTES, MAX_TOKENS, provider_fixture_module, research_module, write_once

STORE = Path(__file__).resolve().parents[2]/'.batch3-vibe/profile/.vibe-trading/auth/openai-codex.json'
PROVIDER_SHA = '64e257725e04ff0b1d8e7a56061d67aa190113d60340850b45bc821de74e867e'


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Invalid binding JSON')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    json.dumps(value, allow_nan=False)
    return value


def binding_metadata(token):
    try:
        account, access = token['account_id'], token['access']
        if not isinstance(account, str) or not account or not isinstance(access, str):
            raise ValueError()
        payload = access.split('.')[1]
        claims = strict_json(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
        claim_account = claims['https://api.openai.com/auth']['chatgpt_account_id']
        expiry = claims['exp']
        if (claim_account != account or type(expiry) not in (int,float) or not math.isfinite(expiry)):
            raise ValueError()
        return {'account_sha256': hashlib.sha256(account.encode()).hexdigest(),
            'local_account_binding_verified': True, 'token_fresh': expiry > time.time()+300,
            'jwt_signature_verified': False, 'server_account_verified': False,
            'billing_ceiling_verified': False, 'model_requests': 0, 'dispatch_status': 'blocked'}
    except Exception:
        raise ValueError('Account binding invalid; no credential details recorded') from None


def check_binding():
    # Read only the fixed Vibe store; never import/copy the Codex CLI store.
    for path in (STORE, *STORE.parents):
        if path.is_symlink() or (getattr(path.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Credential reparse path rejected')
    with STORE.open('rb') as source:
        raw = source.read(65537)
    if len(raw) > 65536:
        raise ValueError('Credential metadata exceeds limit')
    return binding_metadata(strict_json(raw))


def invoke_bound(source, prompt, token, expected_account_sha, http_module):
    """Trusted internal core. Test with fake HTTP only until dispatch is enabled."""
    if hashlib.sha256(source).hexdigest() != PROVIDER_SHA:
        raise ValueError('Trusted provider identity mismatch')
    metadata = binding_metadata(token)
    if not metadata['token_fresh'] or metadata['account_sha256'] != expected_account_sha:
        raise ValueError('Bound account mismatch or expired token')
    if not isinstance(prompt,str) or len(prompt.encode()) > MAX_BYTES:
        raise ValueError('Bound prompt exceeds limit')
    # ponytail: expired tokens fail closed; refresh stays in the existing app until separately reviewed.
    with provider_fixture_module().provider_namespace(source, http_module) as namespace:
        adapter = namespace['OpenAICodexLLM'](model=MODEL, reasoning_effort='medium',
            timeout=120, max_requests=1, codex_url='https://chatgpt.com/backend-api/codex/responses')
        adapter._headers = lambda **kwargs: namespace['_build_headers'](token['account_id'],token['access'])
        try:
            message = adapter.invoke([{'role':'user','content':prompt}])
            usage = message.usage_metadata
            if (message.tool_calls or message.response_metadata.get('model_name') != 'gpt-6.1-sol'
                    or message.response_metadata.get('finish_reason') != 'stop'
                    or not isinstance(usage,dict) or set(usage) != {'input_tokens','output_tokens','total_tokens'}
                    or any(type(n) is not int or n < 0 for n in usage.values())
                    or usage['total_tokens'] != usage['input_tokens']+usage['output_tokens']
                    or usage['output_tokens'] > MAX_TOKENS):
                raise ValueError()
            proposal = research_module().parse_proposal(message.content.encode())
            return {'proposal':proposal, 'usage':usage, 'account_sha256':metadata['account_sha256'],
                'model':'gpt-6.1-sol','reasoning_effort':'medium','promotion_status':'blocked'}
        except Exception:
            raise ValueError('Bound provider request failed; no retry or credential details recorded') from None


def dispatch(packet, binding, output):
    # No live entry until billing enforcement, outer controller and current seal pass review.
    raise ValueError('Live dispatch disabled: billing enforcement and production controller unverified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-binding', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check_binding()
        write_once(args.output,result)
        print(json.dumps(result,sort_keys=True))
    except Exception:
        print('Binding check refused; no token details recorded.',file=sys.stderr)
        raise SystemExit(2) from None
