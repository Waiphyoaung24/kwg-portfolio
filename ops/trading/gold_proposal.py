"""Distinct sealed development proposal controller; no approval writer or renewal."""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from batch3_runner import DOCKER, MAX_BYTES, SANDBOX_IMAGE, research_module, write_once
from gold_account import (BOUND, DEADLINE, FILES as ACCOUNT_FILES, MODELS,
                          PROXY as ACCOUNT_PROXY, cleanup_guard, private_acl, probes)
from supported_gateway import PARSER_FILES, PYTHON, SQUID_IMAGE, inspect_container, watchdog
from supported_oauth_transport import MODEL, URL, invoke_isolated
from trusted_gateway import no_reparse, verify_seal
from trusted_oauth_transport import strict_json

FILES = ('gold_proposal.py', *ACCOUNT_FILES)
PROXY = ACCOUNT_PROXY.replace('auth.openai.com api.openai.com', 'api.openai.com').replace('kwg-gold-account', 'kwg-gold-proposal')
POLICY = dict(mode='gold_proposal_preparation', worker_image=SANDBOX_IMAGE, proxy_image=SQUID_IMAGE,
    proxy_sha256=hashlib.sha256(PROXY.encode()).hexdigest(), worker_python=PYTHON,
    httpx='0.28.1', httpcore='1.0.9', certifi='2026.5.20', logging='none',
    deadline_seconds=DEADLINE, url=URL, model=MODEL, reasoning_effort='medium',
    max_posts=1, retries=0, tools=False, trade_authority=False, additional_spend_usd=0,
    input_max_bytes=BOUND, proposal_max_bytes=MAX_BYTES, production_dispatch='blocked')
PREPARATION_SHA = '1c93fc050b0de511e6fa635b157720c3be74a1832c7585cec90296bc6ee7f046'
PACKET_SHA = 'e6f2d78918772b3791b3451c70a326a3d24de2a95da3c332d44d720065e70038'
PROMPT_SHA = 'cb4584ac365334f372a82a3b963bb806650c59ce9d84a8b23742f6145e12b9a7'
MODES = ('boundary', 'termination', 'dispatch')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_private(path, bound=BOUND):
    private_acl(path)
    with path.open('rb') as source: raw = source.read(bound+1)
    if len(raw)>bound: raise ValueError('Private input limit')
    return raw


def prepare_inputs(root, sealed):
    """Seal existing small artifacts; large dataset/baseline remain private and hash-bound."""
    from gold_experiment import source_hashes
    development=root/'gold-development'
    packet=development/'real-packet-e75e515e09a6'
    inputs=development/'real-inputs-e75e515e09a6'
    receipt_raw=read_private(inputs/'preparation-receipt.json')
    if sha(receipt_raw)!=PREPARATION_SHA: raise ValueError('Preparation identity refused')
    artifacts={'real-packet.json':(packet/'packet.json',PACKET_SHA),
        'real-prompt.txt':(packet/'prompt/prompt.txt',PROMPT_SHA),
        'real-manifest.json':(inputs/'manifest.json','3fe09a21ceca7e4386dcb9ffb33102fe46ec139bda651e9ff41f7773622a6e81'),
        'real-receipt.json':(inputs/'preparation-receipt.json',PREPARATION_SHA)}
    hashes={}
    for name,(path,expected) in artifacts.items():
        raw=read_private(path)
        if sha(raw)!=expected: raise ValueError('Prepared input changed')
        with (sealed/'inputs'/name).open('xb') as output: output.write(raw)
        hashes[name]=expected
    manifest=strict_json((sealed/'inputs/real-manifest.json').read_bytes())
    if manifest['code_sha256']!=source_hashes(): raise ValueError('Evaluator changed')
    billing=strict_json(read_private(root/'gold-plan-auth/billing-settings-20261005.json'))
    host=strict_json(read_private(root/'gold-plan-auth/host.json'))
    intent=dict(mode='one_real_development_proposal', policy=POLICY, inputs=hashes,
        preparation_sha256=PREPARATION_SHA, dataset_sha256=manifest['dataset_sha256'],
        baseline_sha256='632a33fcb6a0adac8d3a5449aeebe8751479dbf8f81a880afae99eb301078c18',
        experiment_sha256=strict_json((sealed/'inputs/real-packet.json').read_bytes())['identity']['manifest_sha256'],
        evaluator_sha256=manifest['code_sha256'], client_id_sha256=billing['client_id_sha256'],
        subject_sha256=billing['subject_sha256'], host_id_sha256=sha(host['id'].encode()),
        qualification='unqualified', promotion_status='blocked', owner_authorization='pending')
    write_once(sealed/'inputs/intent.json',intent)


