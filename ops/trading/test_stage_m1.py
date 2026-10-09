import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class StageM1Test(unittest.TestCase):
    def test_isolated_python_loads_staged_modules_and_matches_manifest_identity(self):
        source = Path(__file__).parent
        names = ('demo_pilot.py', 'demo_one_shot.py', 'mt5_data.py', 'gold_signal.py', 'gold_experiment.py')
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            for name in (*names, 'switch-pilot-m1.py'):
                (stage / name).write_bytes((source / name).read_bytes().replace(b'\r\n', b'\n'))
            hashes = {name: hashlib.sha256((stage / name).read_bytes()).hexdigest() for name in names}
            expected = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            result = subprocess.run([sys.executable, '-I', '-B', '-c',
                "import runpy,sys; p=runpy.run_path(sys.argv[1])['pilot']; print(p.__file__); print(p.identity())",
                str(stage / 'switch-pilot-m1.py')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = result.stdout.splitlines()
            self.assertEqual(Path(lines[0]).resolve(), (stage / 'demo_pilot.py').resolve())
            self.assertEqual(lines[1], expected)

    def test_unprivileged_receiver_preserves_bytes_and_rejects_bad_hash(self):
        source = Path(__file__).with_name('stage-m1-pilot.ps1').read_text()
        remote = source.split("$taskRemote = @'\n", 1)[1].split("\n'@", 1)[0]
        receiver = next(ast.literal_eval(node.value) for node in ast.parse(remote).body
                        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'receiver' for t in node.targets))
        self.assertIn("'--user','mt5','kwg-mt5-desktop','python3'", remote)
        self.assertNotIn("'chown'", remote)
        raw = b'print("sample")\n'
        bundle = {'sample.py': {'data': base64.b64encode(raw).decode(), 'sha256': hashlib.sha256(raw).hexdigest()}}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'stage'
            result = subprocess.run([sys.executable, '-B', '-c', receiver, str(target)],
                                    input=json.dumps(bundle).encode(), capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((target / 'sample.py').read_bytes(), raw)
            bundle['sample.py']['sha256'] = 'wrong'
            invalid = Path(directory) / 'invalid'
            result = subprocess.run([sys.executable, '-B', '-c', receiver, str(invalid)],
                                    input=json.dumps(bundle).encode(), capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((invalid / 'sample.py').exists())


if __name__ == '__main__':
    unittest.main()
