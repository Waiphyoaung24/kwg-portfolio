"""Launch the existing local Vibe product using its separate configuration home."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


PIN = 'cc54832cb50de29d14bb10097b18e08f0a843650'
ROOT = Path(__file__).resolve().parents[2] / '.batch3-vibe'


def child_environment(root: Path, inherited: dict) -> dict:
    env = {key: value for key, value in inherited.items()
           if key.upper() in {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP'}}
    profile = root / 'profile'
    env.update(USERPROFILE=str(profile), APPDATA=str(profile / 'AppData/Roaming'),
               LOCALAPPDATA=str(profile / 'AppData/Local'),
               VIBE_TRADING_HOME=str(profile / '.vibe-trading'),
               LANGCHAIN_PROVIDER='openai-codex', MAX_RETRIES='0', TIMEOUT_SECONDS='120',
               VIBE_TRADING_ENABLE_SCHEDULER='0', VIBE_TRADING_ENABLE_SHELL_TOOLS='0',
               VIBE_TRADING_CHANNELS_AUTO_START='0', PYTHONDONTWRITEBYTECODE='1',
               PYTHONIOENCODING='utf-8')
    # Model comes from the workspace settings file, never the parent environment.
    return env


def product_args(action: str, root: Path) -> list:
    agent = str(root / 'upstream/agent')
    prefix = 'import sys; sys.path.insert(0, sys.argv.pop(1)); '
    if action == 'login':
        return ['-B', '-c', prefix + 'from cli.main import _entrypoint; _entrypoint()',
                agent, 'provider', 'login', 'openai-codex']
    return ['-B', '-c', prefix + 'from api_server import serve_main; raise SystemExit(serve_main(sys.argv[1:]))',
            agent, '--host', '127.0.0.1', '--port', '8899']


def verify_source(root: Path) -> bool:
    prefix = ['git', '-C', str(root / 'upstream')]
    pin = subprocess.run([*prefix, 'rev-parse', 'HEAD'],
                         capture_output=True, text=True, check=True).stdout.strip()
    clean = subprocess.run([*prefix, 'diff', '--quiet', 'HEAD', '--', 'agent'],
                           capture_output=True).returncode == 0
    extras = []
    for mode in ([], ['--ignored']):
        result = subprocess.run([*prefix, 'ls-files', '-z', '--others',
                                 '--exclude-standard', *mode, '--', 'agent'],
                                capture_output=True, text=True, check=True)
        extras.extend(result.stdout.split('\0'))
    unexpected = any(Path(name).suffix.lower() in {'.py', '.pyc', '.pyd', '.so', '.dll'}
                     for name in extras if name)
    return pin == PIN and clean and not unexpected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'login', 'serve'))
    args = parser.parse_args()
    python = Path.home() / 'AppData/Roaming/uv/tools/vibe-trading-ai/Scripts/python.exe'
    if not python.is_file() or not (ROOT / 'profile/.vibe-trading').is_dir():
        parser.exit(2, 'Prepared local runtime/workspace is missing.\n')
    if not verify_source(ROOT):
        parser.exit(2, 'Upstream source differs from the prepared product pin.\n')
    if args.action == 'status':
        print(json.dumps({'version': '0.1.15', 'agent_source_pin_verified': True,
            'dependency_and_frontend_integrity_verified': False,
            'url': 'http://127.0.0.1:8899/', 'configuration_home': str(ROOT / 'profile'),
            'oauth_file_present': (ROOT / 'profile/.vibe-trading/auth/openai-codex.json').is_file(),
            'oauth_validity_verified': False, 'os_sandbox': False}))
        return 0
    if args.action == 'login' and not sys.stdin.isatty():
        parser.exit(2, 'Run login in your own interactive terminal; never paste callback URLs into chat.\n')
    return subprocess.run([str(python), *product_args(args.action, ROOT)],
                          cwd=ROOT / 'upstream/agent',
                          env=child_environment(ROOT, os.environ)).returncode


if __name__ == '__main__':
    raise SystemExit(main())
