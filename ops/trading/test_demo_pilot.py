import json
import runpy
from contextlib import closing
import os
import sqlite3
from pathlib import Path
import tempfile
from types import SimpleNamespace as Record
import unittest
from unittest.mock import patch

import demo_pilot as pilot
from test_demo_one_shot import fake_mt5, NOW

recovery = runpy.run_path(str(Path(__file__).with_name('resume-demo-pilot.py')))
migration = runpy.run_path(str(Path(__file__).with_name('switch-pilot-m1.py')))


class PilotTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'pilot.sqlite3'
        self.pause = Path(self.temp.name) / 'pilot.pause'
        self.db = pilot.open_state(self.path, 123)
        self.addCleanup(self.db.close)
        self.mt5 = fake_mt5(enabled=True)
        self.mt5.account_info.return_value.balance = 10000
        self.mt5.history_deals_get.return_value = ()
        self.mt5.order_check.return_value = Record(retcode=0)
        self.clock = NOW
        for p in (patch.dict(os.environ, {'MT5_SERVER_OFFSET_SECONDS': '0'}),
                  patch('time.time', side_effect=lambda: self.clock)):
            p.start()
            self.addCleanup(p.stop)

    def start(self, seconds=3600):
        pilot.activate(self.mt5, self.db, 123, NOW, NOW + seconds, self.pause)

    def tick(self, stamp, *, signal='long', allowed=True, **kwargs):
        self.clock = stamp
        self.mt5.symbol_info_tick.return_value.time = stamp
        self.mt5.symbol_info_tick.return_value.time_msc = stamp * 1000
        seconds = pilot.candle_seconds(pilot.state(self.db))
        self.mt5.copy_rates_from_pos.return_value = [dict(time=(stamp // seconds - 250 + i) * seconds,
            open=100, high=101, low=99, close=100) for i in range(250)]
        with patch('demo_pilot.evaluate', return_value={'bar_time': stamp // seconds * seconds - seconds,
                   'signal': signal, 'reason': 'evaluated'}), \
                patch('demo_pilot.entry_allowed', return_value=allowed):
            return pilot.poll_once(self.mt5, self.db, 123, stamp, self.pause, **kwargs)

    def fill(self):
        def send(request):
            self.mt5.positions_get.return_value = (Record(ticket=77, symbol='XAUUSD-VIP',
                magic=request['magic'], comment=request['comment'], type=request['type'],
                volume=request['volume'], price_open=request['price'], sl=request['sl'],
                tp=request['tp'], profit=0),)
            self.mt5.history_deals_get.return_value = (Record(ticket=78, order=77,
                position_id=77, symbol='XAUUSD-VIP', magic=request['magic'],
                comment=request['comment'], entry=0, type=request['type'], volume=request['volume'],
                price=request['price'], time=self.clock, profit=0, commission=0, swap=0, fee=0),)
            return Record(retcode=10009, order=77, deal=78)
        self.mt5.order_send.side_effect = send

    def test_account_recovery_preserves_risk_window_and_backs_up_pause(self):
        self.start()
        p = pilot.state(self.db)
        p['pause'] = recovery['ACCOUNT_PAUSE']
        pilot.save(self.db, p)
        backup = self.path.with_name('backup.sqlite3')
        result = recovery['resume'](self.mt5, self.db, 123, NOW, self.pause, pilot.identity(), backup)
        for key in ('start', 'end', 'initial_equity', 'initial_balance', 'peak', 'day_equity', 'code'):
            self.assertEqual(result[key], p[key])
        self.assertIsNone(result['pause'])
        self.assertIsNone(result['last_bar'])
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(pilot.state(db)['pause'], recovery['ACCOUNT_PAUSE'])
        self.mt5.order_send.assert_not_called()

    def test_account_recovery_refuses_other_pauses_expiry_exposure_and_changed_code(self):
        self.start()
        original = pilot.state(self.db)
        for change in ({'pause': 'Daily equity loss limit reached'},
                       {'pause': recovery['ACCOUNT_PAUSE'], 'end': NOW},
                       {'pause': recovery['ACCOUNT_PAUSE'], 'code': 'changed'}):
            p = {**original, **change}
            pilot.save(self.db, p)
            with self.assertRaises(ValueError):
                recovery['review'](self.mt5, self.db, 123, NOW, self.pause, pilot.identity())
            self.assertEqual(pilot.state(self.db), p)
        p = {**original, 'pause': recovery['ACCOUNT_PAUSE']}
        pilot.save(self.db, p)
        self.mt5.positions_get.return_value = (Record(ticket=1),)
        with self.assertRaises(ValueError):
            recovery['review'](self.mt5, self.db, 123, NOW, self.pause, pilot.identity())
        self.mt5.positions_get.return_value = ()
        self.pause.write_text('owner pause')
        with self.assertRaises(ValueError):
            recovery['review'](self.mt5, self.db, 123, NOW, self.pause, pilot.identity())
        self.assertEqual(pilot.state(self.db), p)
        self.mt5.order_send.assert_not_called()

    def test_requires_explicit_activation_and_rejects_wrong_or_real_accounts(self):
        self.tick(NOW)
        self.mt5.order_send.assert_not_called()
        for field, value in [('trade_mode', 2), ('login', 456), ('server', 'other')]:
            original = getattr(self.mt5.account_info.return_value, field)
            setattr(self.mt5.account_info.return_value, field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.start()
            setattr(self.mt5.account_info.return_value, field, original)
        with self.assertRaises(ValueError):
            self.start(8 * 86400)
        self.start()
        with self.assertRaises(sqlite3.IntegrityError):
            self.start()

    def test_one_crossover_one_protected_entry_and_persistent_journal(self):
        self.start()
        self.fill()
        self.tick(NOW)
        result = self.tick(NOW + 900)
        self.assertEqual(result['execution']['status'], 'open')
        self.assertEqual(self.mt5.order_send.call_count, 1)

        request = self.mt5.order_send.call_args.args[0]
        self.assertTrue(request['comment'].startswith('kwg-pilot-'))
        self.assertLess(request['sl'], request['price'])
        self.assertGreater(request['tp'], request['price'])
        self.tick(NOW + 905)
        reopened = pilot.open_state(self.path, 123)
        try:
            self.assertEqual(pilot.state(reopened)['last_bar'], NOW)
        finally:
            reopened.close()
        self.tick(NOW + 910, bootstrap=True)
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_m1_uses_completed_minutes_for_signal_and_order_checks(self):
        self.start()
        p = pilot.state(self.db)
        p['strategy'] = pilot.M1_STRATEGY
        pilot.save(self.db, p)
        self.fill()
        self.tick(NOW, bootstrap=True)
        self.mt5.order_send.assert_not_called()
        result = self.tick(NOW + 60)
        self.assertEqual(result['pilot']['strategy'], pilot.M1_STRATEGY)
        self.assertEqual(result['execution']['status'], 'open')
        self.assertTrue(all(call.args[1:] == (1, 1, 250) for call in self.mt5.copy_rates_from_pos.call_args_list[1:]))
        self.tick(NOW + 65)
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_m1_migration_preserves_original_window_and_risk_history(self):
        self.start()
        original = pilot.state(self.db)
        original['code'] = 'previous-reviewed-code'
        pilot.save(self.db, original)
        self.mt5.copy_rates_from_pos.return_value = [dict(time=NOW - (250-i)*60,
            open=100, high=101, low=99, close=100) for i in range(250)]
        inputs = (self.mt5, self.db, 123, NOW, self.pause, original['code'], pilot.identity())
        migration['review'](*inputs)
        self.assertEqual(pilot.state(self.db), original)
        backup = self.path.with_name('before-m1.sqlite3')
        updated = migration['switch'](*inputs, backup)
        for key in ('start', 'end', 'initial_equity', 'initial_balance', 'peak', 'day_equity', 'last_poll'):
            self.assertEqual(updated[key], original[key])
        self.assertEqual(updated['strategy'], pilot.M1_STRATEGY)
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(pilot.state(db), original)
        self.mt5.order_send.assert_not_called()

    def test_m1_migration_cannot_bypass_pause_risk_or_exposure(self):
        self.start()
        original = pilot.state(self.db)
        inputs = (self.mt5, self.db, 123, NOW, self.pause, original['code'], pilot.identity())
        for change in ({'pause': 'Daily equity loss limit reached'}, {'end': NOW}, {'code': 'wrong'}):
            p = {**original, **change}
            pilot.save(self.db, p)
            with self.assertRaises(ValueError):
                migration['review'](*inputs)
            self.assertEqual(pilot.state(self.db), p)
        pilot.save(self.db, original)
        self.mt5.account_info.return_value.equity = 9800
        with self.assertRaises(ValueError):
            migration['review'](*inputs)
        self.mt5.account_info.return_value.equity = 10000
        self.mt5.orders_get.return_value = (Record(ticket=1),)
        with self.assertRaises(ValueError):
            migration['review'](*inputs)
        self.assertEqual(pilot.state(self.db), original)
        self.mt5.order_send.assert_not_called()

    def test_m1_switch_can_wait_for_spread_but_runner_cannot_enter(self):
        self.start()
        original = pilot.state(self.db)
        self.mt5.copy_rates_from_pos.return_value = [dict(time=NOW - (250-i)*60,
            open=100, high=101, low=99, close=100) for i in range(250)]
        self.mt5.symbol_info_tick.return_value.ask = 100.3
        inputs = (self.mt5, self.db, 123, NOW, self.pause, original['code'], pilot.identity())
        p = migration['switch'](*inputs, self.path.with_name('wide-spread-backup.sqlite3'))
        self.assertIn('entry blocked', p['reason'])
        for stamp in (NOW, NOW + 60, NOW + 120):
            result = self.tick(stamp)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['reason'], 'ATR or spread outside allowed range')
        self.mt5.order_send.assert_not_called()

    def test_m1_switch_still_rejects_stale_ticks(self):
        self.start()
        original = pilot.state(self.db)
        self.mt5.copy_rates_from_pos.return_value = [dict(time=NOW - (250-i)*60,
            open=100, high=101, low=99, close=100) for i in range(250)]
        self.mt5.symbol_info_tick.return_value.time_msc = (NOW - 31) * 1000
        with self.assertRaisesRegex(ValueError, 'older than 30 seconds'):
            migration['review'](self.mt5, self.db, 123, NOW, self.pause, original['code'], pilot.identity())
        self.assertEqual(pilot.state(self.db), original)
        self.mt5.order_send.assert_not_called()

    def test_uncertain_submission_is_not_retried(self):
        self.start()
        self.mt5.order_send.return_value = None
        self.tick(NOW)
        result = self.tick(NOW + 900)
        self.assertEqual(result['pilot']['status'], 'needs_attention')
        self.tick(NOW + 1800)
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_owner_pause_and_daily_loss_persist(self):
        self.start()
        self.tick(NOW)
        self.pause.write_text('pause')
        result = self.tick(NOW + 900)
        self.assertEqual(result['pilot']['status'], 'paused')
        self.mt5.order_send.assert_not_called()
        self.pause.unlink()
        self.assertEqual(self.tick(NOW + 1800)['pilot']['status'], 'paused')

    def test_equity_risk_and_external_cashflow_block_entry(self):
        for field, value in [('equity', 9899), ('balance', 11000)]:
            with self.subTest(field=field):
                self.db.execute('DELETE FROM pilot')
                self.db.commit()
                self.mt5.account_info.return_value.equity = 10000
                self.mt5.account_info.return_value.balance = 10000
                self.start()
                self.tick(NOW)
                setattr(self.mt5.account_info.return_value, field, value)
                self.assertEqual(self.tick(NOW + 900)['pilot']['status'], 'paused')
                self.mt5.order_send.assert_not_called()

    def test_restart_baseline_missed_bar_and_stale_quote_do_not_enter(self):
        self.start()
        self.tick(NOW)
        self.tick(NOW + 1800)
        self.tick(NOW + 2700, bootstrap=True)
        self.mt5.order_send.assert_not_called()

    def test_pause_during_broker_check_prevents_submission(self):
        self.start()
        self.tick(NOW)
        def check(request):
            self.pause.write_text('pause')
            return Record(retcode=0)
        self.mt5.order_check.side_effect = check
        self.tick(NOW + 900)
        self.mt5.order_send.assert_not_called()

    def test_expiry_flat_and_uncertain_close(self):
        self.start(seconds=1000)
        self.fill()
        self.tick(NOW)
        self.tick(NOW + 900)
        self.mt5.order_send.side_effect = lambda request: None
        result = self.tick(NOW + 1001)
        self.assertEqual(self.mt5.order_send.call_count, 2)
        self.assertEqual(result['pilot']['status'], 'needs_attention')
        self.tick(NOW + 1100)
        self.assertEqual(self.mt5.order_send.call_count, 2)

    def test_expiry_rejected_close_keeps_exposure_visible_as_needs_attention(self):
        self.start(seconds=1000)
        self.fill()
        self.tick(NOW)
        self.tick(NOW + 900)
        self.mt5.order_check.return_value = Record(retcode=10018)
        result = self.tick(NOW + 1001)
        self.assertEqual(self.mt5.order_send.call_count, 1)
        self.assertEqual(result['pilot']['status'], 'needs_attention')
        self.assertIn('Expiry close check rejected', result['pilot']['reason'])

    def test_code_change_latches_pause(self):
        self.start()
        self.tick(NOW)
        with patch('demo_pilot.identity', return_value='changed'):
            result = self.tick(NOW + 900)
        self.assertEqual(result['pilot']['status'], 'paused')
        self.mt5.order_send.assert_not_called()

    def test_short_entry_and_filter_rejection(self):
        self.start()
        self.fill()
        self.tick(NOW)
        self.tick(NOW + 900, signal='none')
        self.tick(NOW + 1800, signal='short', allowed=False)
        self.mt5.order_send.assert_not_called()
        result = self.tick(NOW + 2700, signal='short')
        self.assertEqual(result['execution']['side'], 'sell')
        request = self.mt5.order_send.call_args.args[0]
        self.assertGreater(request['sl'], request['price'])
        self.assertLess(request['tp'], request['price'])

    def test_rejected_entry_does_not_repeat_same_bar(self):
        self.start()
        self.mt5.order_send.return_value = Record(retcode=10006, order=0, deal=0)
        self.tick(NOW)
        self.assertEqual(self.tick(NOW + 900)['execution']['status'], 'disarmed')
        self.tick(NOW + 905)
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_partial_fill_pauses_and_missing_protection_needs_attention(self):
        self.start()
        self.fill()
        self.tick(NOW)
        self.tick(NOW + 900)
        position = self.mt5.positions_get.return_value[0]
        position.volume = .005
        self.assertEqual(self.tick(NOW + 905)['pilot']['status'], 'paused')
        position.sl = 0
        self.assertEqual(self.tick(NOW + 910)['pilot']['status'], 'needs_attention')
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_final_signal_change_prevents_submission(self):
        self.start()
        self.tick(NOW)
        def check(request):
            self.clock += 900
            return Record(retcode=0)
        self.mt5.order_check.side_effect = check
        self.tick(NOW + 900)
        self.mt5.order_send.assert_not_called()

    def test_stale_quote_and_excess_minimum_lot_risk_refuse_entry(self):
        self.start()
        self.tick(NOW)
        self.mt5.order_calc_profit.return_value = -1000
        self.tick(NOW + 900)
        self.mt5.order_send.assert_not_called()
        self.clock = NOW + 1000
        result = pilot.poll_once(self.mt5, self.db, 123, self.clock, self.pause)
        self.assertEqual(result['status'], 'blocked')
        self.mt5.order_send.assert_not_called()

    def test_expiry_close_is_reconciled_to_broker_deals(self):
        self.start(seconds=1000)
        self.fill()
        self.tick(NOW)
        self.tick(NOW + 900)
        entry = self.mt5.history_deals_get.return_value[0]
        def close(request):
            self.assertEqual(request['position'], 77)
            self.mt5.positions_get.return_value = ()
            self.mt5.history_deals_get.return_value = (entry, Record(ticket=80, order=79,
                position_id=77, symbol='XAUUSD-VIP', magic=request['magic'],
                comment=request['comment'], entry=1, type=1, volume=.01,
                price=request['price'], time=self.clock, profit=-1, commission=0, swap=0, fee=0,
                reason=self.mt5.DEAL_REASON_CLIENT))
            self.mt5.account_info.return_value.balance = 9999
            return Record(retcode=10009, order=79, deal=80)
        self.mt5.order_send.side_effect = close
        result = self.tick(NOW + 1001)
        self.assertEqual(result['pilot']['status'], 'expired')
        self.assertEqual(result['pilot']['realized_net_usd'], -1)
        self.assertEqual(result['pilot']['completed_trades'], 1)

    def test_daily_reference_does_not_reset_on_restart_or_missed_midnight(self):
        self.start(seconds=7 * 86400)
        self.tick(NOW)
        p = pilot.state(self.db)
        p['day_equity'] = 12000
        pilot.save(self.db, p)
        result = self.tick(NOW + 900)
        self.assertEqual(result['pilot']['status'], 'paused')
        self.assertIn('Daily equity', result['pilot']['reason'])
        self.assertEqual(self.tick((NOW // 86400 + 1) * 86400 + 100)['pilot']['status'], 'paused')
        self.mt5.order_send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
