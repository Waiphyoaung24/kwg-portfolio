"""Sealed same-account renewal and model catalog. No inference or billing API."""
import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import ssl
import struct
import subprocess
import sys
import time
import uuid
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch3_runner import DOCKER, SANDBOX_IMAGE, write_once
from supported_gateway import PYTHON, SQUID_IMAGE, inspect_container, watchdog
from supported_oauth_transport import MODEL
from trusted_gateway import no_reparse, verify_seal
from trusted_oauth_transport import strict_json

ISSUER = 'https://auth.openai.com'
RESOURCE = 'https://api.openai.com/v1'
TOKEN = ISSUER+'/api/accounts/oauth/token'
JWKS = ISSUER+'/.well-known/jwks.json'
MODELS = RESOURCE+'/models'
SCOPES = set('openid profile email offline_access resource.invoke chatgpt.tokens.use.direct'.split())
BOUND = 262144
DEADLINE = 180
FILES = ('gold_account.py', 'supported_gateway.py', 'supported_oauth_transport.py',
         'trusted_gateway.py', 'trusted_oauth_transport.py', 'batch3_runner.py')
PROXY = '''http_port 3128
acl approved dstdomain -n auth.openai.com api.openai.com
acl tls_port port 443
acl private dst 0.0.0.0/8 10.0.0.0/8 100.64.0.0/10 127.0.0.0/8 169.254.0.0/16 172.16.0.0/12 192.168.0.0/16 224.0.0.0/4 240.0.0.0/4 ::/128 ::1/128 fc00::/7 fe80::/10 ff00::/8
http_access deny !CONNECT
http_access deny !approved
http_access deny !tls_port
http_access deny private
http_access allow CONNECT approved tls_port
http_access deny all
cache deny all
access_log none
cache_log /dev/null
cache_store_log none
pid_filename none
hosts_file /etc/hosts
visible_hostname kwg-gold-account
dns_nameservers 1.1.1.1 1.0.0.1
'''
POLICY = dict(mode='gold_account_only', worker_image=SANDBOX_IMAGE, proxy_image=SQUID_IMAGE,
    proxy_sha256=hashlib.sha256(PROXY.encode()).hexdigest(), worker_python=PYTHON,
    httpx='0.28.1', httpcore='1.0.9', certifi='2026.5.20', logging='none',
    deadline_seconds=DEADLINE, endpoints=[JWKS, TOKEN, MODELS], max_refresh_posts=1,
    max_catalog_gets=1, auth_max_bytes=BOUND, catalog_max_bytes=2097152,
    response_encodings=['identity','gzip'], model=MODEL, inference_dispatch='blocked', billing_ceiling_verified=False)


class AccountHTTPError(ValueError):
    def __init__(self,status):
        self.status=status
        super().__init__('Account HTTP refused')


class AccountResponseError(ValueError):
    def __init__(self,code):
        self.code=code
        super().__init__('Account response refused')


def request(client, operation, value=None):
    if operation == 'keys': method, url, options = 'GET', JWKS, {}
    elif operation == 'refresh':
        if (not isinstance(value, dict) or set(value) != {'client_id','refresh_token'}
                or not isinstance(value['client_id'], str) or not value['client_id'].startswith('oaiapp_')
                or not isinstance(value['refresh_token'], str) or not 0 < len(value['refresh_token']) <= 16384):
            raise ValueError('Invalid renewal input')
        method, url, options = 'POST', TOKEN, {'data': {**value, 'grant_type':'refresh_token', 'resource':RESOURCE}}
    elif operation == 'catalog':
        if not isinstance(value, str) or not 0 < len(value) <= 16384: raise ValueError('Invalid catalog input')
        method, url, options = 'GET', MODELS, {'headers': {'Authorization':'Bearer '+value}}
    else: raise ValueError('Account operation required')
    with client.stream(method, url, headers={**options.pop('headers', {}), 'Accept-Encoding':'identity'}, **options) as response:
        if response.status_code != 200: raise AccountHTTPError(response.status_code)
        encoding=response.headers.get('content-encoding','identity').lower()
        if encoding not in ('identity','gzip'): raise AccountResponseError('unsupported_encoding')
        limit=2097152 if operation=='catalog' else BOUND
        decoder=zlib.decompressobj(16+zlib.MAX_WBITS) if encoding=='gzip' else None
        raw=bytearray();wire=0
        for chunk in response.iter_raw(chunk_size=4096):
            wire+=len(chunk)
            if wire>limit: raise AccountResponseError('wire_limit')
            raw.extend(decoder.decompress(chunk,limit+1-len(raw)) if decoder else chunk)
            if len(raw)>limit or decoder and decoder.unconsumed_tail: raise AccountResponseError('decoded_limit')
        if decoder and (not decoder.eof or decoder.unused_data): raise AccountResponseError('invalid_gzip')
    try: result=strict_json(raw)
    except ValueError: raise AccountResponseError('invalid_json') from None
    if not isinstance(result,dict): raise AccountResponseError('object_required')
    return result


