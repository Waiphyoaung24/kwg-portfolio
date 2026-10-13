"""Every staged list that ships the runner or control server also ships jev_m5.py."""
from pathlib import Path
import re
import unittest

HERE = Path(__file__).parent
SHIPPED = ("'demo_pilot.py'", '"demo_pilot.py"', "'control_server.py'", '"control_server.py"')
# One bracketed group without nested brackets: a PowerShell @(...) array, Python tuple/list or set.
GROUP = re.compile(r'[(\[{][^()\[\]{}]*[)\]}]')


def offenders(text):
    found = []
    for match in GROUP.finditer(text):
        group = match.group(0)
        # demo_pilot.SOURCES lists jev_m5.py (asserted below), so spreading it ships the module.
        if '*pilot.SOURCES' in group:
            continue
        if any(name in group for name in SHIPPED) and "'jev_m5.py'" not in group and '"jev_m5.py"' not in group:
            found.append(group)
    return found


class StagingListTest(unittest.TestCase):
    def test_lists_shipping_runner_or_control_server_include_jev_m5(self):
        files = [p for p in sorted(HERE.glob('*.py')) + sorted(HERE.glob('*.ps1')) if not p.name.startswith('test_')]
        checked = set()
        for path in files:
            text = path.read_text(encoding='utf-8')
            if any(name in text for name in SHIPPED):
                checked.add(path.name)
            with self.subTest(file=path.name):
                self.assertEqual(offenders(text), [])
        # The scan must actually reach the known staging scripts.
        self.assertLessEqual({'deploy-demo-pilot.py', 'deploy-demo-pilot.ps1', 'stage-m1-pilot.ps1',
                              'stage-two-symbol-pilot.ps1', 'stage-m5-jev.ps1', 'switch-pilot-m5.py'}, checked)

    def test_runner_identity_sources_include_jev_m5(self):
        import demo_pilot
        self.assertIn('jev_m5.py', demo_pilot.SOURCES)

    def test_dockerfile_copies_jev_m5_with_the_runner(self):
        copies = [line for line in (HERE / 'Dockerfile').read_text().splitlines() if line.startswith('COPY ')]
        runner = next(line for line in copies if ' demo_pilot.py ' in line)
        self.assertIn(' jev_m5.py ', runner)
        self.assertTrue(any(' control_server.py ' in line for line in copies))

    def test_scanner_flags_a_list_without_jev_m5(self):
        self.assertEqual(len(offenders("$names = @('demo_pilot.py','mt5_data.py')")), 1)
        self.assertEqual(offenders("sources = ('demo_pilot.py', 'jev_m5.py')"), [])
        self.assertEqual(offenders("args == [b'/opt/trading/demo_pilot.py', b'run']"), [])


if __name__ == '__main__':
    unittest.main()