def verify_inputs(root, sealed):
    from batch3_adapter import MAX_INPUT_BYTES, adapt_real, encode
    intent_raw=(sealed/'inputs/intent.json').read_bytes();intent=strict_json(intent_raw)
    if (intent['mode']!='one_real_development_proposal' or intent['policy']!=POLICY
            or intent['owner_authorization']!='pending' or intent['qualification']!='unqualified'
            or intent['promotion_status']!='blocked'
            or set(intent['inputs'])!= {'real-packet.json','real-prompt.txt','real-manifest.json','real-receipt.json'}
            or intent['inputs']['real-packet.json']!=PACKET_SHA or intent['inputs']['real-prompt.txt']!=PROMPT_SHA
            or intent['inputs']['real-receipt.json']!=PREPARATION_SHA): raise ValueError('Intent refused')
    for name,expected in intent['inputs'].items():
        if name not in ('real-packet.json','real-prompt.txt','real-manifest.json','real-receipt.json'):
            raise ValueError('Input path refused')
        if sha((sealed/'inputs'/name).read_bytes())!=expected: raise ValueError('Input identity refused')
    development=root/'gold-development'
    data=read_private(development/'gold-history-20260928-ssh-20261005.json',MAX_INPUT_BYTES)
    baseline=read_private(development/'real-inputs-e75e515e09a6/baseline-a.json',MAX_INPUT_BYTES)
    if sha(data)!=intent['dataset_sha256'] or sha(baseline)!=intent['baseline_sha256']:
        raise ValueError('Large private input changed')
    packet,_=adapt_real(data,baseline,(sealed/'inputs/real-manifest.json').read_bytes())
    research=research_module()
    if (encode(packet)!=(sealed/'inputs/real-packet.json').read_bytes()
            or research.build_prompt(packet).encode()!=(sealed/'inputs/real-prompt.txt').read_bytes()
            or packet['identity']['manifest_sha256']!=intent['experiment_sha256']):
        raise ValueError('Prepared packet no longer reproducible')
    return intent, sha(intent_raw)


def approval_gate(value, seal_sha, intent_sha, now):
    if (not isinstance(value,dict) or set(value)!= {'mode','seal_sha256','intent_sha256',
            'approved_at','expires_at','one_proposal_authorized','additional_spend_usd','account_seal_sha256'}
            or value['mode']!='one_real_development_proposal' or value['seal_sha256']!=seal_sha
            or value['intent_sha256']!=intent_sha or value['one_proposal_authorized'] is not True
            or type(value['additional_spend_usd']) is not int or value['additional_spend_usd']!=0
            or any(type(value[k]) is not int for k in ('approved_at','expires_at'))
            or not now-1800<=value['approved_at']<=now+5
            or not now<value['expires_at']<=value['approved_at']+1800
            or not isinstance(value['account_seal_sha256'],str) or len(value['account_seal_sha256'])!=64
            or any(c not in '0123456789abcdef' for c in value['account_seal_sha256'])):
        raise ValueError('Concrete fresh owner authorization required')


def billing_gate(value, intent, now):
    observed=value.get('observations',{})
    stamp=datetime.fromisoformat(value['saved_at'].replace('Z','+00:00')).timestamp()
    if (not now-300<=stamp<=now+5 or value.get('billing_ceiling_verified') is not True
            or any(value.get(k)!=intent[k] for k in ('client_id_sha256','subject_sha256'))
            or observed.get('app_name')!='KWG Gold Research' or observed.get('gold_app_entries')!=1
            or observed.get('app_plan_usage_allowed') is not True
            or observed.get('manage_usage_followed_from_gold_connection') is not True
            or observed.get('apps_credit_use_allowed') is not False
            or observed.get('automatic_reload_enabled') is not False or observed.get('save_button_enabled') is not False):
        raise ValueError('Fresh saved provider credit prevention required')


