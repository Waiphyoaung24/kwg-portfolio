"""Exercise the desktop launcher without starting a desktop or touching MT5."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('desktop.sh')


class DesktopTest(unittest.TestCase):
    def test_vnc_requires_provisioned_password_and_uses_it(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            commands = home / 'bin'
            commands.mkdir()
            for name in ('Xvfb', 'xdpyinfo', 'openbox', 'websockify', 'wine'):
                stub = commands / name
                stub.write_text('#!/bin/sh\nexit 0\n')
                stub.chmod(0o700)
            stub = commands / 'x11vnc'
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$HOME/vnc-args"\n')
            stub.chmod(0o700)
            env = {'PATH': str(commands) + os.pathsep + os.defpath, 'HOME': root,
                   'DISPLAY': ':99', 'WINEPREFIX': str(home / 'wine')}
            missing = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('VNC password', missing.stderr)
            self.assertFalse((home / 'vnc-args').exists())
            password = home / '.vnc' / 'passwd'
            password.parent.mkdir()
            password.write_bytes(b'fake-password-file')
            password.chmod(0o600)
            ready = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(ready.returncode, 0, ready.stderr)
            args = (home / 'vnc-args').read_text().splitlines()
            self.assertNotIn('-nopw', args)
            self.assertEqual(args[args.index('-rfbauth') + 1], str(password))


if __name__ == '__main__':
    unittest.main()