def jwt_claims(token, keys, audience, *, expired=False):
    import jwt  # Host already has PyJWT/cryptography; neither is added to the worker.
    header = jwt.get_unverified_header(token)
    if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str): raise ValueError('Signature refused')
    matches = [key for key in keys['keys'] if key.get('kid') == header['kid']]
    if len(matches) != 1: raise ValueError('Signing key ambiguous')
    claims = jwt.decode(token, jwt.PyJWK.from_dict(matches[0], algorithm='RS256').key,
        algorithms=['RS256'], audience=audience, issuer=ISSUER, leeway=5,
        options={'require':['sub','exp','iat','iss','aud'], 'verify_exp':not expired})
    if not isinstance(claims['sub'], str) or not claims['sub']: raise ValueError('Subject refused')
    return claims


def validate_saved(record, keys, issued, host):
    if (record['issuer'] != ISSUER or record['client_id'] != issued['client_id']
            or not record['client_id'].startswith('oaiapp_') or record['ext_agent_host_id'] != host['id']
            or record['dispatch_status'] != 'blocked' or record['billing_ceiling_verified'] is not False
            or record['model_requests'] != 0 or not SCOPES.issubset(record['scopes'])
            or type(record.get('expires_at')) is not int):
        raise ValueError('Saved registration binding refused')
    identity = jwt_claims(record['id_token'], keys, record['client_id'], expired=True)
    access = jwt_claims(record['access_token'], keys, RESOURCE, expired=True)
    if (identity['sub'] != record['subject'] or access['sub'] != record['subject']
            or access['client_id'] != record['client_id'] or identity.get('azp', record['client_id']) != record['client_id']
            or not SCOPES.issubset(access['scope'].split()) or type(access['exp']) is not int
            or abs(record['expires_at']-access['exp']) > 10
            or isinstance(identity['aud'],list) and len(identity['aud'])>1 and identity.get('azp')!=record['client_id']):
        raise ValueError('Saved signed account mismatch')
    return identity


def renewed_record(tokens, keys, previous, prior_identity):
    if (tokens.get('token_type', '').lower() != 'bearer' or type(tokens.get('expires_in')) is not int
            or not 300 < tokens['expires_in'] <= 7200 or not isinstance(tokens.get('scope'), str)
            or not SCOPES.issubset(tokens['scope'].split())
            or any(not isinstance(tokens.get(k), str) or not 0 < len(tokens[k]) <= 16384
                   for k in ('access_token','refresh_token','id_token'))):
        raise ValueError('Renewed credentials refused')
    identity = jwt_claims(tokens['id_token'], keys, previous['client_id'])
    access = jwt_claims(tokens['access_token'], keys, RESOURCE)
    if (identity['sub'] != previous['subject'] or access['sub'] != previous['subject']
            or access['client_id'] != previous['client_id'] or identity.get('azp', previous['client_id']) != previous['client_id']
            or ('nonce' in identity and identity['nonce'] != prior_identity.get('nonce'))
            or not SCOPES.issubset(access['scope'].split())
            or not time.time()+300 < access['exp'] <= time.time()+tokens['expires_in']+10):
        raise ValueError('Renewed signed account mismatch')
    if isinstance(identity['aud'], list) and len(identity['aud']) > 1 and identity.get('azp') != previous['client_id']:
        raise ValueError('Identity authorized party required')
    return {**previous, **{key:tokens[key] for key in ('access_token','refresh_token','id_token')},
        'scopes':tokens['scope'].split(), 'expires_at':int(access['exp']), 'saved_at':int(time.time())}


