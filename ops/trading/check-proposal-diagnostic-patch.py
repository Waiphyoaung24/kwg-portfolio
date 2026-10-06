"""Verify the pinned diagnostic patch, shared-runtime compatibility and reversal.

Requires Windows, Python 3.12+ and the pinned commit in the local Git database.
All patch operations and fixture seals occur in a disposable public-source export.
"""
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

BASE = '18620b96eb05eeef86dcea52acf3e00cb1c09e6c'
FILES = {'gold_proposal.py', 'supported_oauth_transport.py', 'test_gold_proposal.py',
         'test_supported_oauth_transport.py', 'test_proposal_diagnostics.py'}
OFFLINE = '''
import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path.cwd()))
def offline(event, args):
    if event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        raise RuntimeError('Live IO forbidden in diagnostic tests')
    if event == 'open' and '.batch3-vibe' in str(args[0]):
        raise RuntimeError('Private runtime forbidden in diagnostic tests')
sys.addaudithook(offline)
'''


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*')
            if p.is_file() and '.git' not in p.relative_to(folder).parts}


def main():
    if sys.platform != 'win32' or sys.version_info < (3, 12):
        raise SystemExit('Use Windows and Python 3.12+ for the real temporary-file locking test.')
    root = Path(__file__).resolve().parents[2]
    patch = Path(__file__).with_name('patches') / '2026-10-06-proposal-diagnostics.patch'
    names = {line[6:] for line in patch.read_text(encoding='utf-8').splitlines() if line.startswith('+++ b/')}
    if names != {'ops/trading/'+name for name in FILES}:
        raise SystemExit('Unexpected patch scope')
    archive = subprocess.run(['git', '-C', str(root), 'archive', BASE, 'ops/trading'],
                             check=True, capture_output=True).stdout
    with tempfile.TemporaryDirectory(prefix='kwg-diagnostic-check-') as folder:
        work = Path(folder)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(work, filter='data')
        # Honor the exported eol=lf attributes; never alter global Git configuration.
        subprocess.run(['git', 'init', '--quiet', str(work)], check=True)
        before = snapshot(work)
        trading = work/'ops/trading'
        policy = subprocess.run([sys.executable, '-I', '-B', '-c', OFFLINE+'''
import json, gold_proposal, gold_account, supported_gateway
print(json.dumps(dict(proposal=gold_proposal.POLICY, account=gold_account.POLICY, gateway=supported_gateway.POLICY)))
'''], cwd=trading, check=True, capture_output=True).stdout
        for flags in (['--check'], []):
            subprocess.run(['git', 'apply', *flags, str(patch)], cwd=work, check=True)
        changed = {name for name, raw in snapshot(work).items() if before.get(name) != raw}
        if changed != {'ops/trading/'+name for name in FILES}:
            raise SystemExit('Applied patch changed unexpected files')
        (trading/'policy-before.json').write_bytes(policy)
        extra = trading/'test_proposal_runtime_integration.py'
        shutil.copyfile(Path(__file__).with_name('diagnostic-tests')/extra.name, extra)
        code = OFFLINE+'''
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'test_supported_oauth_transport', 'test_gold_proposal', 'test_proposal_diagnostics',
    'test_proposal_runtime_integration'])
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
'''
        subprocess.run([sys.executable, '-I', '-B', '-c', code], cwd=trading, check=True)
        extra.unlink(); (trading/'policy-before.json').unlink()
        for flags in (['--check'], []):
            subprocess.run(['git', 'apply', '--reverse', *flags, str(patch)], cwd=work, check=True)
        after = snapshot(work)
        if after != before:
            for name in sorted(before.keys() | after.keys()):
                if before.get(name) != after.get(name):
                    old, new = before.get(name, b''), after.get(name, b'')
                    print('Rollback difference:', name, 'bytes', len(old), len(new), 'CRLF counts', old.count(b'\r\n'), new.count(b'\r\n'))
            raise SystemExit('Rollback did not restore the exact pinned public-source tree')
    print('19 fake checks passed; reverse patch restored every pinned file byte and removed the added test.')
    print('No checkout, sealed runtime or production registry changed.')


if __name__ == '__main__':
    main()
