import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import jev_research as research
from test_observe_gold import fake_sdk, history, observer
from test_simulate_gold import SPEC


class ResearchTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'research.sqlite3'
        self.db = research.open_journal(self.path, SPEC)
        self.addCleanup(self.db.close)

    def capture(self, end=250, status='observed', spike=True):
        bars = history(end)
        previous = self.db.execute('SELECT payload FROM samples ORDER BY bar_time DESC LIMIT 1').fetchone()
        if previous:
            known = {b['time']: b for b in json.loads(previous[0])['bars']}
            bars = [known.get(b['time'], b) for b in bars]
        if spike:
            bars[-1]['close'] = 101
        research.capture(self.db, bars, 100, 100.01, (end+1)*900, status)
        return bars

    def response(self, stamp=250*900, status='ok'):
        sample = json.loads(self.db.execute('SELECT payload FROM samples WHERE bar_time=?', (stamp,)).fetchone()[0])
        return dict(status=status, input_sha256=sample['input_sha256'], model=research.MODEL,
                    prompt_sha256=research.digest(research.PROMPT), decision='positive',
                    probabilities={'positive': .6, 'nonpositive': .3, 'abstain': .1})

    def test_before_slope_filter_no_backfill_and_no_future_candles(self):
        with patch.object(research, 'entry_allowed', return_value=False):
            self.capture()
        sample = json.loads(self.db.execute('SELECT payload FROM samples').fetchone()[0])
        self.assertTrue(sample['eligible'])
        self.assertFalse(sample['slope_pass'])
        self.assertEqual(max(b['time'] for b in sample['bars']), 250*900)
        self.assertEqual(len(research.pending(self.db, 251*900)), 1)
        self.assertEqual(research.pending(self.db, 251*900+16), [])
        with self.assertRaises(ValueError):
            research.capture(self.db, history(), 100, 100.01, 251*900+31, 'observed')
        self.assertFalse(research.capture(self.db, history(), 100, 100.01, 251*900, 'observed'))

    def test_response_identity_deadline_failure_and_immutability(self):
        self.capture()
        bad = self.response(); bad['input_sha256'] = 'wrong'
        with self.assertRaises(ValueError):
            research.record_response(self.db, 250*900, bad, 251*900+1)
        bad = self.response(); bad['probabilities']['positive'] = float('nan')
        with self.assertRaises(ValueError):
            research.record_response(self.db, 250*900, bad, 251*900+1)
        research.record_response(self.db, 250*900, self.response(status='timeout'), 251*900+16)
        with self.assertRaises(sqlite3.IntegrityError):
            research.record_response(self.db, 250*900, self.response(), 251*900+17)
        report = research.report(self.db)
        self.assertEqual(report['outcomes'][0]['jev']['status'], 'timeout')
        self.assertEqual(report['arms']['jev']['selected'], 0)

    def test_restart_keeps_setup_and_configuration_is_frozen(self):
        self.capture()
        self.db.close()
        self.db = research.open_journal(self.path, SPEC)
        self.addCleanup(self.db.close)
        self.assertEqual(research.report(self.db)['eligible'], 1)
        with self.assertRaises(ValueError):
            research.open_journal(self.path, {**SPEC, 'point': .02})

    def test_late_success_excluded_and_timely_success_retained(self):
        self.capture(250, 'baseline', False)
        self.capture(251)
        stamp = 251*900
        research.record_response(self.db, stamp, self.response(stamp), 252*900+16)
        self.assertEqual(research.report(self.db)['arms']['jev']['selected'], 0)
        bars = history(252); bars[-2]['close'] = 101; bars[-1]['close'] = 99
        research.capture(self.db, bars, 99, 99.01, 253*900, 'observed')
        stamp = 252*900
        research.record_response(self.db, stamp, self.response(stamp), 253*900+1)
        report = research.report(self.db)
        self.assertEqual(report['arms']['jev']['selected'], 1)
        self.assertEqual(report['outcomes'][0]['jev']['provenance'], 'imported_unverified')

    def test_revised_candles_rejected(self):
        self.capture()
        with self.assertRaisesRegex(ValueError, 'candles changed'):
            research.capture(self.db, history(251), 100, 100.01, 252*900, 'observed')

    def test_unresolved_window_end_is_not_a_realized_outcome(self):
        self.capture(250, 'baseline', False)
        self.capture(251)
        self.capture(252, 'observed', False)
        result = research.report(self.db)
        self.assertEqual(result['outcomes'][0]['outcome'], 'pending')
        self.assertIsNone(result['outcomes'][0]['trade'])
        self.assertEqual(result['arms']['baseline']['resolved'], 0)
        self.assertEqual(result['missing_responses'], 1)
        # A later completed candle hits the target; all approaches use that same outcome.
        bars = history(253)
        bars[-3]['close'] = 101
        bars[-1].update(high=108, close=107)
        research.capture(self.db, bars, 107, 107.01, 254*900, 'observed')
        resolved = research.report(self.db)['outcomes'][0]
        self.assertEqual(resolved['outcome'], 'resolved')
        self.assertEqual(resolved['trade']['exit_reason'], 'target')
        self.assertGreater(resolved['trade']['net_pnl'], 0)

    def test_missing_candle_censors_outcome(self):
        self.capture(250, 'baseline', False)
        self.capture(251)
        self.capture(253, 'baseline', False)
        result = research.report(self.db)
        self.assertEqual(result['outcomes'][0]['outcome'], 'censored_gap')
        self.assertEqual(result['arms']['baseline']['resolved'], 0)

    def test_observer_integration_keeps_startup_and_orders_guarded(self):
        db = observer.open_state(Path(self.directory.name)/'observer.sqlite3', 123)
        self.addCleanup(db.close)
        sdk = fake_sdk()
        observer.poll_once(sdk, db, 123, 251*900, True, research=self.db)
        sdk = fake_sdk(251)
        sdk.copy_rates_from_pos.return_value[-1]['close'] = 101
        observer.poll_once(sdk, db, 123, 252*900, False, research=self.db)
        observer.poll_once(sdk, db, 123, 252*900, False, research=self.db)
        result = research.report(self.db)
        self.assertEqual((result['samples'], result['eligible']), (2, 1))
        sdk.order_send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
