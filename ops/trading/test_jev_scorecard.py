import json
from pathlib import Path
import tempfile
import unittest

import jev_research as research
from jev_scorecard import export, publish
from test_observe_gold import history
from test_simulate_gold import SPEC


class ScorecardTest(unittest.TestCase):
    def test_export_preserves_frozen_journal_and_pending_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'journal.sqlite3'
            db = research.open_journal(path, SPEC)
            research.capture(db, history(250), 100, 100.01, 251*900, 'baseline')
            bars = history(251); bars[-1]['close'] = 101
            research.capture(db, bars, 100, 100.01, 252*900, 'observed')
            db.close()
            before = path.read_bytes()
            result = export(path, 252*900+1)
            self.assertEqual(result['outcomes'][0]['outcome'], 'pending')
            self.assertIsNone(result['outcomes'][0]['trade'])
            self.assertTrue(result['outcomes'][0]['sample']['eligible'])
            self.assertEqual(path.read_bytes(), before)

    def test_missing_journal_is_not_created_and_clears_old_results(self):
        with tempfile.TemporaryDirectory() as folder:
            path, output = Path(folder)/'missing.sqlite3', Path(folder)/'report.json'
            output.write_text('{"status":"ready"}')
            publish(path, output)
            self.assertFalse(path.exists())
            self.assertEqual(json.loads(output.read_text())['status'], 'unavailable')

    def test_changed_sample_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'journal.sqlite3'
            db = research.open_journal(path, SPEC)
            bars = history(250); bars[-1]['close'] = 101
            research.capture(db, bars, 100, 100.01, 251*900, 'observed')
            sample = json.loads(db.execute('SELECT payload FROM samples').fetchone()[0])
            sample['ask'] += 1
            db.execute('UPDATE samples SET payload=?', (json.dumps(sample),)); db.commit(); db.close()
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                export(path)
