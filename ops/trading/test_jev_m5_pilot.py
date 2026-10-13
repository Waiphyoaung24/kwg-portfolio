import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace as Record
import unittest
from unittest.mock import Mock, patch

import demo_pilot as pilot
import jev_m5
import mt5_data
from mt5_data import BrokerUnavailable
from test_demo_one_shot import fake_mt5, NOW  # NOW is also on the M5 grid
from test_jev_m5 import receipt
import test_demo_pilot



class JevM5PilotTest(unittest.TestCase):
    # Reuse the PilotTest harness without re-running its tests.
    start, fill = test_demo_pilot.PilotTest.start, test_demo_pilot.PilotTest.fill

    def setUp(self):
        test_demo_pilot.PilotTest.setUp(self)
        self.feed = Path(self.temp.name) / 'jev-m5.json'
        self.receipts = Path(self.temp.name) / 'jev-m5-receipts.sqlite3'
        for p in (patch.object(pilot, 'JEV_FEED', self.feed), patch.object(pilot, 'RECEIPTS', self.receipts)):
            p.start()
            self.addCleanup(p.stop)

    def activate_m5(self, mode='shadow'):
        self.start()
        p = pilot.state(self.db)
        p.update(strategy=pilot.M5_JEV_STRATEGY, code=pilot.identity())
        if mode is not None:
            p['jev_mode'] = mode
        pilot.save(self.db, p)

    def tick(self, stamp, *, signal='long', allowed=True, **kwargs):
        # PilotTest.tick plus atr14, so the real Jev state can be built.
        self.clock = stamp
        self.mt5.symbol_info_tick.return_value.time = stamp
        self.mt5.symbol_info_tick.return_value.time_msc = stamp * 1000
        seconds = pilot.candle_seconds(pilot.state(self.db))
        self.mt5.copy_rates_from_pos.return_value = [dict(time=(stamp // seconds - 250 + i) * seconds,
            open=100, high=101, low=99, close=100) for i in range(250)]
        with patch('demo_pilot.evaluate', return_value={'bar_time': stamp // seconds * seconds - seconds,
                   'signal': signal, 'reason': 'evaluated', 'ema20': {'long': 101, 'short': 99}.get(signal, 100),
                   'ema50': 100, 'atr14': 2.0}), \
                patch('demo_pilot.entry_allowed', return_value=allowed):
            return pilot.poll_once(self.mt5, self.db, 123, stamp, self.pause, **kwargs)

    def rows(self):
        return [tuple(r) for r in self.db.execute(
            'SELECT bar_time, side, input_sha256, submitted, reason FROM jev_candidates ORDER BY bar_time')]

    def provenance(self):
        return [tuple(r) for r in self.db.execute('SELECT jev_mode, attempt FROM jev_candidates ORDER BY bar_time')]

    def test_m5_candle_cooldown_trend_and_sources(self):
        self.activate_m5()
        p = pilot.state(self.db)
        self.assertEqual(pilot.candle_seconds(p), 300)
        self.assertTrue(pilot.trending(p))
        self.assertIn('jev_m5.py', pilot.SOURCES)
        for strategy in (pilot.TREND_STRATEGY, pilot.BTC_STRATEGY, pilot.BTC_SCALP_STRATEGY):
            self.assertTrue(pilot.trending({'strategy': strategy}))
        for strategy in (pilot.STRATEGY, pilot.M1_STRATEGY):
            self.assertFalse(pilot.trending({'strategy': strategy}))
        self.assertFalse(pilot.trending(None))
        db = Mock(execute=lambda *a: Mock(fetchone=lambda: (NOW,)))
        self.assertEqual(pilot.cooldown_remaining(db, p, NOW + 1), 299)

    def test_shadow_trades_like_trend_publishes_and_journals_candidate(self):
        self.activate_m5()
        self.fill()
        self.tick(NOW + 300, bootstrap=True)                       # baseline candle
        baseline = json.loads(self.feed.read_text())
        self.assertEqual(baseline, {'status': 'ready', 'checked_at': NOW + 300, 'candidate': False,
                                    'bar_time': NOW})
        self.mt5.order_send.assert_not_called()
        report = self.tick(NOW + 600)                               # candidate
        self.assertEqual(report['execution']['status'], 'open')     # shadow never blocks
        feed = json.loads(self.feed.read_text())
        self.assertEqual(set(feed), {'status', 'checked_at', 'candidate', 'bar_time', 'state_json', 'input_sha256', 'bid', 'ask'})
        self.assertTrue(feed['candidate'])
        state = json.loads(feed['state_json'])
        self.assertEqual(state['bar_time'], NOW + 300)
        # The digest binds the exact published bytes, which are the canonical form of the state.
        self.assertEqual(feed['input_sha256'], hashlib.sha256(feed['state_json'].encode()).hexdigest())
        self.assertEqual(feed['input_sha256'], pilot.jev_m5.input_sha256(state))
        self.assertEqual(feed['state_json'], json.dumps(state, sort_keys=True, separators=(',', ':')))
        self.assertEqual(self.rows(), [(NOW + 300, 'long', feed['input_sha256'], 1, None)])
        self.assertEqual(report['pilot']['strategy'], pilot.M5_JEV_STRATEGY)
        self.assertEqual(report['pilot']['jev_mode'], 'shadow')
        self.tick(NOW + 605)                                        # same candle: no repeat
        self.tick(NOW + 900)                                        # open position: not a candidate
        self.assertFalse(json.loads(self.feed.read_text())['candidate'])
        self.assertEqual(self.mt5.order_send.call_count, 1)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.provenance(), [('shadow', self.db.execute('SELECT id FROM attempts').fetchone()[0])])

    def test_open_state_migrates_old_candidate_table(self):
        path = Path(self.temp.name) / 'old.sqlite3'
        db = pilot.open_state(path, 123)
        with db:
            db.execute('DROP TABLE jev_candidates')
            db.execute('CREATE TABLE jev_candidates (bar_time INTEGER PRIMARY KEY, side TEXT NOT NULL, '
                       'input_sha256 TEXT NOT NULL, submitted INTEGER NOT NULL, reason TEXT)')
            db.execute("INSERT INTO jev_candidates VALUES (1, 'long', '', 0, 'old')")
        db.close()
        db = pilot.open_state(path, 123)
        self.addCleanup(db.close)
        pilot.journal_jev(db, dict(bar_time=2, side='short', input_sha256='', error=None, attempt=None,
                                   jev_mode='shadow'), 'new')
        self.assertEqual([tuple(r) for r in db.execute('SELECT bar_time, reason, jev_mode, attempt FROM jev_candidates')],
                         [(1, 'old', None, None), (2, 'new', 'shadow', None)])

    def test_shadow_journals_unsubmitted_candidate_with_reason(self):
        self.activate_m5()
        self.tick(NOW + 300, bootstrap=True)
        self.mt5.order_check.return_value = Record(retcode=10019)
        report = self.tick(NOW + 600)
        self.assertNotEqual(report['execution']['status'], 'open')
        (bar_time, side, digest, submitted, reason), = self.rows()
        self.assertEqual((bar_time, side, submitted), (NOW + 300, 'long', 0))
        self.assertEqual(len(digest), 64)
        self.assertTrue(reason)

    def candidate_tick(self):
        self.activate_m5()
        self.tick(NOW + 300, bootstrap=True)
        return self.tick(NOW + 600)

    def test_unknown_broker_outcome_counts_as_submitted(self):
        self.mt5.order_send.return_value = None
        report = self.candidate_tick()
        self.assertEqual(report['execution']['status'], 'needs_attention')
        self.mt5.order_send.assert_called_once()
        (_, _, _, submitted, reason), = self.rows()
        self.assertEqual(submitted, 1)
        self.assertTrue(reason.startswith('needs_attention'))

    def test_broker_unavailable_after_send_counts_as_submitted(self):
        self.activate_m5()
        p = pilot.state(self.db)
        p.update(run_policy='continuous', end=None)
        pilot.save(self.db, p)
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        with patch('demo_one_shot._reconcile', side_effect=BrokerUnavailable('Broker reconciliation data unavailable.')):
            report = self.tick(NOW + 600)
        self.mt5.order_send.assert_called_once()
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(self.rows()[0][3:], (1, 'Broker reconciliation data unavailable.'))

    def test_guard_refusal_before_send_is_not_submitted(self):
        def pause(request):
            self.pause.write_text('owner pause')
            return Record(retcode=0)
        self.mt5.order_check.side_effect = pause
        report = self.candidate_tick()
        self.mt5.order_send.assert_not_called()
        self.assertEqual(report['execution']['status'], 'disarmed')
        self.assertEqual(self.rows()[0][3:], (0, 'disarmed: Pause or expiry before submission'))

    def test_exception_after_arm_is_journaled_unsubmitted(self):
        original = pilot.execution.process_once
        def process(*args, **kwargs):
            if kwargs.get('before_submit'):
                raise ValueError('Unexpected entry failure')
            return original(*args, **kwargs)
        self.activate_m5()
        self.tick(NOW + 300, bootstrap=True)
        with patch.object(pilot.execution, 'process_once', side_effect=process):
            report = self.tick(NOW + 600)
        self.assertEqual((report['status'], report['reason']), ('blocked', 'Unexpected entry failure'))
        self.assertEqual(self.rows()[0][3:], (0, 'Unexpected entry failure'))

    def test_journal_failure_never_disrupts_the_runner(self):
        self.activate_m5()
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        self.db.execute('DROP TABLE jev_candidates')
        report = self.tick(NOW + 600)
        self.assertEqual(report['execution']['status'], 'open')

    def test_unexpected_state_error_never_blocks_shadow_trading(self):
        self.activate_m5()
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        with patch('demo_pilot.jev_m5.state', side_effect=KeyError('atr14')):
            report = self.tick(NOW + 600)
        self.assertEqual(report['execution']['status'], 'open')
        self.assertEqual(self.rows()[0][2:4], ('', 1))

    def test_feed_failure_never_blocks_shadow_trading(self):
        self.activate_m5()
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        with patch.object(pilot, 'JEV_FEED', Path(self.temp.name) / 'missing' / 'jev-m5.json'):
            report = self.tick(NOW + 600)
        self.assertEqual(report['execution']['status'], 'open')
        (_, _, digest, submitted, reason), = self.rows()
        self.assertEqual((len(digest), submitted), (64, 1))
        self.assertIn('Jev feed unavailable', reason)

    def test_invalid_state_never_blocks_shadow_trading(self):
        self.activate_m5()
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        with patch('demo_pilot.jev_m5.state', side_effect=ValueError('Need 50 completed M5 bars')):
            report = self.tick(NOW + 600)
        self.assertEqual(report['execution']['status'], 'open')
        self.assertEqual(self.rows(), [(NOW + 300, 'long', '', 1,
                                        'Jev feed unavailable: Need 50 completed M5 bars')])

    def assert_paused(self, mode, reason):
        self.activate_m5(mode)
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        report = self.tick(NOW + 600)
        self.assertEqual((report['status'], report['reason']), ('blocked', reason))
        self.assertEqual(pilot.state(self.db)['pause'], reason)
        self.mt5.order_send.assert_not_called()
        self.assertEqual(self.rows(), [])

    def test_missing_mode_pauses_without_orders(self):
        self.assert_paused(None, 'Invalid Jev mode')

    def test_unknown_mode_pauses_without_orders(self):
        self.assert_paused('live', 'Invalid Jev mode')

    def test_other_strategies_never_publish_feed_or_jev_mode(self):
        self.start()
        p = pilot.state(self.db)
        p['strategy'] = pilot.TREND_STRATEGY
        pilot.save(self.db, p)
        self.fill()
        self.tick(NOW, bootstrap=True)
        report = self.tick(NOW + 60)
        self.assertEqual(report['execution']['status'], 'open')
        self.assertFalse(self.feed.exists())
        self.assertNotIn('jev_mode', report['pilot'])
        self.assertEqual(self.rows(), [])

    def test_refresh_keeps_matching_candidate_visible_until_deadline(self):
        bar, digest = NOW + 300, 'a' * 64
        self.feed.write_text(json.dumps(dict(status='ready', checked_at=NOW + 600, candidate=True, bar_time=bar,
                                             state_json='{}', input_sha256=digest, bid=1, ask=2)))
        checked = lambda: json.loads(self.feed.read_text())['checked_at']
        pilot.refresh_jev(bar, 'b' * 64, NOW + 610)                 # other input
        pilot.refresh_jev(bar + 300, digest, NOW + 610)            # other candle
        self.assertEqual(checked(), NOW + 600)
        pilot.refresh_jev(bar, digest, NOW + 650.7)
        self.assertEqual(checked(), NOW + 650)
        self.assertEqual(json.loads(self.feed.read_text())['input_sha256'], digest)
        pilot.refresh_jev(bar, None, NOW + 690)                    # shadow: matches the published candle
        self.assertEqual(checked(), NOW + 690)
        pilot.refresh_jev(bar, digest, NOW + 691)                  # after the Jev deadline
        self.assertEqual(checked(), NOW + 690)
        self.feed.write_text(json.dumps(dict(status='ready', checked_at=NOW, candidate=False, bar_time=bar)))
        pilot.refresh_jev(bar, None, NOW + 610)
        self.assertEqual(checked(), NOW)

    def test_refresh_never_raises(self):
        pilot.refresh_jev(NOW, 'a' * 64, NOW + 10)                 # missing feed
        self.feed.write_text('{not json')
        pilot.refresh_jev(NOW, 'a' * 64, NOW + 10)
        self.feed.write_text('[]')
        pilot.refresh_jev(NOW, 'a' * 64, NOW + 10)
        self.assertEqual(self.feed.read_text(), '[]')

    def test_shadow_polls_refresh_candidate_feed_until_deadline(self):
        self.activate_m5()
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        self.tick(NOW + 600)
        self.assertEqual(json.loads(self.feed.read_text())['bar_time'], NOW + 300)
        self.tick(NOW + 630)
        feed = json.loads(self.feed.read_text())
        self.assertEqual((feed['candidate'], feed['checked_at']), (True, NOW + 630))
        self.tick(NOW + 691)
        self.assertEqual(json.loads(self.feed.read_text())['checked_at'], NOW + 630)

    def test_feed_refresh_continues_after_shadow_trade_opens(self):
        self.activate_m5()
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        self.assertEqual(self.tick(NOW + 600)['execution']['status'], 'open')
        bar = NOW + 300
        digest = json.loads(self.feed.read_text())['input_sha256']
        for stamp in (NOW + 620, bar + 390):                        # same candle, position open
            report = self.tick(stamp)
            self.assertEqual(report['execution']['status'], 'open')
            feed = json.loads(self.feed.read_text())
            self.assertEqual((feed['candidate'], feed['bar_time'], feed['input_sha256'], feed['checked_at']),
                             (True, bar, digest, stamp))
        self.tick(bar + 391)                                        # past the Jev deadline
        self.assertEqual(json.loads(self.feed.read_text())['checked_at'], bar + 390)
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_read_gold_maps_m5_timeframe(self):
        mt5 = fake_mt5(enabled=True)
        mt5.TIMEFRAME_M5 = 5
        stamp = NOW + 300
        mt5.symbol_info_tick.return_value.time = stamp
        mt5.symbol_info_tick.return_value.time_msc = stamp * 1000
        mt5.copy_rates_from_pos.return_value = [dict(time=(stamp // 300 - 250 + i) * 300,
            open=100, high=101, low=99, close=100) for i in range(250)]
        _, bars = mt5_data.read_gold(mt5, 123, stamp, execution=True, bar_seconds=300, trend_demo=True)
        self.assertEqual(mt5.copy_rates_from_pos.call_args[0][1], 5)
        self.assertIs(type(bars[-1]['time']), int)


class JevVetoTest(unittest.TestCase):
    setUp, start, fill = JevM5PilotTest.setUp, JevM5PilotTest.start, JevM5PilotTest.fill
    activate_m5, tick, rows = JevM5PilotTest.activate_m5, JevM5PilotTest.tick, JevM5PilotTest.rows
    provenance = JevM5PilotTest.provenance

    # Candidate candle closes at T = NOW + 600 (bar_time NOW + 300); deadline T + 90.
    def pending(self, signal='long'):
        self.activate_m5('veto')
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        report = self.tick(NOW + 600, signal=signal)
        self.mt5.order_send.assert_not_called()
        return report

    def store(self, choice='buy', completed=NOW + 620, digest=None):
        digest = digest or pilot.state(self.db)['pending_entry']['input_sha256']
        jev_m5.store_receipt(self.receipts, receipt(choice, completed=completed, bar_time=NOW + 300,
                                                    input_sha256=digest), received=completed)

    def test_candidate_defers_and_agreeing_receipt_submits_next_poll(self):
        report = self.pending()
        self.assertEqual(report['reason'], 'Waiting for Jev')
        pending = pilot.state(self.db)['pending_entry']
        feed = json.loads(self.feed.read_text())
        self.assertTrue(feed['candidate'])
        self.assertEqual(pending, {'bar_time': NOW + 300, 'side': 'long', 'input_sha256': feed['input_sha256']})
        self.assertEqual(self.rows(), [])
        self.store()
        report = self.tick(NOW + 630)
        self.assertEqual(report['execution']['status'], 'open')
        self.mt5.order_send.assert_called_once()
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.assertEqual(self.rows(), [(NOW + 300, 'long', pending['input_sha256'], 1, None)])
        self.assertEqual(self.provenance(), [('veto', self.db.execute('SELECT id FROM attempts').fetchone()[0])])
        self.tick(NOW + 640)
        self.mt5.order_send.assert_called_once()

    def test_waiting_entry_refreshes_candidate_feed(self):
        self.pending()
        self.assertEqual(self.tick(NOW + 650)['reason'], 'Waiting for Jev')
        feed = json.loads(self.feed.read_text())
        self.assertEqual((feed['candidate'], feed['bar_time'], feed['checked_at']), (True, NOW + 300, NOW + 650))

    def test_hold_receipt_drops_entry(self):
        self.pending()
        self.store('hold')
        self.tick(NOW + 630)
        self.mt5.order_send.assert_not_called()
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.assertEqual(self.rows()[0][3:], (0, 'Jev chose hold'))
        self.assertEqual(self.provenance(), [('veto', None)])

    def test_no_receipt_by_deadline_drops_entry(self):
        self.pending()
        self.assertEqual(self.tick(NOW + 690)['reason'], 'Waiting for Jev')
        self.tick(NOW + 691)
        self.mt5.order_send.assert_not_called()
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.assertEqual(self.rows()[0][3:], (0, 'No Jev receipt'))

    def test_receipt_for_other_input_drops_entry(self):
        self.pending()
        self.store(digest='b' * 64)
        self.tick(NOW + 630)
        self.mt5.order_send.assert_not_called()
        self.assertEqual(self.rows()[0][3:], (0, 'Receipt is for another candle'))

    def test_new_candle_drops_pending_without_replay(self):
        self.pending()
        self.store()
        self.tick(NOW + 900)              # next candle: the old receipt must not be replayed
        self.mt5.order_send.assert_not_called()
        self.assertEqual(self.rows()[0][0::3], (NOW + 300, 0))
        self.assertEqual(self.rows()[0][4], 'Jev receipt missed the 90-second deadline')
        self.assertEqual(pilot.state(self.db)['pending_entry']['bar_time'], NOW + 600)

    def test_pause_drops_pending(self):
        self.pending()
        self.store()
        self.pause.write_text('owner pause')
        self.tick(NOW + 630)
        self.mt5.order_send.assert_not_called()
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.assertEqual(self.rows()[0][3:], (0, 'Paused by owner'))

    def test_signal_change_drops_pending(self):
        self.pending()
        self.store()
        self.tick(NOW + 630, signal='short')
        self.mt5.order_send.assert_not_called()
        self.assertEqual(self.rows()[0][3:], (0, 'Signal changed'))

    def test_jev_never_originates(self):
        self.pending(signal='none')
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.store(digest='a' * 64)
        self.tick(NOW + 630, signal='none')
        self.tick(NOW + 640, signal='long')
        self.mt5.order_send.assert_not_called()
        self.assertEqual(self.rows(), [])

    def test_receipt_read_error_keeps_waiting_until_valid(self):
        self.pending()
        self.store()
        with patch('demo_pilot.jev_m5.load_receipt', side_effect=sqlite3.OperationalError('database is locked')):
            self.assertEqual(self.tick(NOW + 630)['reason'], 'Waiting for Jev')
        self.mt5.order_send.assert_not_called()
        self.assertEqual(self.tick(NOW + 640)['execution']['status'], 'open')
        self.assertEqual(self.rows()[0][3], 1)

    def test_restart_drops_pending(self):
        self.pending()
        self.store()
        self.tick(NOW + 700, bootstrap=True)
        self.mt5.order_send.assert_not_called()
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.assertEqual(self.rows()[0][3:], (0, 'Runner restarted'))

    def test_state_failure_fails_closed(self):
        self.activate_m5('veto')
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        with patch('demo_pilot.jev_m5.state', side_effect=ValueError('Need 50 completed M5 bars')):
            self.tick(NOW + 600)
        self.mt5.order_send.assert_not_called()
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.assertEqual(self.rows(), [(NOW + 300, 'long', '', 0, 'Jev feed unavailable: Need 50 completed M5 bars')])

    def test_exposure_while_waiting_drops_entry(self):
        self.pending()
        self.store()
        self.mt5.positions_get.return_value = (Record(ticket=5, symbol='XAUUSD-VIP'),)
        self.tick(NOW + 630)
        self.mt5.order_send.assert_not_called()
        self.assertNotIn('pending_entry', pilot.state(self.db))
        self.assertEqual(self.rows()[0][3:], (0, 'Account exposure blocks another entry'))

    def test_shadow_ignores_disagreeing_receipt(self):
        self.activate_m5('shadow')
        self.fill()
        self.tick(NOW + 300, bootstrap=True)
        jev_m5.store_receipt(self.receipts, receipt('sell', completed=NOW + 300, bar_time=NOW + 300),
                             received=NOW + 300)
        self.assertEqual(self.tick(NOW + 600)['execution']['status'], 'open')
        self.mt5.order_send.assert_called_once()

    def test_deadline_rechecked_at_submission(self):
        self.pending()
        self.store()
        def late(request):
            self.clock = NOW + 691
            return Record(retcode=0)
        self.mt5.order_check.side_effect = late
        self.tick(NOW + 630)
        self.mt5.order_send.assert_not_called()
        self.assertEqual(self.rows()[0][3:], (0, 'disarmed: Jev deadline passed before submission'))

    def test_corrupt_receipt_keeps_waiting(self):
        self.pending()
        with sqlite3.connect(self.receipts) as db:
            db.execute('CREATE TABLE receipts (bar_time INTEGER PRIMARY KEY, received REAL NOT NULL, payload TEXT NOT NULL)')
            db.execute('INSERT INTO receipts VALUES (?, ?, ?)', (NOW + 300, NOW + 620, '{corrupt'))
        self.assertEqual(self.tick(NOW + 630)['reason'], 'Waiting for Jev')
        self.mt5.order_send.assert_not_called()
