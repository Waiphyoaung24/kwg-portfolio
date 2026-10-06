"""Apply the reviewed patch to a disposable pinned snapshot and run fake-only tests.

Requires Windows, Python 3.12+ and the pinned commit in the local Git database.
Never fetches, changes a checkout, opens credentials or invokes a live helper.
"""
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

BASE = '18620b96eb05eeef86dcea52acf3e00cb1c09e6c'
FILES = {'gold_proposal.py', 'supported_oauth_transport.py', 'test_gold_proposal.py',
         'test_supported_oauth_transport.py', 'test_proposal_diagnostics.py'}


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
        for flags in (['--check'], []):
            subprocess.run(['git', 'apply', *flags, str(patch)], cwd=work, check=True)
        # Defense against accidental live IO in these specific tests, not a sandbox claim.
        code = '''
import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path.cwd()))
def offline(event, args):
    if event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        raise RuntimeError('Live IO forbidden in diagnostic tests')
    if event == 'open' and '.batch3-vibe' in str(args[0]):
        raise RuntimeError('Private runtime forbidden in diagnostic tests')
sys.addaudithook(offline)
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'test_supported_oauth_transport', 'test_gold_proposal', 'test_proposal_diagnostics'])
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(not result.wasSuccessful())
'''
        subprocess.run([sys.executable, '-I', '-B', '-c', code], cwd=work/'ops/trading', check=True)
    print('Pinned patch verified offline; no checkout or sealed runtime changed.')


if __name__ == '__main__':
    main()