def accepted_account(record_raw, receipt, intent, account_sha, now):
    record=strict_json(record_raw)
    if (receipt.get('seal_sha256')!=account_sha or receipt.get('passed') is not True
            or receipt.get('cleanup_verified') is not True or receipt.get('required_model_present') is not True
            or receipt.get('server_account_verified') is not True or receipt.get('production_isolation_verified') is not True
            or receipt.get('registration_sha256')!=sha(record_raw)
            or type(receipt.get('accepted_at')) is not int or not now-300<=receipt['accepted_at']<=now+5
            or type(record.get('expires_at')) is not int or record['expires_at']<=now+300
            or record.get('issuer')!='https://auth.openai.com' or record.get('dispatch_status')!='blocked'
            or MODEL not in receipt.get('available_models',[]) or receipt.get('model_requests')!=0
            or any(not isinstance(record.get(k),str) or not record[k] for k in ('client_id','subject','ext_agent_host_id','access_token'))):
        raise ValueError('Fresh signed account acceptance required')
    for field,key in (('client_id','client_id_sha256'),('subject','subject_sha256'),('ext_agent_host_id','host_id_sha256')):
        if sha(record[field].encode())!=intent[key] or receipt.get(key)!=intent[key]: raise ValueError('Account binding mismatch')
    return record['access_token']


def reserve_production(registry, identity, seal_sha, intent_sha):
    if not isinstance(identity,str) or len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity):
        raise ValueError('Experiment identity required')
    attempt=registry/identity
    attempt.mkdir()  # Atomic, experiment-wide: even unknown/failed outcomes stay consumed.
    write_once(attempt/'started.json',dict(state='outcome_unknown',seal_sha256=seal_sha,
        intent_sha256=intent_sha,experiment_sha256=identity,max_posts=1,retries=0))
    return attempt


def dispatch_prerequisites(root, sealed, seal_sha, intent, intent_sha):
    # Approval is checked before auth-store access, network setup or production reservation.
    review=root/'proposal-readiness';now=time.time()
    approval=strict_json(read_private(review/(seal_sha+'.approval.json')))
    approval_gate(approval,seal_sha,intent_sha,now)
    for mode in ('boundary','termination'):
        result=strict_json(read_private(review/(seal_sha+'.'+mode)/'receipt.json'))
        if result.get('passed') is not True or result.get('seal_sha256')!=seal_sha or result.get('cleanup_verified') is not True:
            raise ValueError('Final native boundary acceptance required')
    denial=strict_json(read_private(review/(seal_sha+'.coding-denial.json')))
    if (denial.get('seal_sha256')!=seal_sha or denial.get('actual_coding_token') is not True
            or type(denial.get('checked_at')) is not int or not now-300<=denial['checked_at']<=now+5
            or denial.get('registration_open_denied') is not True or denial.get('canary_open_denied') is not True
            or denial.get('credential_contents_read') is not False):
        raise ValueError('Actual restricted coding credential denial required')
    billing_gate(strict_json(read_private(root/'gold-plan-auth'/('billing-dispatch-'+seal_sha+'.json'))),intent,now)
    account_sealed=root/('sealed-account-'+sealed.name.removeprefix('sealed-proposal-'))
    verify_seal(account_sealed,approval['account_seal_sha256'])
    from gold_account import POLICY as ACCOUNT_POLICY
    if strict_json((account_sealed/'readiness.json').read_bytes()).get('policy')!=ACCOUNT_POLICY:
        raise ValueError('Account acceptance policy differs')
    for name in ACCOUNT_FILES:
        if (account_sealed/'code'/name).read_bytes()!=(sealed/'code'/name).read_bytes():
            raise ValueError('Shared account source differs')
    receipt=strict_json(read_private(root/'account-readiness'/(approval['account_seal_sha256']+'.accept')/'receipt.json'))
    return approval['account_seal_sha256'],receipt


