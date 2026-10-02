"""Bounded synthetic transport rehearsal. No live provider or credential access."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


SANDBOX_IMAGE = 'sha256:35b089054ac9b4257976107e71673d9e30ac17c9b50bbf8b4783f2f6d1d1981f'
DOCKER = Path('C:/Program Files/Docker/Docker/resources/bin/docker.exe')


MODEL = 'openai-codex/gpt-6.1-sol'
MAX_TOKENS = 2048
MAX_BYTES = 16384
DEADLINE = 180


def preflight():
    """Read-only local runtime check; never authenticates or enables dispatch."""
    result = {'model': MODEL, 'reasoning_effort': 'medium', 'model_requests': 0,
        'additional_spend_approved_usd': 0, 'paid_fallback_allowed': False,
        'docker_engine_available': False, 'pinned_image_available': False,
        'production_isolation_verified': False, 'production_transport_implemented': False,
        'billing_ceiling_verified': False, 'dispatch_status': 'blocked'}
    config = Path(__file__).with_name('fixtures')
    # Do not load the owner's Docker credentials or an inherited remote context.
    if (config/'config.json').exists():
        result['blockers'] = ['unexpected_docker_config', 'production_transport_missing', 'billing_unverified']
        return result
    command = [str(DOCKER), '--config', str(config), '-H', 'npipe:////./pipe/dockerDesktopLinuxEngine']
    env = {k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR'}}
    try:
        info = subprocess.run([*command,'info','--format','{{.OSType}}'],
            env=env,capture_output=True,timeout=10)
        result['docker_engine_available'] = info.returncode == 0 and info.stdout.strip() == b'linux'
        if result['docker_engine_available']:
            image = subprocess.run([*command,'image','inspect','--format','{{.Id}}',SANDBOX_IMAGE],
                env=env,capture_output=True,timeout=10)
            result['pinned_image_available'] = image.returncode == 0 and image.stdout.strip().decode('ascii') == SANDBOX_IMAGE
    except (OSError,subprocess.TimeoutExpired,UnicodeError):
        pass
    result['blockers'] = ['production_transport_missing','billing_unverified','production_isolation_unverified']
    if not result['docker_engine_available']:
        result['blockers'].append('docker_unavailable')
    elif not result['pinned_image_available']:
        result['blockers'].append('pinned_image_unavailable')
    return result


def research_module():
    spec = importlib.util.spec_from_file_location('batch3_research', Path(__file__).with_name('research-gold.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provider_fixture_module():
    spec = importlib.util.spec_from_file_location('batch3_provider_fixture', Path(__file__).with_name('check-vibe-codex-guard.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_auth_fixture(value):
    if (not isinstance(value, dict) or set(value) != {'expired', 'refresh'}
            or type(value['expired']) is not bool
            or value['refresh'] not in ('success', 'permanent', 'timeout', 'stale', 'delay')):
        raise ValueError('Invalid fake authentication fixture')


def validate_auth_audit(value):
    if (not isinstance(value, dict) or set(value) != {'refreshes', 'clears', 'inference_posts'}
            or any(type(n) is not int or n not in (0, 1) for n in value.values())):
        raise ValueError('Invalid fake authentication audit')


def write_once(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with path.open('xb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    return hashlib.sha256(raw).hexdigest()


def worker():
    """One fake HTTP request through pinned definitions; no auth or generated code."""
    allowed = {'SYSTEMROOT', 'WINDIR', 'USERPROFILE', 'HOME', 'APPDATA', 'LOCALAPPDATA',
               'TEMP', 'TMP', 'PYTHONIOENCODING', 'LC_CTYPE'}
    if not sys.flags.isolated or not sys.flags.no_site or any(k.upper() not in allowed for k in os.environ):
        raise ValueError('Worker environment not isolated')
    payload = json.loads(sys.stdin.buffer.read(65537))
    if (set(payload) not in ({'fixture', 'request'}, {'fixture', 'request', 'auth_fixture'})
            or payload['request']['tools'] != []):
        raise ValueError('Invalid worker input')
    fixture = payload['fixture']
    if not {'response', 'tool_calls', 'usage', 'delay_seconds'} <= set(fixture) <= {'response', 'tool_calls', 'usage', 'delay_seconds', 'http_status'}:
        raise ValueError('Invalid fixture')
    delay = fixture['delay_seconds']
    if type(delay) not in (int, float) or not 0 <= delay <= DEADLINE:
        raise ValueError('Invalid delay')
    time.sleep(delay)
    source = Path('provider.py').read_bytes()
    if hashlib.sha256(source).hexdigest() != payload['request']['provider_source_sha256']:
        raise ValueError('Worker provider source mismatch')
    headers, refreshes, clears, audit = None, [], [], []
    auth_fixture = payload.get('auth_fixture')
    if 'auth_fixture' in payload:
        validate_auth_fixture(auth_fixture)
        if hashlib.sha256(json.dumps(auth_fixture, sort_keys=True, separators=(',', ':'),
                allow_nan=False).encode()).hexdigest() != payload['request']['auth_fixture_sha256']:
            raise ValueError('Auth fixture identity mismatch')
        helper = Path(__file__).with_name('batch3_auth_fixture.py')
        if hashlib.sha256(helper.read_bytes()).hexdigest() != payload['request']['auth_fixture_source_sha256']:
            raise ValueError('Auth fixture source mismatch')
        spec = importlib.util.spec_from_file_location('fake_auth_fixture', helper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        headers, refreshes, clears = module.fake_auth(source, **auth_fixture)
    try:
        response = provider_fixture_module().invoke_fixture(source, payload['request'], fixture,
            fake_header_factory=headers, audit=audit)
    except Exception:
        if auth_fixture is not None:
            print(json.dumps({'auth_audit': {'refreshes': len(refreshes), 'clears': len(clears),
                'inference_posts': len(audit)}}))
        raise SystemExit(2) from None
    if auth_fixture is not None:
        response['auth_audit'] = {'refreshes': len(refreshes), 'clears': len(clears),
            'inference_posts': len(audit)}
    usage = response['usage']
    if (not isinstance(usage, dict) or set(usage) != {'input_tokens', 'output_tokens', 'total_tokens'}
            or any(type(n) is not int or n < 0 for n in usage.values())
            or usage['total_tokens'] != usage['input_tokens'] + usage['output_tokens']
            or usage['output_tokens'] > MAX_TOKENS):
        raise ValueError('Usage missing or invalid')
    response['isolation_probe_passed'] = False
    if payload['request']['sandbox_expected']:
        import socket
        if os.getuid() != 65534:
            raise ValueError('Unexpected sandbox user')
        try:
            Path('/work/write-must-fail').write_text('synthetic probe')
        except OSError:
            pass
        else:
            raise ValueError('Sandbox filesystem is writable')
        with socket.socket() as connection:
            connection.settimeout(.2)
            try:
                connection.connect(('192.0.2.1', 443))
            except OSError:
                pass
            else:
                raise ValueError('Sandbox has network access')
        response['isolation_probe_passed'] = True
    print(json.dumps(response, separators=(',', ':')))


def run_fixture(packet, fixture, output_dir, *, deadline=DEADLINE, sandbox=False, auth_fixture=None):
    research = research_module()
    prompt = research.build_prompt(packet)
    if packet['limitations'] != ['synthetic_fixture']:
        raise ValueError('Synthetic packet required; live dispatch disabled')
    if type(deadline) not in (int, float) or not 0 < deadline <= DEADLINE:
        raise ValueError('Invalid deadline')
    if auth_fixture is not None:
        validate_auth_fixture(auth_fixture)
    source = provider_fixture_module().prepare_source(
        Path(__file__).resolve().parents[2] / '.batch3-vibe/upstream/agent/src/providers/openai_codex.py',
        Path(__file__).with_name('vibe-codex-one-request.patch'))
    request = {'model': MODEL, 'reasoning': {'effort': 'medium'}, 'tools': [],
               'tool_choice': 'none', 'parallel_tool_calls': False,
               'max_output_tokens': MAX_TOKENS, 'timeout_seconds': 120,
               'max_inference_posts': 1, 'retry': False, 'fallback': False,
               'prompt': prompt, 'provider_source_sha256': hashlib.sha256(source).hexdigest(),
               'sandbox_expected': bool(sandbox)}
    payload_value = {'fixture': fixture, 'request': request}
    if auth_fixture is not None:
        request['auth_fixture_sha256'] = research.digest(auth_fixture)
        request['auth_fixture_source_sha256'] = hashlib.sha256(
            Path(__file__).with_name('batch3_auth_fixture.py').read_bytes()).hexdigest()
        payload_value['auth_fixture'] = auth_fixture
    payload = json.dumps(payload_value, allow_nan=False).encode()
    if len(payload) > 65536 or len(prompt.encode()) > MAX_BYTES:
        raise ValueError('Worker input too large')
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(mode=0o700)
    container_name = 'kwg-batch3-fixture-' + uuid.uuid4().hex if sandbox else None
    # Exclusive reservation survives failure; never delete it to retry dispatch.
    write_once(output_dir / 'attempt.json', {'state': 'reserved_synthetic',
        'packet_sha256': research.digest(packet), 'request_sha256': research.digest(request),
        'worker_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'container_name': container_name, 'sandbox_image': SANDBOX_IMAGE if sandbox else None})
    write_once(output_dir / 'packet.json', packet)
    write_once(output_dir / 'request.json', request)
    if auth_fixture is not None:
        write_once(output_dir / 'auth-fixture.json', auth_fixture)
    with (output_dir / 'provider.py').open('xb') as output:
        output.write(source)
        output.flush()
        os.fsync(output.fileno())
    env = {k: v for k, v in os.environ.items() if k.upper() in {'SYSTEMROOT', 'WINDIR'}}
    env.update(USERPROFILE=str(output_dir), HOME=str(output_dir),
               APPDATA=str(output_dir), LOCALAPPDATA=str(output_dir),
               TEMP=str(output_dir), TMP=str(output_dir), PYTHONIOENCODING='utf-8')
    result = {'mode': 'synthetic-isolated-worker', 'status': 'worker_failed',
              'model_requests': 0, 'fake_requests': None, 'usage': None,
              'usage_source': 'synthetic_fixture', 'cost_usd': None,
              'live_dispatch': 'blocked_unknown_cost_and_unqualified_inputs',
              'filesystem_boundary': 'fixed_worker_no_file_tools_clean_environment',
              'os_sandbox': False, 'promotion_status': 'blocked',
              'human_promotion_approval_required': True, 'candidate_registered': False}
    if auth_fixture is not None:
        result.update(auth_audit=None, authentication='fake_memory_only')
    started = time.monotonic()
    command = [sys.executable, '-I', '-S', '-B', str(Path(__file__).resolve()), '--worker']
    docker = None
    if sandbox:
        config = output_dir / 'docker-config'
        config.mkdir()
        docker = [str(DOCKER), '--config', str(config), '-H', 'npipe:////./pipe/dockerDesktopLinuxEngine']
        command = [*docker, 'run', '--name', container_name, '--pull', 'never', '--network', 'none',
            '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '32',
            '--memory', '128m', '--cpus', '1', '--user', '65534:65534', '--workdir', '/work', '-i',
            '--entrypoint', '/usr/sbin/python3']
        empty = output_dir / 'empty-image-volume'
        empty.mkdir()
        for host, target in ((Path(__file__).resolve(), '/code/batch3_runner.py'),
                (Path(__file__).with_name('check-vibe-codex-guard.py').resolve(), '/code/check-vibe-codex-guard.py'),
                (output_dir / 'provider.py', '/work/provider.py'),
                (empty, '/etc/searxng'), (empty, '/var/cache/searxng')):
            command += ['--mount', f'type=bind,source={host},target={target},readonly']
        mount_targets = {'/code/batch3_runner.py', '/code/check-vibe-codex-guard.py', '/work/provider.py',
                         '/etc/searxng', '/var/cache/searxng'}
        if auth_fixture is not None:
            helper = Path(__file__).with_name('batch3_auth_fixture.py').resolve()
            command += ['--mount', f'type=bind,source={helper},target=/code/batch3_auth_fixture.py,readonly']
            mount_targets.add('/code/batch3_auth_fixture.py')
        command += [SANDBOX_IMAGE, '-I', '-S', '-B', '-c',
            "import os,sys,runpy; os.environ.clear(); sys.argv=['/code/batch3_runner.py','--worker']; runpy.run_path(sys.argv[0],run_name='__main__')"]
    try:
        completed = subprocess.run(command,
            input=payload, cwd=output_dir, env=env, capture_output=True, timeout=deadline)
        if docker:
            inspected = subprocess.run([*docker, 'inspect', container_name], capture_output=True, timeout=10, check=True)
            state = json.loads(inspected.stdout)[0]
            host = state['HostConfig']
            if (host['NetworkMode'] != 'none' or not host['ReadonlyRootfs'] or host['Privileged']
                    or host['CapDrop'] != ['ALL'] or 'no-new-privileges' not in host['SecurityOpt']
                    or host['Memory'] != 134217728 or host['PidsLimit'] != 32 or host['NanoCpus'] != 1000000000
                    or state['Config']['User'] != '65534:65534'
                    or {mount['Destination'] for mount in state['Mounts']} != mount_targets
                    or len(state['Mounts']) != len(mount_targets) or any(mount['RW'] for mount in state['Mounts'])
                    or state['Image'] != SANDBOX_IMAGE):
                raise ValueError('Container isolation mismatch')
            result.update(os_sandbox=True, sandbox_image=SANDBOX_IMAGE,
                          filesystem_boundary='readonly_reviewed_files_two_empty_readonly_dirs_no_credentials_no_network')
        if auth_fixture is not None and len(completed.stdout) <= 65536 and completed.stdout:
            response = json.loads(completed.stdout)
            validate_auth_audit(response.get('auth_audit'))
            if completed.returncode != 0 and set(response) != {'auth_audit'}:
                raise ValueError('Unexpected failed authentication response')
            result['auth_audit'] = response['auth_audit']
        if completed.returncode == 0 and len(completed.stdout) <= 65536:
            response = json.loads(completed.stdout)
            keys = {'response', 'usage', 'fake_requests', 'model_requests', 'isolation_probe_passed'}
            if auth_fixture is not None:
                keys.add('auth_audit')
            if (set(response) != keys
                    or response['fake_requests'] != 1 or response['model_requests'] != 0
                    or response['isolation_probe_passed'] is not bool(sandbox)):
                raise ValueError('Invalid worker response')
            proposal = research.parse_proposal(response['response'].encode())
            write_once(output_dir / 'response.json', response)
            write_once(output_dir / 'proposal.json', proposal)
            result.update(status='parsed_synthetic', fake_requests=1,
                          usage=response['usage'], proposal_sha256=research.digest(proposal),
                          isolation_probe_passed=response['isolation_probe_passed'])
    except subprocess.TimeoutExpired:
        # subprocess.run kills and waits for this fixed worker; it spawns no children.
        result['status'] = 'deadline_exceeded'
    except (ValueError, OSError, subprocess.CalledProcessError):
        pass  # Never persist arbitrary exception/stdout/stderr bodies.
    finally:
        if docker:
            try:
                removed = subprocess.run([*docker, 'rm', '-f', '-v', container_name],
                    capture_output=True, timeout=20)
                result['sandbox_cleanup_verified'] = removed.returncode == 0
                if not result['sandbox_cleanup_verified']:
                    result['status'] = 'sandbox_cleanup_failed'
            except (OSError, subprocess.TimeoutExpired):
                result.update(status='sandbox_cleanup_failed', sandbox_cleanup_verified=False)
    result['elapsed_seconds'] = round(time.monotonic() - started, 3)
    write_once(output_dir / 'result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    route = parser.add_mutually_exclusive_group(required=True)
    route.add_argument('--worker', action='store_true')
    route.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(),sort_keys=True))
        raise SystemExit(2)
    try:
        worker()
    except Exception:
        raise SystemExit(2) from None
