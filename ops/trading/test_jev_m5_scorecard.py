import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import demo_pilot as pilot
import jev_m5
from jev_m5_scorecard import connect, export, publish
from test_jev_m5 import receipt

BASE = 1_800_000_000 // 300 * 300
LATER = BASE + 10**6  # every synthetic candle is past its Jev deadline


class M5ScorecardTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.journal = self.folder / 'pilot.sqlite3'
        self.receipts = self.folder / 'jev-m5-receipts.sqlite3'
        with patch.dict(os.environ, {'MT5_SERVER_OFFSET_SECONDS': '0'}):
            pilot.open_state(self.journal, 123).close()
        self.n = 0

    def add(self, net=1.0, *, choice='buy', mode='shadow', side='long', receipt_status='ok',
            completed=20, received=None, state=True, closed=True):
        """One candidate with an attempt; completed/received are seconds after candle close."""
        bar = BASE + 300 * self.n
        self.n += 1
        digest = f'{self.n:064x}' if state else ''
        attempt = f'a{self.n}'
        with sqlite3.connect(self.journal) as db:
            db.execute("INSERT INTO attempts (id, side, armed_at, expires_at, state, phase, request_json, "
                       "realized_net_usd) VALUES (?, ?, ?, ?, ?, 'entry', '{}', ?)",
                       (attempt, 'buy', bar + 300, bar + 1200, 'closed' if closed else 'open', net))
            db.execute('INSERT INTO jev_candidates (bar_time, side, input_sha256, submitted, reason, jev_mode, attempt) '
                       'VALUES (?, ?, ?, 1, NULL, ?, ?)', (bar, side, digest, mode, attempt))
        if receipt_status is not None and state:
            ok = receipt_status == 'ok'
            value = receipt(choice, status=receipt_status, bar_time=bar, input_sha256=digest,
                            completed=bar + 300 + completed)
            if not ok:
                value.update(choice=None, confidence=None, probabilities=None)
            jev_m5.store_receipt(self.receipts, value, received=bar + 300 + (completed if received is None else received))

    def test_frontend_contract_fixtures_match_export(self):
        """The dashboard test (src/scripts/trading-jev-m5.test.mjs) maps these exact exports.

        Regenerate after a deliberate scorecard change: REGENERATE_M5_FIXTURES=1 python3 -B -m pytest -q test_jev_m5_scorecard.py
        """
        folder = Path(__file__).parent / 'fixtures'
        cases = {'empty': export(self.journal, self.receipts, now=5)}
        self.add(-3.0, state=False)                                # no Jev state: a bad receipt
        self.add(-3.0, receipt_status='timeout')
        self.add(5.0)
        self.add(-3.0, completed=91)                               # late
        self.add(2.0, closed=False)
        cases['bad-receipt'] = export(self.journal, self.receipts, now=LATER)
        for i in range(56):
            self.add(5.0 if i % 2 else -3.0, choice='buy' if i % 2 else 'hold')
        cases['passing'] = export(self.journal, self.receipts, now=LATER)
        self.assertTrue(cases['passing']['gate']['passes'])
        self.assertIn('Bad receipts 3/5 reach the 20% limit', cases['bad-receipt']['gate']['reasons'])
        for name, value in cases.items():
            path = folder / f'jev-m5-scorecard-{name}.json'
            if os.environ.get('REGENERATE_M5_FIXTURES') == '1':
                path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), value)

    def test_empty_journal_fails_with_three_reasons(self):
        result = export(self.journal, self.receipts, now=5)
        self.assertEqual((result['status'], result['generated_at'], result['candidates']), ('ready', 5, 0))
        self.assertFalse(result['gate']['passes'])
        self.assertEqual(len(result['gate']['reasons']), 3)
        self.assertEqual(result['all'], {'trades': 0, 'avg_net_usd': None})
        self.assertFalse(self.receipts.exists())                   # never created

    def test_fifty_trades_with_kept_advantage_pass(self):
        for i in range(50):
            self.add(5.0 if i % 2 else -3.0, choice='buy' if i % 2 else 'hold')
        result = export(self.journal, self.receipts, now=LATER)
        self.assertEqual(result['closed'], 50)
        self.assertEqual(result['receipts']['ok'], 50)
        self.assertEqual(result['all'], {'trades': 50, 'avg_net_usd': 1.0})
        self.assertEqual(result['jev_kept'], {'trades': 25, 'avg_net_usd': 5.0})
        self.assertEqual(result['jev_vetoed'], {'trades': 25, 'avg_net_usd': -3.0})
        self.assertEqual(result['gate'], {'min_closed': 50, 'bad_receipt_max': .2, 'bad_receipt_rate': 0.0,
                                          'passes': True, 'reasons': []})
        self.assertEqual(result['qualification'], 'demo fills; unqualified; not a profitability claim')

    def test_twenty_percent_bad_receipts_fail(self):
        for i in range(40):
            self.add(5.0 if i % 2 else -3.0, choice='buy' if i % 2 else 'hold')
        for status in ('timeout', 'unavailable', 'budget_exhausted', 'invalid'):
            self.add(-3.0, receipt_status=status)
        self.add(-3.0, receipt_status=None)                        # missing
        for _ in range(5):
            self.add(-3.0, completed=91)                           # late
        result = export(self.journal, self.receipts, now=LATER)
        self.assertEqual(result['receipts'], {'ok': 40, 'timeout': 1, 'unavailable': 1, 'budget_exhausted': 1,
                                              'invalid': 1, 'missing': 1, 'late': 5})
        self.assertEqual(result['gate']['bad_receipt_rate'], .2)
        self.assertFalse(result['gate']['passes'])
        self.assertEqual(len(result['gate']['reasons']), 1)
        self.assertIn('receipts', result['gate']['reasons'][0])

    def test_unresolved_pl_is_excluded_and_counted(self):
        self.add(4.0)
        self.add(None)
        self.add(2.0, closed=False)                                # still open: not closed
        result = export(self.journal, self.receipts, now=LATER)
        self.assertEqual((result['closed'], result['unresolved']), (2, 1))
        self.assertEqual(result['all'], {'trades': 1, 'avg_net_usd': 4.0})

    def test_only_shadow_rows_count_and_stateless_rows_are_separate(self):
        self.add(9.0, mode='veto')
        self.add(1.0, state=False)                                 # Jev state build failed
        self.add(3.0)
        result = export(self.journal, self.receipts, now=LATER)
        self.assertEqual(result['mode_counts'], {'shadow': 2, 'veto': 1})
        self.assertEqual((result['candidates'], result['no_state']), (2, 1))
        self.assertEqual(sum(result['receipts'].values()), 1)      # no-state rows have no receipt bucket
        self.assertEqual(result['gate']['bad_receipt_rate'], .5)   # but count as bad
        self.assertEqual(result['all'], {'trades': 2, 'avg_net_usd': 2.0})
        self.assertEqual(result['jev_vetoed'], {'trades': 1, 'avg_net_usd': 1.0})

    def test_stateless_rows_count_as_bad_receipts(self):
        for i in range(100):
            self.add(5.0, state=bool(i % 2))
        result = export(self.journal, self.receipts, now=LATER)
        self.assertEqual((result['candidates'], result['no_state'], result['receipts']['ok']), (100, 50, 50))
        self.assertEqual(result['gate']['bad_receipt_rate'], .5)
        self.assertFalse(result['gate']['passes'])
        self.assertTrue(any('receipts' in reason for reason in result['gate']['reasons']))

    def test_candidates_inside_their_deadline_are_pending(self):
        self.add(5.0)
        self.add(5.0, receipt_status=None)
        due = BASE + 300 + 300 + jev_m5.DEADLINE                   # second candle's deadline
        result = export(self.journal, self.receipts, now=due - 1)
        self.assertEqual((result['pending'], result['candidates'], result['closed']), (1, 1, 1))
        self.assertEqual(result['receipts']['missing'], 0)
        result = export(self.journal, self.receipts, now=due)
        self.assertEqual((result['pending'], result['candidates'], result['receipts']['missing']), (0, 2, 1))

    def test_receipt_stored_after_the_deadline_is_late_and_vetoed(self):
        self.add(5.0, completed=20, received=91)
        self.add(1.0, completed=20, received=90)
        result = export(self.journal, self.receipts, now=LATER)
        self.assertEqual((result['receipts']['late'], result['receipts']['ok']), (1, 1))
        self.assertEqual(result['jev_kept'], {'trades': 1, 'avg_net_usd': 1.0})
        self.assertEqual(result['jev_vetoed'], {'trades': 1, 'avg_net_usd': 5.0})

    def test_connections_are_read_only_and_leave_the_journal_unchanged(self):
        self.add(1.0)
        before = self.journal.read_bytes()
        export(self.journal, self.receipts, now=LATER)
        self.assertEqual(self.journal.read_bytes(), before)
        with connect(self.journal) as db, self.assertRaises(sqlite3.OperationalError):
            db.execute('DELETE FROM jev_candidates')

    def test_publish_is_atomic_and_reports_unavailable_journal(self):
        output = self.folder / 'jev-m5-scorecard.json'
        publish(self.journal, self.receipts, output)
        self.assertEqual(json.loads(output.read_text())['status'], 'ready')
        missing = self.folder / 'missing.sqlite3'
        publish(missing, self.receipts, output)
        self.assertFalse(missing.exists())
        self.assertEqual(json.loads(output.read_text())['status'], 'unavailable')
        self.assertFalse(output.with_suffix('.tmp').exists())


if __name__ == '__main__':
    unittest.main()