def worker():
    watchdog(DEADLINE);os.environ.clear()
    raw=sys.stdin.buffer.read(BOUND+1)
    if len(raw)>BOUND: raise ValueError('Worker input limit')
    value=strict_json(raw)
    if not isinstance(value,dict) or set(value)!= {'operation','value'}: raise ValueError('Worker input refused')
    if any(importlib.metadata.version(name)!=POLICY[name] for name in ('httpx','httpcore','certifi')):
        raise ValueError('Worker dependencies refused')
    operation=value['operation'];payload=value['value']
    if operation=='hold':
        if payload!='FAKE_CANARY_TERMINATION': raise ValueError('Synthetic input required')
        print('SYNTHETIC_INPUT_RECEIVED',flush=True)
        while True: time.sleep(.25)
    if operation=='probes':
        result=probes(payload,url=MODELS)
        import httpx
        with httpx.Client(proxy='http://kwg-egress:3128',trust_env=False,verify=True,follow_redirects=False,timeout=10) as client:
            with client.stream('GET',MODELS) as response:
                result['public_tls_verified']=response.status_code==401  # No auth, body read or inference.
        for target in ('auth.openai.com:443','api.openai.com.evil.invalid:443','1.1.1.1:443'):
            import socket
            with socket.create_connection(('kwg-egress',3128),timeout=2) as connection:
                connection.sendall(('CONNECT '+target+' HTTP/1.1\r\nHost: '+target+'\r\n\r\n').encode())
                result['proxy:'+target]=b' 403 ' in connection.recv(4096).split(b'\r\n')[0]
    elif operation=='proposal':
        if not isinstance(payload,dict) or set(payload)!= {'prompt','access_token'}: raise ValueError('Proposal input refused')
        result=invoke_isolated(payload['prompt'],payload['access_token'])
    else: raise ValueError('Fixed worker operation required')
    output=json.dumps(result,allow_nan=False).encode()
    if len(output)>BOUND: raise ValueError('Worker output limit')
    sys.stdout.buffer.write(output)


def location(seal_sha):
    sealed=Path(__file__).resolve().parent.parent
    if Path(__file__).parent.name!='code' or not sealed.name.startswith('sealed-proposal-') or sealed.parent.name!='.batch3-vibe':
        raise ValueError('Sealed proposal entry required')
    verify_seal(sealed,seal_sha)
    metadata=strict_json((sealed/'readiness.json').read_bytes())
    if (metadata.get('policy')!=POLICY or metadata.get('mode')!='gold_proposal_preparation'
            or sealed.name!='sealed-proposal-'+metadata['git_commit'][:12]
            or metadata.get('production_registry')!=str(sealed.parent/'production-attempts')
            or metadata.get('production_dispatch')!='blocked'
            or any(metadata.get(k) is not False for k in ('production_isolation_verified','server_account_verified','billing_ceiling_verified'))):
        raise ValueError('Proposal preparation policy refused')
    private_acl(sealed)
    return sealed


