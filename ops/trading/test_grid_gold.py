import copy
import json
import subprocess
import sys
import tempfile
import math
from pathlib import Path
import runpy
import unittest

from gold_experiment import prepare_experiment, source_hashes

grid = runpy.run_path(str(Path(__file__).with_name('grid-gold.py')))['grid']
SPEC = dict(point=.01, trade_contract_size=100, trade_tick_size=.01,
            volume_min=.01, volume_max=100, volume_step=.01, currency_profit='USD')


def dataset(n):
    bars = [dict(time=(i + 1) * 900, open=2000 + 20 * math.sin(i / 15),
                 high=2001 + 20 * math.sin(i / 15), low=1999 + 20 * math.sin(i / 15),
                 close=2000 + 20 * math.sin((i + 1) / 15), spread=20) for i in range(n)]
    for bar in bars:
        bar['high'] = max(bar['high'], bar['open'], bar['close'])
        bar['low'] = min(bar['low'], bar['open'], bar['close'])
    return {'schema_version': 1, 'symbol': 'XAUUSD-VIP', 'timeframe': 'M15',
            'source': {'start_pos': 1}, 'captured_at': (n + 2) * 900,
            'current_contract_specification': SPEC, 'bars': bars}


class GridTest(unittest.TestCase):
    def setUp(self):
        self.data = dataset(10000)
        self.manifest = prepare_experiment(self.data, 'a' * 64, source_hashes())
        self.manifest['status'] = 'frozen'

    def test_grid_never_evaluates_validation_or_reserved_bars_and_is_deterministic(self):
        self.data['bars'][6000:] = [None] * 4000
        first = grid(self.data, self.manifest)
        self.assertEqual([r['lookback_bars'] for r in first['rows']], [None, 2, 3, 4, 5])
        self.assertEqual(first['dev_end_index'], 6000)
        self.assertEqual(first['qualification'], 'unqualified')
        self.assertIn(first['selected'], (None, 2, 3, 4, 5))
        self.assertEqual(first, grid(self.data, self.manifest))
        self.assertEqual(first['identity']['dataset_sha256'], 'a' * 64)
        self.assertEqual(len(first['grid_sha256']), 64)

    def test_rejects_unfrozen_or_mismatched_manifest_and_short_dataset(self):
        bad = []
        for key, value in [('status', 'prepared'), ('reserved_start_index', 6000),
                           ('code_sha256', {}), ('risk', {}), ('scenarios', {})]:
            bad.append(self.manifest | {key: value})
        changed = copy.deepcopy(self.manifest)
        changed['windows']['development']['end'] = self.data['bars'][6999]['time']
        bad.append(changed)
        for manifest in bad:
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                grid(self.data, manifest)
        with self.assertRaises(ValueError):
            grid(self.data | {'bars': self.data['bars'][:5999]}, self.manifest)

    def test_cli_rejects_wrong_dataset_hash_without_creating_report(self):
        with tempfile.TemporaryDirectory() as root:
            data, manifest, output = (Path(root) / name for name in ('data.json', 'manifest.json', 'grid.json'))
            data.write_text(json.dumps(self.data))
            manifest.write_text(json.dumps(self.manifest))
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('grid-gold.py')),
                '--dataset', str(data), '--manifest', str(manifest), '--output', str(output)],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Dataset checksum mismatch', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
