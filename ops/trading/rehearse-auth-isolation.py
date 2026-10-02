"""Credential-free Docker rehearsal; never performs real OAuth or inference."""
import argparse
from pathlib import Path

from batch3_runner import run_fixture, write_once
from test_batch3_rehearsal import GOOD
from test_research_gold import packet_fixture


def rehearse(output):
    output = Path(output)
    output.mkdir(mode=0o700)
    cases = []
    for name, auth, status, deadline in (
            ('refresh_success', {'expired': True, 'refresh': 'success'}, 200, 180),
            ('refresh_failure', {'expired': True, 'refresh': 'permanent'}, 200, 180),
            ('inference_401', {'expired': False, 'refresh': 'success'}, 401, 180),
            ('auth_timeout', {'expired': True, 'refresh': 'delay'}, 200, 1)):
        result = run_fixture(packet_fixture(), dict(GOOD, http_status=status),
            output/name, auth_fixture=auth, deadline=deadline, sandbox=True)
        expected = 'parsed_synthetic' if name == 'refresh_success' else (
            'deadline_exceeded' if name == 'auth_timeout' else 'worker_failed')
        passed = result['status'] == expected and result.get('sandbox_cleanup_verified') is True
        if name != 'auth_timeout':
            passed = passed and result['os_sandbox'] is True and result['auth_audit'] is not None
            if passed:
                refreshes, clears, posts = {'refresh_success': (1, 0, 1),
                    'refresh_failure': (1, 1, 0), 'inference_401': (0, 0, 1)}[name]
                passed = result['auth_audit'] == {'refreshes': refreshes, 'clears': clears,
                    'inference_posts': posts}
        if name == 'refresh_success':
            passed = passed and result.get('isolation_probe_passed') is True
        cases.append({'case': name, 'passed': passed, 'status': result['status'],
            'auth_audit': result.get('auth_audit'), 'os_sandbox': result['os_sandbox'],
            'cleanup_verified': result.get('sandbox_cleanup_verified'), 'model_requests': 0})
        if not passed:
            break  # Preserve failed attempts; do not automatically retry.
    summary = {'mode': 'fake_auth_docker_rehearsal', 'cases': cases,
        'passed': len(cases) == 4 and all(c['passed'] for c in cases),
        'real_credential_transport_verified': False, 'billing_ceiling_verified': False,
        'model_requests': 0, 'promotion_status': 'blocked'}
    write_once(output/'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = rehearse(args.output)
    print('PASS: fake-auth Docker isolation and cleanup; model_requests=0' if result['passed']
          else 'FAIL: preserve the attempt; no automatic retry or live dispatch')
    raise SystemExit(0 if result['passed'] else 2)
