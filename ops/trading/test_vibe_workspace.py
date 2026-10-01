"""Local launcher configuration checks; no provider imports or network."""
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class WorkspaceTest(unittest.TestCase):
    def test_clean_environment_and_existing_product_commands(self):
        path = Path(__file__).with_name('vibe-workspace.py')
        self.assertTrue(path.exists())
        spec = importlib.util.spec_from_file_location('vibe_workspace', path)
        workspace = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workspace)
        root = Path('C:/synthetic/workspace')
        env = workspace.child_environment(root, {'SystemRoot': 'C:/Windows',
            'PATH': 'synthetic', 'OPENAI_API_KEY': 'DO_NOT_INHERIT',
            'KWG_GOLD_MCP_TOKEN': 'DO_NOT_INHERIT', 'LANGCHAIN_MODEL_NAME': 'other',
            'MT5_DEMO_LOGIN': 'DO_NOT_INHERIT', 'CODEX_HOME': 'DO_NOT_INHERIT'})
        for key in ('OPENAI_API_KEY', 'KWG_GOLD_MCP_TOKEN', 'LANGCHAIN_MODEL_NAME',
                    'MT5_DEMO_LOGIN', 'CODEX_HOME'):
            self.assertNotIn(key, env)
        self.assertEqual(env['USERPROFILE'], str(root / 'profile'))
        self.assertEqual(env['VIBE_TRADING_HOME'], str(root / 'profile/.vibe-trading'))
        self.assertEqual(env['LANGCHAIN_PROVIDER'], 'openai-codex')
        self.assertEqual(env['VIBE_TRADING_ENABLE_SCHEDULER'], '0')
        self.assertEqual(env['VIBE_TRADING_ENABLE_SHELL_TOOLS'], '0')
        self.assertEqual(env['VIBE_TRADING_CHANNELS_AUTO_START'], '0')
        args = workspace.product_args('login', root)
        self.assertEqual(args[-3:], ['provider', 'login', 'openai-codex'])
        self.assertIn('--host', workspace.product_args('serve', root))
        self.assertIn('127.0.0.1', workspace.product_args('serve', root))

    def test_added_importable_source_rejects_pin_verification(self):
        path = Path(__file__).with_name('vibe-workspace.py')
        spec = importlib.util.spec_from_file_location('vibe_workspace', path)
        workspace = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workspace)
        self.assertTrue(hasattr(workspace, 'verify_source'))
        for extra in ('agent/cli/added.py\0', 'agent/cli/added.pyc\0', 'agent/cli/added.pyd\0'):
            results = [SimpleNamespace(stdout=workspace.PIN, returncode=0),
                       SimpleNamespace(stdout='', returncode=0),
                       SimpleNamespace(stdout=extra, returncode=0),
                       SimpleNamespace(stdout='', returncode=0)]
            with patch.object(workspace.subprocess, 'run', side_effect=results):
                self.assertFalse(workspace.verify_source(Path('synthetic')))


if __name__ == '__main__':
    unittest.main()
