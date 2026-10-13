import json
from pathlib import Path
from types import SimpleNamespace as Record
import unittest
from unittest.mock import Mock, patch

import demo_pilot as pilot
import mt5_data
from test_demo_one_shot import fake_mt5, NOW  # NOW is also on the M5 grid
import test_demo_pilot



class JevM5PilotTest(unittest.TestCase):
    # Reuse the PilotTest harness without re-running its tests.
    start, fill = test_demo_pilot.PilotTest.start, test_demo_pilot.PilotTest.fill

    def setUp(self):
        test_demo_pilot.PilotTest.setUp(self)
        self.feed = Path(self.temp.name) / 'jev-m5.json'
        p = patch.object(pilot, 'JEV_FEED', self.feed)
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
                   'signal': signal, 'reason': 'evaluated', 'ema20': 101 if signal == 'long' else 99,
                   'ema50': 100, 'atr14': 2.0}), \
                patch('demo_pilot.entry_allowed', return_value=allowed):
            return pilot.poll_once(self.mt5, self.db, 123, stamp, self.pause, **kwargs)

    def rows(self):
        return [tuple(r) for r in self.db.execute('SELECT * FROM jev_candidates ORDER BY bar_time')]

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
        self.assertEqual(set(feed), {'status', 'checked_at', 'candidate', 'state', 'input_sha256', 'bid', 'ask'})
        self.assertTrue(feed['candidate'])
        self.assertEqual(feed['state']['bar_time'], NOW + 300)
        self.assertEqual(feed['input_sha256'], pilot.jev_m5.input_sha256(feed['state']))
        self.assertEqual(self.rows(), [(NOW + 300, 'long', feed['input_sha256'], 1, None)])
        self.assertEqual(report['pilot']['strategy'], pilot.M5_JEV_STRATEGY)
        self.assertEqual(report['pilot']['jev_mode'], 'shadow')
        self.tick(NOW + 605)                                        # same candle: no repeat
        self.tick(NOW + 900)                                        # open position: not a candidate
        self.assertFalse(json.loads(self.feed.read_text())['candidate'])
        self.assertEqual(self.mt5.order_send.call_count, 1)
        self.assertEqual(len(self.rows()), 1)

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

    def test_veto_mode_pauses_until_implemented(self):
        self.assert_paused('veto', 'Veto mode not implemented')

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