def catalog_matches(value):
    models = value.get('models')
    if not isinstance(models, list) or len(models) > 1000: raise ValueError('Plan catalog required')
    slugs = []
    for model in models:
        if (not isinstance(model, dict) or not isinstance(model.get('slug'), str)
                or not model['slug'] or len(model['slug']) > 256): raise ValueError('Catalog model refused')
        slugs.append(model['slug'])
    if len(slugs) != len(set(slugs)): raise ValueError('Duplicate catalog model')
    return MODEL in slugs


def probes(value):
    def denied(ip, port):
        try:
            with socket.create_connection((ip, port), timeout=.5): pass
            return False
        except OSError: return True
    result = {f'direct:{ip}':denied(ip, value['host_port']) for ip in value['host_ips']}
    result.update({f'peer:{ip}':denied(ip,443) for ip in value['peer_ips']})
    result.update(internet_ipv4=denied('1.1.1.1',443), internet_ipv6=denied('2606:4700:4700::1111',443))
    for target in ('example.com:443','auth.openai.com:444','auth.openai.com.evil.invalid:443',
                   'api.openai.com:444','127.0.0.1:443','host.docker.internal:443','[::1]:443'):
        with socket.create_connection(('kwg-egress',3128),timeout=2) as connection:
            connection.sendall(('CONNECT '+target+' HTTP/1.1\r\nHost: '+target+'\r\n\r\n').encode())
            result['proxy:'+target]=b' 403 ' in connection.recv(4096).split(b'\r\n')[0]
    with socket.create_connection(('kwg-egress',3128),timeout=2) as connection:
        connection.sendall(b'GET http://auth.openai.com/ HTTP/1.1\r\nHost: auth.openai.com\r\n\r\n')
        result['plain_http_denied']=b' 403 ' in connection.recv(4096).split(b'\r\n')[0]
    import httpx
    try:
        with httpx.Client(proxy='http://kwg-egress:3128',trust_env=False,verify=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT),timeout=10) as client:
            client.get(JWKS)
        result['untrusted_tls_denied']=False
    except httpx.ConnectError: result['untrusted_tls_denied']=True
    for name in ('example.com','auth.openai.com','api.openai.com','host.docker.internal'):
        try: socket.getaddrinfo(name,443); result['dns:'+name]=False
        except OSError: result['dns:'+name]=True
    query=struct.pack('!HHHHHH',123,0x100,1,0,0,0)+b'\x07example\x03com\x00\x00\x01\x00\x01'
    for resolver in ('127.0.0.11','8.8.8.8','1.1.1.1'):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as connection:
            connection.settimeout(.5)
            try:
                connection.sendto(query,(resolver,53));reply=connection.recv(4096)
                result['udp_dns:'+resolver]=len(reply)>=12 and struct.unpack('!H',reply[6:8])[0]==0
            except OSError: result['udp_dns:'+resolver]=True
    for path in ('/snapshot/code/gold_account.py','/tmp/kwg-canary'):
        try:
            with open(path,'ab') as output: output.write(b'CANARY')
            result['readonly:'+path]=False
        except OSError: result['readonly:'+path]=True
    for path in ('/var/run/docker.sock','/host','/fixture/ca.pem','/fixture/key.pem','/root/.codex/auth.json'):
        result['absent:'+path]=not Path(path).exists()
    result['no_default_ipv4']=not any(line.split()[1]=='00000000' for line in Path('/proc/net/route').read_text().splitlines()[1:])
    result['no_default_ipv6']=not any(line.split()[0]=='0'*32 and line.split()[1]=='00' and line.split()[-1]!='lo' for line in Path('/proc/net/ipv6_route').read_text().splitlines())
    return result


