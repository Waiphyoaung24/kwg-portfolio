import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('deploy_pilot', Path(__file__).with_name('deploy-demo-pilot.py'))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentTest(unittest.TestCase):
    def test_changed_bundle_never_reaches_preflight_or_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            (stage / 'desktop.sh').write_bytes(b'changed')
            (stage / 'manifest.json').write_text(json.dumps({'desktop.sh': '0' * 64}))
            with patch.object(deploy.runpy, 'run_path') as preflight, patch.object(deploy.subprocess, 'check_output') as docker:
                with self.assertRaisesRegex(AssertionError, 'Bundle hash mismatch'):
                    deploy.deploy(stage)
                preflight.assert_not_called()
                docker.assert_not_called()

    def test_failed_broker_preflight_never_changes_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            source = b'raise AssertionError("Account must be flat")\n'
            (stage / 'preflight-demo-pilot.py').write_bytes(source)
            (stage / 'manifest.json').write_text(json.dumps({'preflight-demo-pilot.py': hashlib.sha256(source).hexdigest()}))
            with patch.object(deploy.subprocess, 'check_output') as docker:
                with self.assertRaisesRegex(AssertionError, 'Account must be flat'):
                    deploy.deploy(stage)
                docker.assert_not_called()
                self.assertFalse((stage / 'backup').exists())


if __name__ == '__main__':
    unittest.main()