def run(seal_sha, mode):
    sealed=location(seal_sha);root=sealed.parent
    review=root/'proposal-readiness';private_acl(review)
    intent,intent_sha=verify_inputs(root,sealed)
    account_sha,account_receipt=dispatch_prerequisites(root,sealed,seal_sha,intent,intent_sha) if mode=='dispatch' else (None,None)
    attempt=review/(seal_sha+'.'+mode)
    if mode=='dispatch':
        private_acl(root/'production-attempts')
        attempt=reserve_production(root/'production-attempts',intent['experiment_sha256'],seal_sha,intent_sha)
    else: attempt.mkdir()
    for folder in ('docker-config','empty'): (attempt/folder).mkdir()
    (attempt/'squid.conf').write_text(PROXY)
    prefix='kwg-proposal-'+uuid.uuid4().hex
    names={role:prefix+'-'+role for role in ('proxy','probe','request','parser','control','peer','peer-control')}
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
        args=['-I','-B','-c',"import sys;sys.path.insert(0,'/snapshot/code');from gold_proposal import worker\ntry: worker()\nexcept Exception: sys.exit(2)"]
        create(role,SANDBOX_IMAGE,nets['inner'],PYTHON,args,[(sealed/'code'/name,'/snapshot/code/'+name) for name in FILES],['127.0.0.1'])
        state=strict_json(command('inspect',names[role]).stdout)[0]
        if set(state['NetworkSettings']['Networks'])!={nets['inner']}: raise ValueError('Worker extra network')
    def exchange(role,operation,value):
        create_worker(role)
        raw=json.dumps({'operation':operation,'value':value},allow_nan=False).encode()
        if len(raw)>BOUND: raise ValueError('Worker input limit')
        process=command('start','-a','-i',names[role],input=raw,check=False)
        if process.returncode or len(process.stdout)>BOUND: raise ValueError('Proposal worker refused')
        return strict_json(process.stdout)
    guard=subprocess.Popen([sys.executable,'-I','-S','-B',str(sealed/'code/gold_proposal.py'),'--seal-sha256',seal_sha,
        '--guard',str(attempt),'--parent',str(os.getpid())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS,close_fds=True)
    receipt=dict(mode=mode,seal_sha256=seal_sha,intent_sha256=intent_sha,passed=False,
        model_requests=0,dispatch_status='blocked',promotion_status='blocked')
    service=None
    try:
        for _ in range(100):
            if (attempt/'guard-ready.json').exists(): break
            if guard.poll() is not None: raise ValueError('Guardian unavailable')
            time.sleep(.05)
        else: raise ValueError('Guardian not ready')
        command('network','create','--internal','--ipv6','-o','com.docker.network.bridge.gateway_mode_ipv4=isolated',
            '-o','com.docker.network.bridge.gateway_mode_ipv6=isolated',nets['inner'])
        command('network','create','--ipv6',nets['outer'])
        state=strict_json(command('network','inspect',nets['inner']).stdout)[0]
        if not state['Internal'] or not state['EnableIPv6'] or state['Driver']!='bridge' or any(state['Options'].get('com.docker.network.bridge.gateway_mode_'+v)!='isolated' for v in ('ipv4','ipv6')):
            raise ValueError('Inner network refused')
        outer=strict_json(command('network','inspect',nets['outer']).stdout)[0]
        if outer['Internal'] or not outer['EnableIPv6'] or outer['Driver']!='bridge': raise ValueError('Outer network refused')
        create('proxy',SQUID_IMAGE,nets['inner'],'/usr/bin/timeout',[str(DEADLINE),'/usr/sbin/squid','-N','-f','/etc/squid/squid.conf'],[(attempt/'squid.conf','/etc/squid/squid.conf')],['1.1.1.1','1.0.0.1'])
        command('network','connect',nets['outer'],names['proxy'])
        if set(strict_json(command('inspect',names['proxy']).stdout)[0]['NetworkSettings']['Networks'])!=set(nets.values()):
            raise ValueError('Proxy extra network')
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
            create('peer',SANDBOX_IMAGE,nets['outer'],'/usr/sbin/python3',['-I','-S','-B','-c',"import socket,time;s=socket.socket(socket.AF_INET6);s.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,0);s.bind(('::',443));s.listen();time.sleep(180)"],[])
            command('start',names['peer'])
            peer=strict_json(command('inspect',names['peer']).stdout)[0]['NetworkSettings']['Networks'][nets['outer']]
            peer_ips=[peer['IPAddress'],peer['GlobalIPv6Address']]
            if not all(peer_ips): raise ValueError('Dual-stack peer required')
            create('peer-control',SANDBOX_IMAGE,nets['outer'],'/usr/sbin/python3',['-I','-S','-B','-c',"import socket;[(socket.create_connection((ip,443),timeout=2).close()) for ip in "+repr(peer_ips)+"];print('PEER_OK')"],[])
            if command('start','-a',names['peer-control']).stdout.strip()!=b'PEER_OK': raise ValueError('Peer control failed')
            checked=exchange('probe','probes',{'host_ips':ips,'host_port':port,'peer_ips':peer_ips})
            if not checked or any(value is not True for value in checked.values()): raise ValueError('Isolation probe failed')
            receipt.update(probes=checked,public_tls_verified=True,host_internet_positive_control=True)
            if mode=='termination':
                create_worker('request')
                attached=subprocess.Popen([*docker,'start','-a','-i',names['request']],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
                attached.stdin.write(b'{"operation":"hold","value":"FAKE_CANARY_TERMINATION"}');attached.stdin.close()
                if attached.stdout.readline().strip()!=b'SYNTHETIC_INPUT_RECEIVED': raise ValueError('Synthetic transfer not verified')
                receipt['synthetic_input_transferred']=True
                write_once(attempt/'kill-ready.json',receipt)
                while True: time.sleep(.25)
            receipt['passed']=True
        else:
            auth=root/'gold-plan-auth';private_acl(auth)
            import msvcrt
            with (auth/'registration.lock').open('r+b') as lock:
                lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                access=accepted_account(read_private(auth/'registration.json'),account_receipt,intent,account_sha,time.time())
                # Recheck the saved UI receipt immediately before credential transfer.
                billing_gate(strict_json(read_private(auth/('billing-dispatch-'+seal_sha+'.json'))),intent,time.time())
                receipt['model_requests']='outcome_unknown'
                result=exchange('request','proposal',{'prompt':(sealed/'inputs/real-prompt.txt').read_text(encoding='utf-8'),'access_token':access})
            receipt['model_requests']=1
            create('parser',SANDBOX_IMAGE,'none','/usr/sbin/python3',
                ['-I','-S','-B','-c',"import sys;sys.path.insert(0,'/snapshot/code');from supported_gateway import parse_worker\ntry: parse_worker()\nexcept Exception: sys.exit(2)"],
                [(sealed/'code'/name,'/snapshot/code/'+name) for name in PARSER_FILES])
            parsed=command('start','-a','-i',names['parser'],input=json.dumps({'text':result['text']}).encode())
            if len(parsed.stdout)>MAX_BYTES: raise ValueError('Parsed output limit')
            proposal=strict_json(parsed.stdout)
            write_once(attempt/'proposal.json',proposal);write_once(attempt/'usage.json',result['usage'])
            receipt.update(passed=True,dispatch_status='completed_one_request',provider_credit_ceiling_usd=0)
    except Exception as error:
        receipt['failure_kind']=type(error).__name__
        if mode=='dispatch': receipt['dispatch_status']='consumed_outcome_unknown'
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
    sealed=location(seal_sha);attempt=sealed.parent/'proposal-readiness'/(seal_sha+'.termination')
    if attempt.exists(): raise FileExistsError('Preserve consumed termination test')
    process=subprocess.Popen([sys.executable,'-I','-S','-B',str(sealed/'code/gold_proposal.py'),
        '--seal-sha256',seal_sha,'--mode','termination'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+150
    try:
        while time.monotonic()<deadline and not (attempt/'kill-ready.json').exists():
            if process.poll() is not None: raise ValueError('Termination setup refused')
            time.sleep(.1)
        if not (attempt/'kill-ready.json').exists(): raise ValueError('Termination setup deadline')
        before=strict_json((attempt/'kill-ready.json').read_bytes())
        if not before.get('synthetic_input_transferred') or not before.get('public_tls_verified'): raise ValueError('Transfer not ready')
        process.terminate();process.wait(timeout=10)
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
    parser.add_argument('--mode',choices=(*MODES,'verify-termination'))
    parser.add_argument('--guard');parser.add_argument('--parent',type=int)
    args=parser.parse_args()
    try:
        if args.guard:
            sealed=location(args.seal_sha256);path=Path(args.guard)
            intent=strict_json((sealed/'inputs/intent.json').read_bytes())
            allowed={sealed.parent/'proposal-readiness'/(args.seal_sha256+'.'+mode) for mode in ('boundary','termination')}
            allowed.add(sealed.parent/'production-attempts'/intent['experiment_sha256'])
            if path not in allowed or not args.parent: raise ValueError('Fixed guardian attempt required')
            owned=strict_json((path/'owned.json').read_bytes())
            all_names=[*owned['containers'].values(),*owned['networks'].values()]
            if any(not name.startswith('kwg-proposal-') or not name.replace('-','').isalnum() for name in all_names):
                raise ValueError('Guardian resource identity refused')
            cleanup_guard(path,args.parent,policy=POLICY)
        else:
            if args.mode is None: raise ValueError('Proposal mode required')
            result=termination_check(args.seal_sha256) if args.mode=='verify-termination' else run(args.seal_sha256,args.mode)
            print(json.dumps(result,sort_keys=True))
            if not result['passed']: raise SystemExit(2)
    except Exception:
        print('Proposal check refused; preserve inputs, attempts and credentials.',file=sys.stderr)
        raise SystemExit(2) from None
