"""Sealed supported-route rehearsal. Synthetic credentials and local TLS only."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import uuid

from batch3_runner import DEADLINE, DOCKER, MAX_BYTES, SANDBOX_IMAGE, research_module, write_once
from supported_oauth_transport import MODEL, invoke_fake
from trusted_gateway import no_reparse, reserve, verify_seal
from trusted_oauth_transport import strict_json

SQUID_IMAGE = 'ubuntu/squid@sha256:6a097f68bae708cedbabd6188d68c7e2e7a38cedd05a176e1cc0ba29e3bbe029'
PYTHON = '/usr/local/searxng/.venv/bin/python'
CASES = {'success', '401', 'account_mismatch', 'client_mismatch', 'expired', 'missing',
         'bad_usage', 'redirect', 'truncated', 'malformed', 'timeout', 'trickle', 'crash', 'interrupt'}
BINDING = {'issuer': 'https://auth.openai.com', 'subject': 'batch3-supported-fixture', 'client_id': 'oaiapp_fixture'}
BINDING_SHA = hashlib.sha256(json.dumps(BINDING, sort_keys=True).encode()).hexdigest()
CODE_FILES = ('supported_gateway.py', 'supported_oauth_transport.py', 'trusted_gateway.py',
              'trusted_oauth_transport.py', 'batch3_runner.py')
PARSER_FILES = (*CODE_FILES, 'research-gold.py', 'gold_experiment.py', 'gold_signal.py')
MAX_OUTPUT = 65536
SQUID_CONFIG = '''http_port 3128
acl provider dstdomain -n api.openai.com
acl tls_port port 443
http_access allow CONNECT provider tls_port
http_access deny all
cache deny all
access_log none
cache_log /dev/null
cache_store_log none
pid_filename none
hosts_file /etc/hosts
visible_hostname kwg-supported-fake
'''
POLICY = {'mode': 'supported_fake_only', 'url': 'https://api.openai.com/v1/responses', 'model': MODEL,
          'worker_image': SANDBOX_IMAGE, 'proxy_image': SQUID_IMAGE, 'worker_python': PYTHON,
          'httpx': '0.28.1', 'httpcore': '1.0.9', 'certifi': '2026.5.20',
          'network': 'internal_dual_stack_isolated', 'dns_upstream': '127.0.0.1',
          'proxy_config_sha256': hashlib.sha256(SQUID_CONFIG.encode()).hexdigest(),
          'max_posts': 1, 'deadline_seconds': DEADLINE, 'production_dispatch': 'blocked'}


def fake_binding(record):
    if (not isinstance(record, dict) or set(record) != {*BINDING, 'access_token', 'expires_at'}
            or any(record[k] != v for k, v in BINDING.items())
            or record['access_token'] != 'FAKE_CANARY_ACCESS'
            or type(record['expires_at']) not in (int, float) or not time.time()+300 < record['expires_at'] < time.time()+7200):
        raise ValueError('Synthetic binding refused')
    return BINDING_SHA


def watchdog(seconds):
    if not sys.flags.isolated or os.getuid() != 65534 or type(seconds) is not int or not 0 < seconds <= DEADLINE:
        raise ValueError('Worker isolation required')
    signal.signal(signal.SIGALRM, lambda *_: os._exit(2))
    signal.alarm(seconds)  # Explicit handler is required for container PID1.


def worker():
    watchdog(DEADLINE)
    os.environ.clear()
    raw = sys.stdin.buffer.read(MAX_OUTPUT+1)
    if len(raw) > MAX_OUTPUT: raise ValueError('Worker input limit')
    payload = strict_json(raw)
    if not isinstance(payload, dict) or set(payload) != {'case', 'record', 'binding_sha256', 'prompt', 'probe'}:
        raise ValueError('Invalid worker input')
    case = payload['case']
    if case not in CASES or payload['binding_sha256'] != fake_binding(payload['record']):
        raise ValueError('Synthetic binding refused')
    if any(importlib.metadata.version(name) != POLICY[name] for name in ('httpx', 'httpcore', 'certifi')):
        raise ValueError('Runtime dependency mismatch')
    if case == 'crash': os._exit(3)
    if case in ('timeout', 'trickle'): watchdog(3)
    import httpx
    context = ssl.create_default_context(cafile='/fixture/ca.pem')
    def client(**options):
        if options['verify'] is not True: raise ValueError('TLS verification required')
        options['verify'] = context  # Sealed fake mode only; the fake CA has no production entry.
        return httpx.Client(**options)
    probes = probe_worker(payload['probe']) if case == 'success' else None
    os.environ.update(HTTPS_PROXY='http://127.0.0.1:1', HTTP_PROXY='http://127.0.0.1:1',
                      ALL_PROXY='http://127.0.0.1:1', SSL_CERT_FILE='/not-a-trust-store')
    try:
        result = invoke_fake(payload['prompt'], payload['record']['access_token'],
                             SimpleNamespace(Client=client, Timeout=httpx.Timeout), 'http://kwg-egress:3128')
        status = 'completed_transport'
    except ValueError:
        result = None; status = 'transport_failed'
    output = json.dumps({'status': status, 'binding_sha256': BINDING_SHA, 'result': result, 'probes': probes}, ensure_ascii=False)
    if len(output.encode()) > MAX_OUTPUT: raise ValueError('Worker output limit')
    print(output)


def parse_worker():
    watchdog(DEADLINE)
    os.environ.clear()
    raw = sys.stdin.buffer.read(MAX_OUTPUT+1)
    if len(raw) > MAX_OUTPUT: raise ValueError('Parser input limit')
    value = strict_json(raw)
    if not isinstance(value, dict) or set(value) != {'text'}: raise ValueError('Credential-free parser input required')
    print(json.dumps(research_module().parse_proposal(value['text'].encode()), ensure_ascii=False))


def server(case):
    watchdog(DEADLINE)
    if strict_json(Path('/fixture/tls.json').read_bytes()) != {'mode': 'fake_only'}:
        raise ValueError('Fake TLS mode required')
    class Server(ThreadingHTTPServer):
        address_family = socket.AF_INET6
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_OUTPUT: return
            body = strict_json(self.rfile.read(size))
            if (self.path != '/v1/responses' or self.headers.get('Authorization') != 'Bearer FAKE_CANARY_ACCESS'
                    or body != {'model': MODEL, 'reasoning': {'effort': 'medium'}, 'input': [{'role': 'user', 'content': body['input'][0]['content']}],
                                'store': False, 'stream': True}):
                raise ValueError('Unexpected fake request')
            print('FAKE_POST', flush=True)
            self.send_response(401 if case == '401' else 302 if case == 'redirect' else 200)
            self.send_header('Content-Type', 'text/event-stream')
            if case == 'redirect': self.send_header('Location', 'https://example.com/forbidden')
            self.end_headers()
            if case in ('401', 'redirect'): return
            if case == 'timeout': time.sleep(DEADLINE); return
            if case == 'trickle':
                try:
                    for _ in range(DEADLINE*5):
                        self.wfile.write(b': heartbeat\n\n'); self.wfile.flush(); time.sleep(.2)
                except OSError: pass
                return
            if case == 'malformed': self.wfile.write(b'data: {malformed}\n\n'); return
            text = json.dumps({'kind': 'ema20_slope_filter', 'lookback_bars': 3, 'hypothesis': 'Synthetic sealed TLS fixture'})
            events = [{'type': 'response.output_text.delta', 'delta': text}]
            if case != 'truncated':
                events.append({'type': 'response.completed', 'response': {'id': 'fake-response', 'model': MODEL, 'status': 'completed',
                    'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed', 'content': [{'type': 'output_text', 'text': text}]}],
                    'usage': None if case == 'bad_usage' else {'input_tokens': 10, 'output_tokens': 3000, 'total_tokens': 3010}}})
            self.wfile.write(''.join('data: '+json.dumps(e)+'\n\n' for e in events).encode())
    service = Server(('::', 443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('/fixture/cert.pem', '/fixture/key.pem')
    service.socket = context.wrap_socket(service.socket, server_side=True)
    service.serve_forever()


def probe_worker(value):
    def denied(ip, port):
        try:
            with socket.create_connection((ip, port), timeout=.5): pass
            return False
        except OSError: return True
    result = {}
    for ip in value['host_ips']:
        result['host:'+ip] = denied(ip, value['host_port'])
    for ip in value['server_ips']:
        result['direct_server:'+ip] = denied(ip, 443)
    result['direct_internet_ipv4'] = denied('1.1.1.1', 443)
    result['direct_internet_ipv6'] = denied('2606:4700:4700::1111', 443)
    for target in ('example.com:443', 'api.openai.com:444', 'api.openai.com.evil.invalid:443',
                   value['server_ips'][0]+':443', 'host.docker.internal:443', '[::1]:443'):
        with socket.create_connection(('kwg-egress', 3128), timeout=2) as connection:
            connection.sendall(('CONNECT '+target+' HTTP/1.1\r\nHost: '+target+'\r\n\r\n').encode())
            result['proxy:'+target] = b' 403 ' in connection.recv(4096).split(b'\r\n')[0]
    with socket.create_connection(('kwg-egress', 3128), timeout=2) as connection:
        connection.sendall(b'GET http://api.openai.com/ HTTP/1.1\r\nHost: api.openai.com\r\n\r\n')
        result['plain_http_denied'] = b' 403 ' in connection.recv(4096).split(b'\r\n')[0]
    import httpx
    try:
        with httpx.Client(proxy='http://kwg-egress:3128', trust_env=False, timeout=2) as client:
            client.get('https://api.openai.com/')
        result['untrusted_tls_denied'] = False
    except httpx.ConnectError: result['untrusted_tls_denied'] = True
    for name in ('example.com', 'api.openai.com', 'host.docker.internal'):
        try: socket.getaddrinfo(name, 443); result['dns:'+name] = False
        except OSError: result['dns:'+name] = True
    query = struct.pack('!HHHHHH', 123, 0x100, 1, 0, 0, 0)+b'\x07example\x03com\x00\x00\x01\x00\x01'
    for resolver in ('127.0.0.11', '192.168.65.7', '8.8.8.8'):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.settimeout(.5)
            try:
                connection.sendto(query, (resolver, 53))
                reply = connection.recv(4096)
                result['udp_dns:'+resolver] = len(reply) >= 12 and struct.unpack('!H', reply[6:8])[0] == 0
            except OSError: result['udp_dns:'+resolver] = True
    for path in ('/snapshot/code/supported_gateway.py', '/tmp/kwg-write-canary'):
        try:
            with open(path, 'ab') as output: output.write(b'CANARY')
            result['readonly:'+path] = False
        except OSError: result['readonly:'+path] = True
    for path in ('/var/run/docker.sock', '/host', '/root/.codex/auth.json', '/fixture/key.pem', '/fixture/tls.json'):
        result['absent:'+path] = not Path(path).exists()
    result['no_ipv4_default_route'] = not any(line.split()[1] == '00000000' for line in Path('/proc/net/route').read_text().splitlines()[1:])
    result['no_ipv6_default_route'] = not any(line.split()[0] == '0'*32 and line.split()[1] == '00' and line.split()[-1] != 'lo'
        for line in Path('/proc/net/ipv6_route').read_text().splitlines())
    return result


def inspect_container(state, image, network, entry, args, mounts, extras):
    host = state['HostConfig']
    expected = {(os.path.normcase(os.path.normpath(str(source))), target) for source, target in mounts}
    actual = {(os.path.normcase(os.path.normpath(m['Source'])), m['Target']) for m in host['Mounts']}
    if (state['Image'] != image.split('@')[-1] or state['Config']['User'] != ('13:13' if image == SQUID_IMAGE else '65534:65534')
            or state['Config']['Entrypoint'] != [entry] or state['Config']['Cmd'] != args
            or host['NetworkMode'] != network or not host['ReadonlyRootfs'] or host['Privileged']
            or host['CapDrop'] != ['ALL'] or 'no-new-privileges' not in host['SecurityOpt']
            or host['PidsLimit'] != 32 or host['Memory'] != 134217728 or host['NanoCpus'] != 1000000000
            or actual != expected or len(host['Mounts']) != len(mounts) or len(state['Mounts']) != len(mounts)
            or {m['Destination'] for m in state['Mounts']} != {target for _, target in mounts}
            or any(m['Type'] != 'bind' or not m['ReadOnly'] for m in host['Mounts'])
            or any(m['Type'] != 'bind' or m['RW'] for m in state['Mounts'])
            or host.get('PortBindings') or (host.get('ExtraHosts') or []) != extras.get('hosts', [])
            or (host.get('Dns') or []) != extras.get('dns', [])):
        raise ValueError('Supported container configuration mismatch')
    return {'image': state['Image'], 'user': state['Config']['User'], 'network': network,
            'entrypoint': entry, 'mounts': sorted(target for _, target in mounts),
            'readonly': True, 'dns': host['Dns'], 'cap_drop': host['CapDrop']}


def rehearse(sealed, seal_sha, registry, packet, case):
    verify_seal(sealed, seal_sha)
    if case not in CASES: raise ValueError('Unknown fake case')
    attempt = reserve(registry, packet, seal_sha, case, supported=True)
    for folder in ('docker-config', 'empty', 'fixture'): (attempt/folder).mkdir()
    tls = strict_json((sealed/'code/batch3-supported-tls.json').read_bytes())
    for name in ('cert', 'key'):
        with (attempt/'fixture'/f'{name}.pem').open('x') as output: output.write(tls[name])
    with (attempt/'fixture/ca.pem').open('x') as output: output.write(tls['cert'])
    write_once(attempt/'fixture/tls.json', {'mode': 'fake_only'})
    with (attempt/'fixture/squid.conf').open('x') as output: output.write(SQUID_CONFIG)
    prefix = 'kwg-supported-'+uuid.uuid4().hex
    names = {role: prefix+'-'+role for role in ('server', 'proxy', 'worker', 'parser', 'control', 'control6')}
    nets = {role: prefix+'-'+role for role in ('inner', 'outer')}
    write_once(attempt/'owned.json', {'containers': names, 'networks': nets, 'policy': POLICY})
    receipt = {'case': case, 'state': 'reserved', 'model_requests': 0, 'dispatch_status': 'blocked',
        'production_isolation_verified': False, 'server_account_verified': False, 'billing_ceiling_verified': False,
        'packet_sha256': research_module().digest(packet), 'seal_sha256': seal_sha,
        'policy': POLICY, 'binding_sha256': BINDING_SHA, 'configuration_verified': False, 'cleanup_verified': False}
    docker = [str(DOCKER), '--config', str(attempt/'docker-config'), '-H', 'npipe:////./pipe/dockerDesktopLinuxEngine']
    env = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT', 'WINDIR'}}
    started = time.monotonic()
    def command(*args, check=True, **options):
        remaining = DEADLINE-(time.monotonic()-started)
        if remaining <= 0: raise subprocess.TimeoutExpired(args, DEADLINE)
        return subprocess.run([*docker, *args], env=env, capture_output=True, timeout=remaining, check=check, **options)
    def create(role, image, network, entry, args, mounts, *, hosts=(), dns=()):
        masks = ('/var/log/squid', '/var/spool/squid') if image == SQUID_IMAGE else ('/etc/searxng', '/var/cache/searxng')
        mounts = [*mounts, *((attempt/'empty', path) for path in masks)]
        cmd = ['create', '--name', names[role], '--label', 'kwg.supported-attempt='+prefix, '--pull', 'never', '--network', network,
            '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '32',
            '--memory', '128m', '--cpus', '1', '--user', '13:13' if image == SQUID_IMAGE else '65534:65534',
            '-i', '--entrypoint', entry]
        for source, target in mounts: cmd += ['--mount', f'type=bind,source={source},target={target},readonly']
        for host in hosts: cmd += ['--add-host', host]
        for address in dns: cmd += ['--dns', address]
        if role == 'proxy': cmd += ['--network-alias', 'kwg-egress']
        command(*cmd, image, *args)
        state = strict_json(command('inspect', names[role]).stdout)[0]
        receipt.setdefault('containers', {})[role] = inspect_container(state, image, network, entry, args, mounts, {'hosts': list(hosts), 'dns': list(dns)})
        return state
    def bootstrap(function):
        return ['-I', '-B', '-c', "import sys;sys.path.insert(0,'/snapshot/code');from supported_gateway import "+function+';'+function+'()']
    code_mounts = lambda files: [(sealed/'code'/f, '/snapshot/code/'+f) for f in files]
    record = {**BINDING, 'access_token': 'FAKE_CANARY_ACCESS', 'expires_at': time.time()+3600}
    if case == 'account_mismatch': record['subject'] = 'other'
    if case == 'client_mismatch': record['client_id'] = 'oaiapp_other'
    if case == 'expired': record['expires_at'] = 0
    if case == 'missing': record = None
    service = None
    previous_handler = None
    try:
        try: receipt['binding_sha256'] = fake_binding(record)
        except ValueError: receipt['state'] = 'binding_refused'; return receipt
        previous_handler = signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        for network in nets.values():
            command('network', 'create', '--internal', '--ipv6', '-o', 'com.docker.network.bridge.gateway_mode_ipv4=isolated',
                    '-o', 'com.docker.network.bridge.gateway_mode_ipv6=isolated', network)
            state = strict_json(command('network', 'inspect', network).stdout)[0]
            if (not state['Internal'] or not state['EnableIPv6'] or state['Driver'] != 'bridge'
                    or any(state['Options'].get('com.docker.network.bridge.gateway_mode_'+v) != 'isolated' for v in ('ipv4', 'ipv6'))):
                raise ValueError('Network isolation mismatch')
            receipt.setdefault('networks', []).append({'name': network, 'id': state['Id'], 'internal': True, 'ipv6': True, 'options': state['Options']})
        server_args = bootstrap('worker')  # Replace only the sealed fixture entry, never source or endpoints.
        server_args[-1] = "import sys;sys.path.insert(0,'/snapshot/code');from supported_gateway import server;server("+repr(case)+')'
        state = create('server', SANDBOX_IMAGE, nets['outer'], PYTHON, server_args,
            [*code_mounts(CODE_FILES), (attempt/'fixture/cert.pem', '/fixture/cert.pem'),
             (attempt/'fixture/key.pem', '/fixture/key.pem'), (attempt/'fixture/tls.json', '/fixture/tls.json')])
        command('start', names['server'])
        addresses = strict_json(command('inspect', names['server']).stdout)[0]['NetworkSettings']['Networks'][nets['outer']]
        server_ips = [addresses['IPAddress'], addresses['GlobalIPv6Address']]
        if any(not ip for ip in server_ips): raise ValueError('Fake server addresses unavailable')
        create('proxy', SQUID_IMAGE, nets['inner'], '/usr/bin/timeout',
            [str(DEADLINE), '/usr/sbin/squid', '-N', '-f', '/etc/squid/squid.conf'],
            [(attempt/'fixture/squid.conf', '/etc/squid/squid.conf')], hosts=['api.openai.com:'+server_ips[0]])
        command('network', 'connect', nets['outer'], names['proxy'])
        proxy_state = strict_json(command('inspect', names['proxy']).stdout)[0]
        if set(proxy_state['NetworkSettings']['Networks']) != set(nets.values()): raise ValueError('Proxy network mismatch')
        command('start', names['proxy'])
        probe = {'host_ips': [], 'host_port': 1, 'server_ips': server_ips}
        if case == 'success':
            class Canary(BaseHTTPRequestHandler):
                def log_message(self, *args): pass
                def do_GET(self):
                    self.send_response(200); self.end_headers(); self.wfile.write(b'KWG_INERT_HOST')
            service = ThreadingHTTPServer(('0.0.0.0', 0), Canary)
            threading.Thread(target=service.serve_forever, daemon=True).start()
            port = service.server_address[1]
            control_code = "import socket,json,urllib.request;ips=sorted({a[4][0] for a in socket.getaddrinfo('host.docker.internal',0,type=socket.SOCK_STREAM)});assert urllib.request.urlopen('http://host.docker.internal:"+str(port)+"/',timeout=2).read()==b'KWG_INERT_HOST';socket.create_connection(('1.1.1.1',443),timeout=2).close();print(json.dumps(ips))"
            create('control', SANDBOX_IMAGE, 'bridge', '/usr/sbin/python3', ['-I', '-S', '-B', '-c', control_code], [])
            ips = strict_json(command('start', '-a', names['control']).stdout)
            if not ips or any(not isinstance(ip, str) for ip in ips): raise ValueError('Host positive control failed')
            probe = {'host_ips': ips, 'host_port': port, 'server_ips': server_ips}
            receipt['host_positive_control'] = True
            control6_code = "import socket;"+';'.join("socket.create_connection(("+repr(ip)+",443),timeout=2).close()" for ip in server_ips)+";print('CONTROL_OK')"
            create('control6', SANDBOX_IMAGE, nets['outer'], '/usr/sbin/python3', ['-I', '-S', '-B', '-c', control6_code], [])
            if command('start', '-a', names['control6']).stdout.strip() != b'CONTROL_OK': raise ValueError('Upstream positive control failed')
            receipt['upstream_dual_stack_positive_control'] = True
        create('worker', SANDBOX_IMAGE, nets['inner'], PYTHON, bootstrap('worker'),
            [*code_mounts(CODE_FILES), (attempt/'fixture/ca.pem', '/fixture/ca.pem')], dns=['127.0.0.1'])
        worker_state = strict_json(command('inspect', names['worker']).stdout)[0]
        if set(worker_state['NetworkSettings']['Networks']) != {nets['inner']}: raise ValueError('Worker network mismatch')
        receipt['configuration_verified'] = True
        if case == 'interrupt': signal.raise_signal(signal.SIGINT)
        payload = json.dumps({'case': case, 'record': record, 'binding_sha256': BINDING_SHA,
            'prompt': research_module().build_prompt(packet), 'probe': probe}, allow_nan=False).encode()
        if len(payload) > MAX_OUTPUT: raise ValueError('Input limit')
        write_once(attempt/'started.json', {'state': 'started', 'binding_sha256': BINDING_SHA})
        receipt['state'] = 'outcome_unknown'
        result = command('start', '-a', '-i', names['worker'], check=False, input=payload)
        receipt['worker_exit'] = result.returncode
        audit = command('logs', names['server']).stdout
        if any(line != b'FAKE_POST' for line in audit.splitlines()) or audit.count(b'FAKE_POST') > 1:
            raise ValueError('Invalid fake request audit')
        receipt['fake_posts'] = audit.count(b'FAKE_POST')
        if result.returncode != 0:
            receipt['state'] = 'watchdog_exit' if case in ('timeout', 'trickle') and result.returncode == 2 else 'worker_failed'
            return receipt
        if len(result.stdout) > MAX_OUTPUT: raise ValueError('Output limit')
        response = strict_json(result.stdout)
        if (not isinstance(response, dict) or set(response) != {'status', 'binding_sha256', 'result', 'probes'}
                or response['binding_sha256'] != BINDING_SHA): raise ValueError('Worker response mismatch')
        if case == 'success':
            probes = response['probes']
            if not isinstance(probes, dict) or not probes or any(v is not True for v in probes.values()): raise ValueError('Isolation probe failed')
            receipt['probes'] = probes
        if response['status'] == 'transport_failed' and response['result'] is None:
            receipt['state'] = 'transport_failed'; return receipt
        transported = response['result']
        if (response['status'] != 'completed_transport' or not isinstance(transported, dict)
                or set(transported) != {'text', 'usage', 'model', 'reasoning_effort', 'promotion_status'}
                or transported['model'] != MODEL or transported['reasoning_effort'] != 'medium'
                or transported['promotion_status'] != 'blocked'):
            raise ValueError('Invalid transported response')
        create('parser', SANDBOX_IMAGE, 'none', '/usr/sbin/python3', ['-I', '-S', '-B', '-c', bootstrap('parse_worker')[-1]], code_mounts(PARSER_FILES))
        parsed = command('start', '-a', '-i', names['parser'], input=json.dumps({'text': transported['text']}).encode())
        if len(parsed.stdout) > MAX_OUTPUT: raise ValueError('Parser output limit')
        proposal = strict_json(parsed.stdout)
        research_module().parse_proposal(json.dumps(proposal).encode())
        receipt.update(state='completed', proposal=proposal, usage=transported['usage'], parser_credential_free=True)
    except KeyboardInterrupt:
        receipt['state'] = 'interrupted'
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        receipt['failure_kind'] = type(error).__name__  # Class only; never exception text or process stderr.
    finally:
        if previous_handler is not None: signal.signal(signal.SIGINT, previous_handler)
        if service is not None: service.shutdown(); service.server_close()
        cleaned = []
        cleanup_deadline = time.monotonic()+30
        def cleanup(*args):
            remaining = cleanup_deadline-time.monotonic()
            if remaining <= 0: raise subprocess.TimeoutExpired(args, 30)
            return subprocess.run([*docker, *args], env=env, capture_output=True, timeout=min(5, remaining))
        for name in names.values():
            try:
                cleanup('rm', '-f', '-v', name)
                absent = cleanup('ps', '-a', '--filter', f'name=^/{name}$', '--format', '{{.Names}}')
                cleaned.append(absent.returncode == 0 and not absent.stdout.strip())
            except (OSError, subprocess.SubprocessError): cleaned.append(False)
        for name in nets.values():
            try:
                cleanup('network', 'rm', name)
                absent = cleanup('network', 'ls', '--filter', f'name=^{name}$', '--format', '{{.Name}}')
                cleaned.append(absent.returncode == 0 and not absent.stdout.strip())
            except (OSError, subprocess.SubprocessError): cleaned.append(False)
        receipt['cleanup_verified'] = all(cleaned)
        receipt['attempt_consumed'] = True
        receipt['outcome'] = ('completed_synthetic' if receipt['state'] == 'completed' else
            'outcome_unknown' if (attempt/'started.json').exists() else 'failed_before_transmission')
        receipt['elapsed_seconds'] = round(time.monotonic()-started, 3)
        write_once(attempt/'receipt.json', receipt)
    return receipt


def readiness(seal_sha):
    from test_research_gold import packet_fixture
    sealed = Path(__file__).resolve().parent.parent
    if Path(__file__).parent.name != 'code' or sealed.parent.name != '.batch3-vibe' or not sealed.name.startswith('sealed-supported-'):
        raise ValueError('Run the supported sealed snapshot')
    verify_seal(sealed, seal_sha)
    metadata = strict_json((sealed/'readiness.json').read_bytes())
    production = sealed.parent/'production-attempts'
    review = sealed.parent/'supported-readiness'
    if (metadata.get('mode') != 'supported_fake_only' or metadata.get('production_registry') != str(production)
            or metadata.get('registry_acl_checked') is not True or metadata.get('policy') != POLICY
            or metadata.get('production_dispatch') != 'blocked'
            or any(metadata.get(k) is not False for k in ('production_isolation_verified', 'server_account_verified', 'billing_ceiling_verified'))
            or sealed.name != 'sealed-supported-'+metadata['git_commit'][:12]): raise ValueError('Supported seal binding mismatch')
    no_reparse(review); no_reparse(production)
    before = sorted(p.name for p in production.iterdir())
    write_once(review/(seal_sha+'.reserved.json'), {'seal_sha256': seal_sha, 'git_commit': metadata['git_commit'], 'model_requests': 0})
    results = []
    for case in sorted(CASES):
        packet = packet_fixture()
        packet['identity']['manifest_sha256'] = hashlib.sha256(('supported:'+seal_sha+':'+case).encode()).hexdigest()
        result = rehearse(sealed, seal_sha, review/'attempts', packet, case)
        attempt = review/'attempts'/packet['identity']['manifest_sha256']
        expected = ('completed' if case == 'success' else 'binding_refused' if case in ('account_mismatch','client_mismatch','expired','missing')
                    else 'watchdog_exit' if case in ('timeout','trickle') else 'worker_failed' if case == 'crash' else 'interrupted' if case == 'interrupt' else 'transport_failed')
        try: reserve(review/'attempts', packet, seal_sha, case, supported=True); replay = False
        except FileExistsError: replay = True
        passed = result['state'] == expected and result['cleanup_verified'] and replay and result.get('attempt_consumed') is True
        if expected not in ('binding_refused',): passed = passed and result['configuration_verified']
        if case == 'success': passed = passed and result.get('fake_posts') == 1 and result.get('parser_credential_free') is True
        results.append({'case': case, 'passed': passed, 'state': result['state'], 'replay_refused': replay,
            'fake_posts': result.get('fake_posts', 0), 'receipt_sha256': hashlib.sha256((attempt/'receipt.json').read_bytes()).hexdigest()})
        if not passed: break
    unchanged = before == sorted(p.name for p in production.iterdir())
    receipt = {'mode': 'supported_fake_only', 'git_commit': metadata['git_commit'], 'seal_sha256': seal_sha,
        'policy': POLICY, 'cases': results, 'offline_checks_passed': len(results) == len(CASES) and all(r['passed'] for r in results) and unchanged,
        'production_registry_unchanged': unchanged, 'model_requests': 0, 'dispatch_status': 'blocked',
        'production_isolation_verified': False, 'server_account_verified': False, 'billing_ceiling_verified': False,
        'qualification': 'unqualified', 'promotion_status': 'blocked'}
    write_once(review/(seal_sha+'.receipt.json'), receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal-sha256', required=True)
    args = parser.parse_args()
    try:
        result = readiness(args.seal_sha256)
        print(json.dumps(result, sort_keys=True))
        if not result['offline_checks_passed']: raise SystemExit(2)
    except Exception:
        print('Supported rehearsal refused; preserve attempts and receipts.', file=sys.stderr)
        raise SystemExit(2) from None
