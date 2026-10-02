"""One-time supported ChatGPT registration. No inference or billing operations."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import uuid

import httpx
import jwt

ISSUER = 'https://auth.openai.com'
AUTHORIZE = ISSUER + '/api/accounts/authorize'
TOKEN = ISSUER + '/api/accounts/oauth/token'
JWKS = ISSUER + '/.well-known/jwks.json'
RESOURCE = 'https://api.openai.com/v1'
SCOPES = 'openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'
PORT = 1456
REDIRECT = f'http://127.0.0.1:{PORT}/auth/callback'


def create_transaction(host_id, registration=None):
    value = {name: secrets.token_urlsafe(32) for name in ('state', 'nonce', 'verifier')}
    value.update(expires=time.monotonic() + 600, used=False,
                 client_id=(registration or {}).get('client_id'))
    params = dict(client_id=value['client_id'] or 'dynamic_agent_client',
        ext_agent_host_id=host_id, response_type='code', redirect_uri=REDIRECT,
        scope=SCOPES, resource=RESOURCE, state=value['state'], nonce=value['nonce'],
        code_challenge_method='S256', code_challenge=base64.urlsafe_b64encode(
            hashlib.sha256(value['verifier'].encode()).digest()).decode().rstrip('='))
    if not value['client_id']:
        params['agent_name_hint'] = 'KWG Gold Research'
    value['url'] = AUTHORIZE + '?' + urlencode(params)
    return value


def consume_callback(path, transaction):
    parsed = urlsplit(path)
    if parsed.path != '/auth/callback' or parsed.scheme or parsed.netloc:
        raise ValueError('Invalid callback')
    params = parse_qs(parsed.query, keep_blank_values=True, max_num_fields=12)
    if any(len(values) != 1 for values in params.values()):
        raise ValueError('Duplicate callback field')
    if (transaction['used'] or time.monotonic() >= transaction['expires']
            or not secrets.compare_digest(params.get('state', [''])[0], transaction['state'])):
        raise ValueError('Invalid callback state')
    transaction['used'] = True
    if 'error' in params:
        raise ValueError('Authorization declined')
    client_id = params.get('client_id', [transaction['client_id']])[0]
    if (not isinstance(client_id, str) or not client_id.startswith('oaiapp_')
            or len(client_id) > 256 or not params.get('code', [''])[0]
            or (transaction['client_id'] and transaction['client_id'] != client_id)):
        raise ValueError('Invalid issued client')
    return client_id, params['code'][0]


def read_json(client, method, url, **kwargs):
    # Only authentication destinations are reachable through this helper.
    if (method, url) not in {('POST', TOKEN), ('GET', JWKS)}:
        raise ValueError('Authentication endpoint required')
    with client.stream(method, url, **kwargs) as response:
        if response.status_code != 200:
            raise ValueError('Authentication HTTP request failed')
        raw = bytearray()
        for chunk in response.iter_bytes():
            raw.extend(chunk)
            if len(raw) > 262144:
                raise ValueError('Authentication response too large')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Authentication object required')
    return value


def verify_tokens(tokens, keys, client_id, nonce, previous=None):
    header = jwt.get_unverified_header(tokens['id_token'])
    if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str):
        raise ValueError('Unsupported identity signature')
    matches = [key for key in keys['keys'] if key.get('kid') == header['kid']]
    if len(matches) != 1:
        raise ValueError('Identity signing key not unique')
    key = jwt.PyJWK.from_dict(matches[0], algorithm='RS256')
    claims = jwt.decode(tokens['id_token'], key.key, algorithms=['RS256'],
        audience=client_id, issuer=ISSUER, leeway=5,
        options={'require': ['sub', 'exp', 'iat', 'nonce', 'iss', 'aud']})
    if (not isinstance(claims['sub'], str) or not claims['sub']
            or not isinstance(claims['nonce'], str)
            or not secrets.compare_digest(claims['nonce'], nonce)
            or ('azp' in claims and claims['azp'] != client_id)
            or (isinstance(claims['aud'], list) and len(claims['aud']) > 1
                and claims.get('azp') != client_id)):
        raise ValueError('Identity binding failed')
    if previous and (previous['client_id'] != client_id or previous['subject'] != claims['sub']):
        raise ValueError('Registered account changed')
    if tokens.get('token_type', '').lower() != 'bearer':
        raise ValueError('Bearer token required')
    scopes = tokens.get('scope', '').split()
    if not set(SCOPES.split()).issubset(scopes):
        raise ValueError('Required registration scopes missing')
    for name in ('access_token', 'refresh_token'):
        if not isinstance(tokens.get(name), str) or not tokens[name]:
            raise ValueError('Missing credential')
    if type(tokens.get('expires_in')) is not int or tokens['expires_in'] <= 0:
        raise ValueError('Invalid credential expiry')
    return dict(client_id=client_id, subject=claims['sub'], issuer=ISSUER,
        id_token=tokens['id_token'], access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'], scopes=scopes, token_type='Bearer',
        expires_at=int(time.time()) + tokens['expires_in'], saved_at=int(time.time()),
        dispatch_status='blocked', billing_ceiling_verified=False, model_requests=0)


def write_new(path, value):
    pending = path.with_name(path.name + '.' + secrets.token_hex(8) + '.pending')
    with pending.open('x', encoding='utf-8') as target:
        json.dump(value, target, allow_nan=False)
        target.flush()
        os.fsync(target.fileno())
    os.link(pending, path)  # Publish only complete bytes; never overwrite a prior record.
    pending.unlink()


def main():
    root = Path(__file__).resolve().parent
    if root.name != 'gold-plan-auth' or root.parent.name != '.batch3-vibe':
        raise ValueError('Run the private launcher snapshot')
    # Launcher establishes owner/SYSTEM-only ACLs before any credential exists.
    if (root / 'registration.json').exists():
        print('Registration already exists; no overwrite or request performed.', flush=True)
        return
    host_path = root / 'host.json'
    if not host_path.exists():
        write_new(host_path, {'id': 'urn:uuid:' + str(uuid.uuid4())})
    host_id = json.loads(host_path.read_text())['id']
    issued_path = root / 'issued-client.json'
    issued = json.loads(issued_path.read_text()) if issued_path.exists() else None
    transaction = create_transaction(host_id, issued)
    completed = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Callback URLs contain credentials; never log requests.

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def do_GET(self):
            nonlocal completed
            if self.headers.get('Host') != f'127.0.0.1:{PORT}' or len(self.path) > 16384:
                self.send_error(400, 'Invalid local request')
                return
            if self.path == '/' and not transaction['used']:
                self.send_response(302)
                self.send_header('Location', transaction['url'])
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                return
            if urlsplit(self.path).path != '/auth/callback':
                self.send_error(404)
                return
            message = b'Registration failed. No inference was sent. Return to Codex.'
            try:
                client_id, code = consume_callback(self.path, transaction)
                if not issued_path.exists():
                    write_new(issued_path, {'client_id': client_id})
                with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
                    tokens = read_json(client, 'POST', TOKEN, data=dict(
                        grant_type='authorization_code', client_id=client_id, code=code,
                        code_verifier=transaction['verifier'], redirect_uri=REDIRECT,
                        resource=RESOURCE))
                    keys = read_json(client, 'GET', JWKS)
                record = verify_tokens(tokens, keys, client_id, transaction['nonce'])
                record['ext_agent_host_id'] = host_id
                write_new(root / 'registration.json', record)
                write_new(root / 'receipt.json', dict(status='registered',
                    identity_signature_verified=True, model_requests=0,
                    billing_ceiling_verified=False, dispatch_status='blocked'))
                message = b'Registration saved. No credits enabled. No inference sent. Return to Codex.'
                print('Registration saved; signed identity verified; model_requests=0; dispatch=blocked.', flush=True)
                completed = True
            except Exception:
                # Never echo provider errors, tokens, codes or callback parameters.
                print('Registration failed; no credential details recorded in logs.', flush=True)
                completed = transaction['used']
            self.send_response(200 if message.startswith(b'Registration saved') else 400)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.end_headers()
            self.wfile.write(message)

    with HTTPServer(('127.0.0.1', PORT), Handler) as server:
        server.timeout = 1
        print(f'Registration ready at http://127.0.0.1:{PORT}/ (10-minute expiry).', flush=True)
        while not completed and time.monotonic() < transaction['expires']:
            server.handle_request()
    if not (root / 'registration.json').exists():
        raise ValueError('Registration incomplete')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Registration stopped; no inference or billing action performed.', flush=True)
        raise SystemExit(2) from None