def worker():
    watchdog(DEADLINE)
    os.environ.clear()
    raw=sys.stdin.buffer.read(BOUND+1)
    if len(raw)>BOUND: raise ValueError('Worker input limit')
    value = strict_json(raw)
    if not isinstance(value, dict) or set(value) != {'operation','value'}: raise ValueError('Worker input refused')
    if any(importlib.metadata.version(name) != POLICY[name] for name in ('httpx','httpcore','certifi')):
        raise ValueError('Worker runtime refused')
    import httpx
    if value['operation']=='hold':
        if value['value']!='FAKE_CANARY_TERMINATION': raise ValueError('Synthetic termination input required')
        print('SYNTHETIC_INPUT_RECEIVED',flush=True)
        while True: time.sleep(.25)
    if value['operation'] == 'probes': result = probes(value['value'])
    else:
        os.environ.update(HTTPS_PROXY='http://127.0.0.1:1',HTTP_PROXY='http://127.0.0.1:1',ALL_PROXY='http://127.0.0.1:1',SSL_CERT_FILE='/not-a-trust-store')
        with httpx.Client(proxy='http://kwg-egress:3128',trust_env=False,verify=True,
                follow_redirects=False,timeout=httpx.Timeout(connect=10,read=30,write=10,pool=10)) as client:
            try: result = request(client,value['operation'],value['value'])
            except AccountHTTPError as error:
                print(json.dumps({'account_http_status':error.status}));raise SystemExit(2) from None
            except AccountResponseError as error:
                print(json.dumps({'account_response_failure':error.code,'account_http_status':200}));raise SystemExit(2) from None
            except Exception as error:
                print(json.dumps({'account_failure_kind':type(error).__name__}));raise SystemExit(2) from None
        if value['operation']=='catalog':
            present=catalog_matches(result)
            result={'required_model_present':present,'catalog_models_count':len(result['models']),
                    'available_models':[model['slug'] for model in result['models']],
                    'catalog_sha256':hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    raw = json.dumps(result,allow_nan=False).encode()
    if len(raw) > BOUND: raise ValueError('Worker result limit')
    sys.stdout.buffer.write(raw)


def cleanup_guard(attempt, parent):
    owned = strict_json((attempt/'owned.json').read_bytes())
    if owned.get('policy')!=POLICY or set(owned)!= {'containers','networks','policy'}:
        raise ValueError('Guardian ownership policy refused')
    docker = [str(DOCKER),'--config',str(attempt/'docker-config'),'-H','npipe:////./pipe/dockerDesktopLinuxEngine']
    env = {k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR'}}
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype = ctypes.c_void_p
    handle = kernel.OpenProcess(0x100000,False,parent)
    if not handle: raise ValueError('Controller handle unavailable')
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p,ctypes.c_ulong]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    deadline = time.monotonic()+DEADLINE
    write_once(attempt/'guard-ready.json',{'pid':os.getpid()})
    try:
        while time.monotonic()<deadline and not (attempt/'finished.json').exists():
            if kernel.WaitForSingleObject(handle,250)==0: break
        remaining = time.monotonic()+30
        clean = []
        for group,remove,listing in (('containers',['rm','-f','-v'],['ps','-a']),('networks',['network','rm'],['network','ls'])):
            for name in owned[group].values():
                try:
                    budget=min(5,remaining-time.monotonic())
                    if budget<=0: raise ValueError('Cleanup deadline')
                    subprocess.run([*docker,*remove,name],env=env,capture_output=True,timeout=budget)
                    exact=('^'+name+'$') if group=='networks' else ('^/'+name+'$')
                    absent=subprocess.run([*docker,*listing,'--filter','name='+exact,'--format','{{.Name}}' if group=='networks' else '{{.Names}}'],env=env,capture_output=True,timeout=max(.1,min(5,remaining-time.monotonic())))
                    clean.append(absent.returncode==0 and not absent.stdout.strip())
                except (OSError,ValueError,subprocess.SubprocessError): clean.append(False)
        write_once(attempt/'cleanup.json',{'cleanup_verified':all(clean),'guard_independent':True})
    finally: kernel.CloseHandle(handle)


def private_acl(path):
    no_reparse(path)
    # Native ACL verification in owner context; never prints file contents or ACL identities.
    script = "$p=$args[0];$a=Get-Acl -LiteralPath $p;$o=[Security.Principal.NTAccount]::new('KWG-Beast','wai19').Translate([Security.Principal.SecurityIdentifier]);$s=[Security.Principal.SecurityIdentifier]::new('S-1-5-18');if($a.GetOwner([Security.Principal.SecurityIdentifier]) -ne $o -or ((Get-Item -LiteralPath $p).PSIsContainer -and -not $a.AreAccessRulesProtected)){exit 2};$seen=@();foreach($r in $a.Access){$sid=$r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]);if($r.AccessControlType -ne 'Allow' -or $sid -notin @($o,$s) -or $r.FileSystemRights -ne 'FullControl'){exit 2};$seen+=$sid.Value};if($o.Value -notin $seen -or $s.Value -notin $seen){exit 2}"
    encoded = __import__('base64').b64encode((script.replace('$args[0]',"'"+str(path).replace("'","''")+"'")).encode('utf-16le')).decode()
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR'}}
    checked = subprocess.run(['C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],env=env,capture_output=True,timeout=10)
    if checked.returncode: raise ValueError('Private ACL refused')


def atomic_publish(path, expected, record):
    no_reparse(path)
    if path.read_bytes()!=expected: raise ValueError('Concurrent registration change')
    pending=path.with_name('registration.'+uuid.uuid4().hex+'.pending')
    write_once(pending,record)
    private_acl(pending)
    if path.read_bytes()!=expected: raise ValueError('Concurrent registration change')
    os.replace(pending,path)
    private_acl(path)


def run(seal_sha, mode):
    sealed=Path(__file__).resolve().parent.parent
    if Path(__file__).parent.name!='code' or not sealed.name.startswith('sealed-account-') or sealed.parent.name!='.batch3-vibe':
        raise ValueError('Sealed account entry required')
    verify_seal(sealed,seal_sha)
    metadata=strict_json((sealed/'readiness.json').read_bytes())
    if (metadata.get('policy')!=POLICY or metadata.get('mode')!='gold_account_only'
            or sealed.name!='sealed-account-'+metadata['git_commit'][:12]
            or metadata.get('production_registry')!=str(sealed.parent/'production-attempts')
            or metadata.get('production_dispatch')!='blocked'
            or any(metadata.get(k) is not False for k in ('production_isolation_verified','server_account_verified','billing_ceiling_verified'))):
        raise ValueError('Account policy refused')
    review=sealed.parent/'account-readiness'; no_reparse(review); private_acl(review)
    if mode=='accept':
        for check in ('boundary','termination'):
            result=strict_json((review/(seal_sha+'.'+check)/'receipt.json').read_bytes())
            if not result.get('passed') or result.get('seal_sha256')!=seal_sha: raise ValueError('Boundary acceptance required')
    attempt=review/(seal_sha+'.'+mode); attempt.mkdir()
    for folder in ('docker-config','empty'): (attempt/folder).mkdir()
    (attempt/'squid.conf').write_text(PROXY)
    prefix='kwg-account-'+uuid.uuid4().hex
    names={role:prefix+'-'+role for role in ('proxy','probe','keys','refresh','catalog','control','peer','peer-control')}
    nets={role:prefix+'-'+role for role in ('inner','outer')}
    write_once(attempt/'owned.json',{'containers':names,'networks':nets,'policy':POLICY})
    docker=[str(DOCKER),'--config',str(attempt/'docker-config'),'-H','npipe:////./pipe/dockerDesktopLinuxEngine']
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR'}}
    began=time.monotonic()
    def command(*args,check=True,**options):
        budget=DEADLINE-(time.monotonic()-began)
        if budget<=0: raise ValueError('Controller deadline')
        return subprocess.run([*docker,*args],env=env,capture_output=True,timeout=budget,check=check,**options)
    def create(role,image,network,entry,args,mounts,dns=()):
        masks=('/var/log/squid','/var/spool/squid') if image==SQUID_IMAGE else ('/etc/searxng','/var/cache/searxng')
        mounts=[*mounts,*((attempt/'empty',target) for target in masks)]
        cmd=['create','--name',names[role],'--pull','never','--log-driver','none','--network',network,'--read-only',
             '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','32','--memory','128m','--cpus','1',
             '--user','13:13' if image==SQUID_IMAGE else '65534:65534','-i','--entrypoint',entry]
        for source,target in mounts: cmd+=['--mount',f'type=bind,source={source},target={target},readonly']
        for address in dns: cmd+=['--dns',address]
        if role=='proxy': cmd+=['--network-alias','kwg-egress']
        command(*cmd,image,*args)
        state=strict_json(command('inspect',names[role]).stdout)[0]
        inspect_container(state,image,network,entry,args,mounts,{'dns':list(dns)})
        if state['HostConfig']['LogConfig']['Type']!='none' or state['HostConfig'].get('CapAdd') or state['HostConfig']['RestartPolicy']['Name']!='no':
            raise ValueError('Credential logging/restart refused')
    def create_worker(role):
        args=['-I','-B','-c',"import sys;sys.path.insert(0,'/snapshot/code');from gold_account import worker\ntry: worker()\nexcept Exception: sys.exit(2)"]
        create(role,SANDBOX_IMAGE,nets['inner'],PYTHON,args,[(sealed/'code'/name,'/snapshot/code/'+name) for name in FILES],['127.0.0.1'])
        state=strict_json(command('inspect',names[role]).stdout)[0]
        if set(state['NetworkSettings']['Networks'])!={nets['inner']}: raise ValueError('Worker extra network')
    def exchange(role,operation,value=None):
        create_worker(role)
        raw=json.dumps({'operation':operation,'value':value},allow_nan=False).encode()
        if len(raw)>BOUND: raise ValueError('Credential input limit')
        process=command('start','-a','-i',names[role],input=raw,check=False)
        output=process.stdout
        if len(output)>BOUND: raise ValueError('Worker result limit')
        if process.returncode:
            error=strict_json(output) if output else {}
            receipt['failed_operation']=operation
            if set(error)=={'account_http_status'} and type(error['account_http_status']) is int and 100<=error['account_http_status']<=599:
                receipt['account_http_status']=error['account_http_status']
            elif set(error)=={'account_response_failure','account_http_status'} and error['account_http_status']==200 and error['account_response_failure'] in ('unsupported_encoding','wire_limit','decoded_limit','invalid_gzip','invalid_json','object_required'):
                receipt.update(account_http_status=200,account_response_failure=error['account_response_failure'])
            elif set(error)=={'account_failure_kind'} and error['account_failure_kind'] in ('ValueError','ConnectError','ConnectTimeout','ReadTimeout','WriteTimeout','PoolTimeout','RemoteProtocolError'):
                receipt['account_failure_kind']=error['account_failure_kind']
            raise ValueError('Account worker refused')
        return strict_json(output)
    guard=subprocess.Popen([sys.executable,'-I','-S','-B',str(sealed/'code/gold_account.py'),'--seal-sha256',seal_sha,
        '--guard',str(attempt),'--parent',str(os.getpid())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS,close_fds=True)
    receipt=dict(mode=mode,seal_sha256=seal_sha,passed=False,model_requests=0,dispatch_status='blocked',
        production_isolation_verified=False,server_account_verified=False,billing_ceiling_verified=False)
    service=None
    try:
        for _ in range(100):
            if (attempt/'guard-ready.json').exists(): break
            if guard.poll() is not None: raise ValueError('Cleanup guardian unavailable')
            time.sleep(.05)
        else: raise ValueError('Cleanup guardian not ready')
        command('network','create','--internal','--ipv6','-o','com.docker.network.bridge.gateway_mode_ipv4=isolated',
                '-o','com.docker.network.bridge.gateway_mode_ipv6=isolated',nets['inner'])
        command('network','create','--ipv6',nets['outer'])
        state=strict_json(command('network','inspect',nets['inner']).stdout)[0]
        if not state['Internal'] or not state['EnableIPv6'] or any(state['Options'].get('com.docker.network.bridge.gateway_mode_'+v)!='isolated' for v in ('ipv4','ipv6')):
            raise ValueError('Inner network refused')
        outer=strict_json(command('network','inspect',nets['outer']).stdout)[0]
        if outer['Internal'] or not outer['EnableIPv6'] or outer['Driver']!='bridge': raise ValueError('Outer network refused')
        create('proxy',SQUID_IMAGE,nets['inner'],'/usr/bin/timeout',[str(DEADLINE),'/usr/sbin/squid','-N','-f','/etc/squid/squid.conf'],[(attempt/'squid.conf','/etc/squid/squid.conf')],['1.1.1.1','1.0.0.1'])
        command('network','connect',nets['outer'],names['proxy'])
        state=strict_json(command('inspect',names['proxy']).stdout)[0]
        if set(state['NetworkSettings']['Networks'])!=set(nets.values()): raise ValueError('Proxy extra network')
        command('start',names['proxy'])
        if mode in ('boundary','termination'):
            from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
            import threading
            class Handler(BaseHTTPRequestHandler):
                def log_message(self,*args): pass
                def do_GET(self):
                    self.send_response(200);self.end_headers();self.wfile.write(b'CANARY')
            service=ThreadingHTTPServer(('0.0.0.0',0),Handler)
            threading.Thread(target=service.serve_forever,daemon=True).start()
            port=service.server_address[1]
            control="import socket,json,urllib.request;ips=sorted({a[4][0] for a in socket.getaddrinfo('host.docker.internal',0,type=socket.SOCK_STREAM)});assert urllib.request.urlopen('http://host.docker.internal:"+str(port)+"/',timeout=2).read()==b'CANARY';socket.create_connection(('1.1.1.1',443),timeout=2).close();print(json.dumps(ips))"
            create('control',SANDBOX_IMAGE,'bridge','/usr/sbin/python3',['-I','-S','-B','-c',control],[])
            ips=strict_json(command('start','-a',names['control']).stdout)
            create('peer',SANDBOX_IMAGE,nets['outer'],'/usr/sbin/python3',['-I','-S','-B','-c',"import socket,time;s=socket.socket();s.bind(('0.0.0.0',443));s.listen();time.sleep(180)"],[])
            command('start',names['peer'])
            peer=strict_json(command('inspect',names['peer']).stdout)[0]['NetworkSettings']['Networks'][nets['outer']]['IPAddress']
            create('peer-control',SANDBOX_IMAGE,nets['outer'],'/usr/sbin/python3',['-I','-S','-B','-c',"import socket;socket.create_connection(("+repr(peer)+",443),timeout=2).close();print('PEER_OK')"],[])
            if command('start','-a',names['peer-control']).stdout.strip()!=b'PEER_OK': raise ValueError('Peer positive control failed')
            checked=exchange('probe','probes',{'host_ips':ips,'host_port':port,'peer_ips':[peer]})
            if not checked or any(value is not True for value in checked.values()): raise ValueError('Isolation probe failed')
            keys=exchange('keys','keys')
            if not isinstance(keys.get('keys'),list) or not keys['keys']: raise ValueError('Public TLS keys failed')
            receipt.update(probes=checked,public_tls_verified=True,host_internet_positive_control=True)
            if mode=='termination':
                create_worker('refresh')
                attached=subprocess.Popen([*docker,'start','-a','-i',names['refresh']],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                attached.stdin.write(json.dumps({'operation':'hold','value':'FAKE_CANARY_TERMINATION'}).encode());attached.stdin.close()
                if attached.stdout.readline().strip()!=b'SYNTHETIC_INPUT_RECEIVED': raise ValueError('Synthetic transfer not verified')
                receipt['synthetic_input_transferred']=True
                write_once(attempt/'kill-ready.json',receipt)
                while True: time.sleep(.25)  # External test kills this controller; independent guardian owns cleanup.
            receipt['passed']=True
        else:
            auth=sealed.parent/'gold-plan-auth'; private_acl(auth)
            for name in ('registration.json','issued-client.json','host.json','receipt.json'): private_acl(auth/name)
            import msvcrt
            with (auth/'registration.lock').open('a+b') as lock:
                lock.seek(0)
                if not lock.read(1): lock.write(b'0');lock.flush()
                lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                old=(auth/'registration.json').read_bytes(); previous=strict_json(old)
                if len(old)>BOUND: raise ValueError('Private input limit')
                identity=hashlib.sha256(old).hexdigest()
                # This marker survives controller death and consumes a potentially rotating grant.
                marker=auth/('renewal-'+identity+'.started.json')
                if marker.exists(): raise ValueError('Consumed renewal must not repeat')
                keys=exchange('keys','keys')
                prior=validate_saved(previous,keys,strict_json((auth/'issued-client.json').read_bytes()),strict_json((auth/'host.json').read_bytes()))
                if previous['expires_at']<=time.time()+300:
                    write_once(attempt/'previous-registration.private.json',previous)
                    write_once(marker,{'seal_sha256':seal_sha,'state':'outcome_unknown','model_requests':0})
                    tokens=exchange('refresh','refresh',{'client_id':previous['client_id'],'refresh_token':previous['refresh_token']})
                    write_once(attempt/'renewed-unvalidated.private.json',tokens)
                    updated=renewed_record(tokens,keys,previous,prior)
                    atomic_publish(auth/'registration.json',old,updated)
                    write_once(auth/('renewal-'+identity+'.completed.json'),{'seal_sha256':seal_sha,'published':True,'model_requests':0})
                    receipt['renewal_completed']=True
                else: updated=previous; receipt['renewal_completed']=False
                if updated['expires_at']<=time.time()+300: raise ValueError('Fresh access required')
                catalog=exchange('catalog','catalog',updated['access_token'])
                if (set(catalog)!= {'required_model_present','catalog_models_count','catalog_sha256','available_models'}
                        or type(catalog['required_model_present']) is not bool or type(catalog['catalog_models_count']) is not int
                        or not 0<=catalog['catalog_models_count']<=1000 or not isinstance(catalog['catalog_sha256'],str)
                        or len(catalog['catalog_sha256'])!=64
                        or not isinstance(catalog['available_models'],list) or len(catalog['available_models'])!=catalog['catalog_models_count']
                        or any(not isinstance(slug,str) or not 0<len(slug)<=256 for slug in catalog['available_models'])):
                    raise ValueError('Catalog summary refused')
                present=catalog['required_model_present']
                receipt.update(catalog_models_count=catalog['catalog_models_count'],catalog_sha256=catalog['catalog_sha256'],available_models=catalog['available_models'])
                receipt.update(server_account_verified=True,required_model_present=present,production_isolation_verified=True,passed=present)
    except Exception as error:
        receipt['failure_kind']=type(error).__name__
    finally:
        if service is not None: service.shutdown();service.server_close()
        write_once(attempt/'finished.json',{'finished':True})
        limit=time.monotonic()+35
        while not (attempt/'cleanup.json').exists() and time.monotonic()<limit: time.sleep(.1)
        receipt['cleanup_verified']=(attempt/'cleanup.json').exists() and strict_json((attempt/'cleanup.json').read_bytes()).get('cleanup_verified') is True
        receipt['passed']=receipt['passed'] and receipt['cleanup_verified']
        write_once(attempt/'receipt.json',receipt)
    return receipt


def termination_check(seal_sha):
    sealed=Path(__file__).resolve().parent.parent
    verify_seal(sealed,seal_sha)
    attempt=sealed.parent/'account-readiness'/(seal_sha+'.termination')
    if attempt.exists(): raise FileExistsError('Preserve consumed termination test')
    process=subprocess.Popen([sys.executable,'-I','-S','-B',str(sealed/'code/gold_account.py'),
        '--seal-sha256',seal_sha,'--mode','termination'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+150
    try:
        while time.monotonic()<deadline and not (attempt/'kill-ready.json').exists():
            if process.poll() is not None: raise ValueError('Termination setup refused')
            time.sleep(.1)
        if not (attempt/'kill-ready.json').exists(): raise ValueError('Termination setup deadline')
        before=strict_json((attempt/'kill-ready.json').read_bytes())
        if not before.get('synthetic_input_transferred') or not before.get('public_tls_verified'):
            raise ValueError('Termination transfer not ready')
        process.terminate()  # Windows TerminateProcess: the controller cannot run finally cleanup.
        process.wait(timeout=10)
        deadline=time.monotonic()+35
        while not (attempt/'cleanup.json').exists() and time.monotonic()<deadline: time.sleep(.1)
        cleanup=strict_json((attempt/'cleanup.json').read_bytes())
        result={**before,'forced_termination_verified':True,'cleanup_verified':cleanup['cleanup_verified'],
                'passed':cleanup['cleanup_verified'] is True,'controller_exit':process.returncode}
        write_once(attempt/'receipt.json',result)
        return result
    finally:
        if process.poll() is None: process.terminate();process.wait(timeout=10)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal-sha256',required=True)
    parser.add_argument('--mode',choices=('boundary','termination','verify-termination','accept'))
    parser.add_argument('--guard');parser.add_argument('--parent',type=int)
    args=parser.parse_args()
    try:
        if args.guard:
            sealed=Path(__file__).resolve().parent.parent
            verify_seal(sealed,args.seal_sha256)
            path=Path(args.guard)
            if path.parent!=sealed.parent/'account-readiness' or path.name not in {args.seal_sha256+'.'+mode for mode in ('boundary','termination','accept')}:
                raise ValueError('Fixed guardian attempt required')
            cleanup_guard(path,args.parent)
        else:
            if args.mode is None: raise ValueError('Account mode required')
            result=termination_check(args.seal_sha256) if args.mode=='verify-termination' else run(args.seal_sha256,args.mode)
            print(json.dumps(result,sort_keys=True))
            if not result['passed']: raise SystemExit(2)
    except Exception:
        print('Account check refused; preserve attempts and credentials.',file=sys.stderr)
        raise SystemExit(2) from None
