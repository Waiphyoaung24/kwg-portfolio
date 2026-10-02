"""Durable trusted-core controller rehearsal. Fake credentials and HTTP only."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

from batch3_runner import DEADLINE, DOCKER, MAX_BYTES, MAX_TOKENS, MODEL, SANDBOX_IMAGE, research_module, write_once
from trusted_oauth_transport import PROVIDER_SHA, invoke_bound, strict_json

FAKE_ACCOUNT = 'batch3-gateway-fixture'
FAKE_ACCOUNT_SHA = hashlib.sha256(FAKE_ACCOUNT.encode()).hexdigest()
CASES = {'success','401','account_mismatch','bad_usage','timeout'}


def no_reparse(path):
    for item in (path,*path.parents):
        if item.is_symlink() or item.exists() and getattr(item.lstat(),'st_file_attributes',0) & 0x400:
            raise ValueError('Reparse path rejected')


def verify_seal(root, expected):
    no_reparse(root/'manifest.json')
    with (root/'manifest.json').open('rb') as source:
        raw=source.read(65537)
    if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=expected:
        raise ValueError('Seal manifest identity mismatch')
    entries=strict_json(raw)
    if not isinstance(entries,list) or not entries:
        raise ValueError('Invalid seal manifest')
    listed=set()
    for entry in entries:
        if not isinstance(entry,dict) or set(entry)!={'path','sha256'} or not isinstance(entry['path'],str):
            raise ValueError('Invalid seal entry')
        name=entry['path'].replace('\\','/')
        if (':' in name or name.startswith('/') or any(p in ('','.','..') for p in name.split('/'))
                or name.casefold() in listed):
            raise ValueError('Invalid seal path')
        listed.add(name.casefold())
        path=root/name
        no_reparse(path)
        with path.open('rb') as source:
            content=source.read(1048577)
        if len(content)>1048576 or hashlib.sha256(content).hexdigest()!=entry['sha256']:
            raise ValueError('Sealed file identity mismatch')
    actual=set()
    for path in root.rglob('*'):
        no_reparse(path)
        if path.is_file() and path!=root/'manifest.json':
            actual.add(path.relative_to(root).as_posix().casefold())
    if actual!=listed:
        raise ValueError('Unexpected sealed files')


def reserve(registry, packet, seal_sha, case, *, supported=False):
    research=research_module()
    research.validate_packet(packet)
    allowed=CASES
    if supported is True:
        from supported_gateway import CASES as allowed
        from supported_gateway import BINDING, BINDING_SHA, MODEL as SUPPORTED_MODEL
    elif supported is not False:
        raise ValueError('Invalid rehearsal mode')
    if packet['limitations']!=['synthetic_fixture'] or case not in allowed:
        raise ValueError('Synthetic rehearsal only')
    no_reparse(registry)
    registry.mkdir(parents=True,exist_ok=True)
    attempt=registry/packet['identity']['manifest_sha256']
    attempt.mkdir()  # An interrupted reservation also consumes this identity.
    write_once(attempt/'attempt.json',{'state':'reserved_synthetic',
        'created_utc':datetime.now(timezone.utc).isoformat(),'case':case,
        'packet_sha256':research.digest(packet),'seal_sha256':seal_sha,
        'account_sha256':FAKE_ACCOUNT_SHA,'model':MODEL,'reasoning_effort':'medium',
        'max_inference_posts':1,'retry':False,'additional_cost_usd':None,
        **({'mode':'supported_fake_only','binding_sha256':BINDING_SHA,'model':SUPPORTED_MODEL,
            'account_sha256':hashlib.sha256(BINDING['subject'].encode()).hexdigest(),
            'client_sha256':hashlib.sha256(BINDING['client_id'].encode()).hexdigest()} if supported else {}),
        'production_dispatch':'blocked'})
    write_once(attempt/'packet.json',packet)
    return attempt


def validate_response(value):
    if (not isinstance(value,dict) or set(value)!={'status','fake_requests','model_requests','result'}
            or type(value['fake_requests']) is not int or value['fake_requests'] not in (0,1)
            or type(value['model_requests']) is not int or value['model_requests']!=0):
        raise ValueError('Invalid worker response')
    if value['status']=='provider_failed' and value['result'] is None:
        return
    result=value['result']
    if (value['status']!='parsed_synthetic' or value['fake_requests']!=1 or not isinstance(result,dict)
            or set(result)!={'proposal','usage','account_sha256','model','reasoning_effort','promotion_status'}
            or result['account_sha256']!=FAKE_ACCOUNT_SHA or result['model']!='gpt-6.1-sol'
            or result['reasoning_effort']!='medium' or result['promotion_status']!='blocked'):
        raise ValueError('Invalid bound result')
    usage=result['usage']
    if (not isinstance(usage,dict) or set(usage)!={'input_tokens','output_tokens','total_tokens'}
            or any(type(n) is not int or n<0 for n in usage.values())
            or usage['total_tokens']!=usage['input_tokens']+usage['output_tokens']
            or usage['output_tokens']>MAX_TOKENS):
        raise ValueError('Invalid usage')
    research_module().parse_proposal(json.dumps(result['proposal'],allow_nan=False).encode())


def worker():
    if not sys.flags.isolated or not sys.flags.no_site or os.getuid()!=65534:
        raise ValueError('Worker isolation required')
    # PID 1 ignores default termination signals; install an explicit watchdog handler.
    signal.signal(signal.SIGALRM,lambda *_: os._exit(2))
    signal.alarm(DEADLINE)
    raw=sys.stdin.buffer.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise ValueError('Worker input limit')
    payload=strict_json(raw)
    if (set(payload)!={'case','prompt'} or payload['case'] not in CASES
            or not isinstance(payload['prompt'],str) or len(payload['prompt'].encode())>MAX_BYTES):
        raise ValueError('Invalid worker input')
    case=payload['case']
    if case=='timeout': time.sleep(DEADLINE)
    claims={'exp':time.time()+3600,'https://api.openai.com/auth':{
        'chatgpt_account_id':'wrong' if case=='account_mismatch' else FAKE_ACCOUNT}}
    encoded=base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    token={'account_id':FAKE_ACCOUNT,'access':'FAKE_CANARY.'+encoded+'.FAKE_CANARY'}
    calls=[]
    class Response:
        status_code=401 if case=='401' else 200
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def iter_bytes(self,**kwargs):
            events=[{'type':'response.output_text.delta','delta':json.dumps({
                'kind':'ema20_slope_filter','lookback_bars':3,'hypothesis':'Synthetic gateway fixture'})},
                {'type':'response.completed','response':{'status':'completed','model':'gpt-6.1-sol',
                    'usage':None if case=='bad_usage' else {'input_tokens':100,'output_tokens':30,'total_tokens':130}}}]
            yield ''.join('data: '+json.dumps(event)+'\n\n' for event in events).encode()
    class Client:
        def __init__(self,**options):
            if options!={'timeout':120,'follow_redirects':False,'trust_env':False}: raise ValueError()
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def stream(self,method,url,**options):
            calls.append(1)
            body=options['json']; headers=options['headers']
            if (len(calls)!=1 or method!='POST' or url!='https://chatgpt.com/backend-api/codex/responses'
                    or headers['chatgpt-account-id']!=FAKE_ACCOUNT or headers['Authorization']!='Bearer '+token['access']
                    or body['model']!='gpt-6.1-sol' or body['reasoning']!={'effort':'medium'}
                    or body['max_output_tokens']!=MAX_TOKENS or body['tool_choice']!='none'
                    or body['parallel_tool_calls'] or 'tools' in body): raise ValueError()
            return Response()
    try:
        result=invoke_bound(Path('/snapshot/inputs/provider.py').read_bytes(),payload['prompt'],token,
            FAKE_ACCOUNT_SHA,SimpleNamespace(Client=Client))
        status='parsed_synthetic'
    except Exception:
        result=None; status='provider_failed'
    response={'status':status,'fake_requests':len(calls),'model_requests':0,'result':result}
    validate_response(response)
    raw=json.dumps(response,sort_keys=True,allow_nan=False)
    if len(raw.encode())>MAX_BYTES: raise ValueError('Worker output limit')
    print(raw)


def rehearse(registry, packet, seal_sha, case, deadline=DEADLINE):
    if type(deadline) not in (int,float) or not 0<deadline<=DEADLINE:
        raise ValueError('Invalid deadline')
    sealed=Path(__file__).resolve().parent.parent
    if Path(__file__).parent.name!='code': raise ValueError('Run the sealed controller')
    verify_seal(sealed,seal_sha)
    packet=strict_json(json.dumps(packet,allow_nan=False))
    payload=json.dumps({'case':case,'prompt':research_module().build_prompt(packet)},allow_nan=False).encode()
    if len(payload)>MAX_BYTES: raise ValueError('Worker input limit')
    if hashlib.sha256((sealed/'inputs/provider.py').read_bytes()).hexdigest()!=PROVIDER_SHA:
        raise ValueError('Pinned provider mismatch')
    attempt=reserve(Path(registry).absolute(),packet,seal_sha,case)
    config=attempt/'docker-config'; config.mkdir()
    empty=attempt/'empty'; empty.mkdir()
    owned='kwg-trusted-gateway-'+uuid.uuid4().hex
    write_once(attempt/'container.json',{'name':owned,'image':SANDBOX_IMAGE,'deadline_seconds':deadline})
    docker=[str(DOCKER),'--config',str(config),'-H','npipe:////./pipe/dockerDesktopLinuxEngine']
    env={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR'}}
    mounts={str(sealed):'/snapshot',str(empty):'/etc/searxng'}
    mount_pairs=[*mounts.items(),(str(empty),'/var/cache/searxng')]
    bootstrap="import os,sys;os.environ.clear();sys.path.insert(0,'/snapshot/code');from trusted_gateway import worker;worker()"
    command=[*docker,'create','--name',owned,'--pull','never','--network','none','--read-only',
        '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','32',
        '--memory','128m','--cpus','1','--user','65534:65534','-i','--entrypoint','/usr/sbin/python3']
    for source,target in mount_pairs:
        command+=['--mount',f'type=bind,source={source},target={target},readonly']
    command+=[SANDBOX_IMAGE,'-I','-S','-B','-c',bootstrap]
    receipt={'mode':'trusted_gateway_fake_rehearsal','status':'controller_failed','model_requests':0,
        'configuration_verified':False,'cleanup_verified':False,'response':None,
        'production_isolation_verified':False,'billing_ceiling_verified':False,'dispatch_status':'blocked'}
    start=time.monotonic()
    def bounded(args,**kwargs):
        remaining=deadline-(time.monotonic()-start)
        if remaining<=0: raise subprocess.TimeoutExpired(args,deadline)
        return subprocess.run(args,env=env,capture_output=True,timeout=remaining,**kwargs)
    try:
        bounded(command,check=True)
        inspected=bounded([*docker,'inspect',owned],check=True)
        state=strict_json(inspected.stdout)[0]; host=state['HostConfig']
        expected_mounts={(os.path.normcase(os.path.normpath(source)),target) for source,target in mount_pairs}
        actual_mounts={(os.path.normcase(os.path.normpath(m['Source'])),m['Target']) for m in host['Mounts']}
        if (host['NetworkMode']!='none' or not host['ReadonlyRootfs'] or host['Privileged']
                or host['CapDrop']!=['ALL'] or 'no-new-privileges' not in host['SecurityOpt']
                or host['Memory']!=134217728 or host['PidsLimit']!=32 or host['NanoCpus']!=1000000000
                or state['Config']['User']!='65534:65534' or state['Image']!=SANDBOX_IMAGE
                or state['Config']['Entrypoint']!=['/usr/sbin/python3']
                or state['Config']['Cmd']!=['-I','-S','-B','-c',bootstrap]
                or len(host['Mounts'])!=3 or actual_mounts!=expected_mounts
                or any(m['Type']!='bind' or not m['ReadOnly'] for m in host['Mounts'])
                or len(state['Mounts'])!=3 or any(m['RW'] for m in state['Mounts'])):
            raise ValueError('Container configuration mismatch')
        receipt['configuration_verified']=True
        completed=bounded([*docker,'start','-a','-i',owned],input=payload)
        if completed.returncode==0 and len(completed.stdout)<=MAX_BYTES:
            response=strict_json(completed.stdout)
            validate_response(response)
            receipt.update(status=response['status'],response=response)
    except subprocess.TimeoutExpired:
        receipt['status']='deadline_exceeded'
    except (ValueError,KeyError,TypeError,OSError,subprocess.SubprocessError):
        pass
    finally:
        try:
            removed=subprocess.run([*docker,'rm','-f','-v',owned],env=env,capture_output=True,timeout=20)
            absent=subprocess.run([*docker,'ps','-a','--filter',f'name=^/{owned}$','--format','{{.Names}}'],
                env=env,capture_output=True,timeout=10)
            receipt['cleanup_verified']=removed.returncode==0 and absent.returncode==0 and not absent.stdout.strip()
        except (OSError,subprocess.SubprocessError): pass
        if not receipt['cleanup_verified']: receipt['status']='cleanup_unverified'
    receipt['elapsed_seconds']=round(time.monotonic()-start,3)
    write_once(attempt/'receipt.json',receipt)
    return receipt


def readiness(seal_sha):
    """Review a committed seal with fake transport; never reserve a real attempt."""
    from test_research_gold import packet_fixture
    sealed=Path(__file__).resolve().parent.parent
    if (Path(__file__).parent.name!='code' or sealed.parent.name!='.batch3-vibe'
            or not sealed.name.startswith('sealed-gateway-readiness-')):
        raise ValueError('Run the committed readiness seal')
    verify_seal(sealed,seal_sha)
    metadata=strict_json((sealed/'readiness.json').read_bytes())
    production=sealed.parent/'production-attempts'
    if (metadata.get('mode')!='fake_readiness_only' or metadata.get('production_registry')!=str(production)
            or metadata.get('registry_acl_checked') is not True
            or metadata.get('production_dispatch')!='blocked'
            or any(metadata.get(k) is not False for k in ('billing_ceiling_verified',
                'server_account_verified','production_isolation_verified'))
            or not isinstance(metadata.get('git_commit'),str) or len(metadata['git_commit'])!=40
            or sealed.name!='sealed-gateway-readiness-'+metadata['git_commit'][:12]):
        raise ValueError('Invalid readiness binding')
    no_reparse(production)
    if not production.is_dir(): raise ValueError('Fixed production registry unavailable')
    review=sealed.parent/'gateway-readiness'
    no_reparse(review)
    # Synthetic reservations are deliberately separate from the production registry.
    review.mkdir(exist_ok=True)
    reservation=review/(seal_sha+'.reserved.json')
    write_once(reservation,{'seal_sha256':seal_sha,'git_commit':metadata['git_commit'],'model_requests':0})
    results=[]
    for case in sorted(CASES):
        packet=packet_fixture()
        packet['identity']['manifest_sha256']=hashlib.sha256(('fake-readiness:'+seal_sha+':'+case).encode()).hexdigest()
        result=rehearse(review/'attempts',packet,seal_sha,case,10 if case=='timeout' else DEADLINE)
        attempt=review/'attempts'/packet['identity']['manifest_sha256']
        before=(attempt/'attempt.json').read_bytes()
        try:
            reserve(review/'attempts',packet,seal_sha,case)
            replay_refused=False
        except FileExistsError:
            replay_refused=(attempt/'attempt.json').read_bytes()==before
        expected='parsed_synthetic' if case=='success' else 'deadline_exceeded' if case=='timeout' else 'provider_failed'
        results.append({'case':case,'passed':result['status']==expected and result['configuration_verified']
            and result['cleanup_verified'] and replay_refused,'status':result['status'],
            'replay_refused':replay_refused,'receipt_sha256':hashlib.sha256((attempt/'receipt.json').read_bytes()).hexdigest(),
            'fake_requests':(result['response'] or {}).get('fake_requests',0)})
    receipt={'mode':'fake_gateway_readiness','git_commit':metadata['git_commit'],'seal_sha256':seal_sha,
        'offline_checks_passed':all(r['passed'] for r in results),'cases':results,'model_requests':0,
        'production_isolation_verified':False,'server_account_verified':False,'billing_ceiling_verified':False,
        'dispatch_status':'blocked','qualification':'unqualified','promotion_status':'blocked',
        'human_approval_required':True}
    write_once(review/(seal_sha+'.receipt.json'),receipt)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--registry',type=Path)
    mode.add_argument('--readiness',action='store_true')
    parser.add_argument('--seal-sha256',required=True)
    parser.add_argument('--case',choices=sorted(CASES))
    parser.add_argument('--deadline',type=float,default=DEADLINE)
    args=parser.parse_args()
    if args.readiness and (args.case is not None or args.deadline!=DEADLINE):
        parser.error('Readiness uses fixed cases and deadlines')
    if not args.readiness and args.case is None: parser.error('--case is required for rehearsal')
    from test_research_gold import packet_fixture
    try:
        result=readiness(args.seal_sha256) if args.readiness else rehearse(args.registry,packet_fixture(),args.seal_sha256,args.case,args.deadline)
        print(json.dumps(result,sort_keys=True))
        if args.readiness and not result['offline_checks_passed']: raise SystemExit(2)
    except Exception:
        print('Gateway rehearsal refused; preserve the reservation.',file=sys.stderr)
        raise SystemExit(2) from None
