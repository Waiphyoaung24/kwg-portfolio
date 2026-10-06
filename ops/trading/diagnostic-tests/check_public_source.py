"""Fake-only public-source checks: blocks network, subprocess and private-tree IO."""
from pathlib import Path
import sys
import tempfile
import unittest
import hashlib

trading = Path(__file__).resolve().parents[1]
for name, expected in {
    'gold_proposal.py': '8195b6ae0e6ad01a3790e901a042cdc0d039629087df981b90ba0de7a700ee85',
    'supported_oauth_transport.py': 'bd2ca3f1c2952003a1ab1c9ba84fc1bef2699f375f28bfe1ec6b0a6bf19bf73e',
    'test_gold_proposal.py': 'c557da3abb7a5b580c22ff5852af2275a9d39870f5cb8e2232218a2d79a8569c',
    'test_supported_oauth_transport.py': 'dbee602a8dc6101e75505d096136fa57048eae1cd360b3c314c27f947582e023',
    'test_proposal_diagnostics.py': '5a9b1afb829228fb4eec7a2d052af592dbd9870a4fe46fbd2c11303d3962aac4',
}.items():
    if hashlib.sha256((trading/name).read_bytes()).hexdigest() != expected:
        raise SystemExit('Pinned public source changed: '+name)
sys.path.insert(0, str(trading))
sys.path.insert(0, str(Path(__file__).resolve().parent))
fixtures = tempfile.TemporaryDirectory(prefix='kwg-FAKE-public-check-')
fixture_root = Path(fixtures.name).resolve()
old_tempdir = tempfile.tempdir
tempfile.tempdir = str(fixture_root)


def offline(event, args):
    if event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        raise RuntimeError('Live IO forbidden in public-source tests')
    if event == 'open' and '.batch3-vibe' in str(args[0]) and not Path(args[0]).resolve().is_relative_to(fixture_root):
        raise RuntimeError('Private runtime forbidden in public-source tests')


sys.addaudithook(offline)
suite = unittest.defaultTestLoader.loadTestsFromNames([
    'test_supported_oauth_transport', 'test_gold_proposal', 'test_proposal_diagnostics',
    'test_supported_gateway', 'test_gold_account', 'test_gold_account_crypto',
    'test_real_development', 'test_proposal_approval_candidate'])
result = unittest.TextTestRunner(verbosity=1).run(suite)
tempfile.tempdir = old_tempdir
fixtures.cleanup()
raise SystemExit(not result.wasSuccessful())
