from contextlib import closing
import json
from pathlib import Path
import runpy
import sqlite3
import unittest
from unittest.mock import patch

import demo_pilot as pilot
import demo_one_shot as execution
from instruments import BTC, GOLD
from test_demo_one_shot import NOW
import test_two_symbol_pilot as two

migration = runpy.run_path(str(Path(__file__).with_name('migrate-continuous-pilot.py')))


class ContinuousTest(unittest.TestCase):
    setUp = two.TwoSymbolTest.setUp
    migrate = two.TwoSymbolTest.migrate
    position = two.TwoSymbolTest.position

    def prepare(self):
        self.migrate()
        pilot.activate_btc(self.mt5, self.gold, self.btc, 123, NOW, self.home, pilot.SharedAccount(self.gold, self.btc))

    def upgrade(self):
        return migration['migrate'](self.mt5, self.gold, self.btc, 123, NOW,
            pilot.identity(), pilot.identity(), self.home / 'continuous-backup')

    def poll(self, stamp=NOW):
        self.clock = stamp
        return pilot.poll_once(self.mt5, self.btc, 123, stamp, self.home / 'btc.pause',
                               shared=pilot.SharedAccount(self.gold, self.btc))

    def test_migration_preserves_trades_limits_and_owner_pause(self):
        self.position(self.gold, GOLD)
        self.prepare()
        old_risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        old_trade = dict(execution._attempt(self.gold))
        p = pilot.state(self.btc)
        p['pause'] = 'Paused by owner'
        pilot.save(self.btc, p)
        receipt = self.upgrade()
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        for key in ('start', 'initial_balance', 'initial_equity', 'peak', 'day_equity', 'day'):
            self.assertEqual(risk[key], old_risk[key])
        self.assertEqual(dict(execution._attempt(self.gold)), old_trade)
        self.assertEqual(pilot.state(self.btc)['pause'], 'Paused by owner')
        self.assertIsNone(pilot.state(self.gold)['pause'])
        for db in (self.gold, self.btc):
            self.assertTrue(pilot.continuous(pilot.state(db)))
            self.assertFalse(pilot.expired(pilot.state(db), NOW + 90*86400))
        with closing(sqlite3.connect(Path(receipt['backup']) / 'btc.sqlite3')) as saved:
            self.assertEqual(pilot.state(saved), p)
        self.mt5.order_send.assert_not_called()

    def test_disconnect_retries_then_reconciles_open_trade_without_duplicate(self):
        self.prepare()
        self.position(self.btc, BTC, 88)
        self.upgrade()
        self.mt5.terminal_info.return_value.connected = False
        report = self.poll()
        self.assertEqual(report['pilot']['status'], 'active')
        self.assertIsNone(report['health'])
        self.assertEqual(execution._attempt(self.btc)['state'], 'open')
        self.assertTrue(pilot.state(self.btc)['recovering'])
        self.mt5.terminal_info.return_value.connected = True
        recovered = self.poll()
        self.assertFalse(pilot.state(self.btc).get('recovering', False))
        self.assertEqual(recovered['status'], 'baseline')
        self.assertIsNone(pilot.state(self.btc)['pause'])
        self.assertEqual(execution._attempt(self.btc)['state'], 'open')
        self.mt5.order_send.assert_not_called()

    def test_history_outage_recovers_but_balance_mismatch_latches(self):
        self.prepare()
        self.upgrade()
        self.mt5.history_deals_get.side_effect = lambda *args: None
        self.poll()
        self.assertIsNone(pilot.state(self.btc)['pause'])
        self.mt5.history_deals_get.side_effect = lambda *args: ()
        self.poll()
        self.assertFalse(pilot.state(self.btc).get('recovering', False))
        self.mt5.account_info.return_value.balance -= 1
        self.poll()
        self.assertIsNone(pilot.state(self.btc)['pause'])
        self.assertTrue(pilot.state(self.btc)['recovering'])
        self.poll(NOW + 30)
        self.assertEqual(pilot.state(self.btc)['pause'], 'Account balance and deal history disagree')
        self.mt5.account_info.return_value.balance += 1
        self.poll(NOW + 35)
        self.assertIsNotNone(pilot.state(self.btc)['pause'])
        self.mt5.order_send.assert_not_called()

    def test_paused_open_position_is_still_reconciled(self):
        self.prepare()
        self.position(self.btc, BTC, 88)
        self.upgrade()
        (self.home / 'btc.pause').write_text('owner pause')
        with patch.object(execution, '_reconcile', wraps=execution._reconcile) as reconcile:
            report = self.poll()
        reconcile.assert_called()
        self.assertEqual(report['pilot']['status'], 'paused')
        self.assertEqual(report['execution']['status'], 'open')
        self.mt5.order_send.assert_not_called()

    def test_wrong_account_and_loss_limits_never_auto_resume(self):
        self.prepare()
        self.upgrade()
        self.mt5.account_info.return_value.login = 456
        self.poll()
        self.mt5.account_info.return_value.login = 123
        self.poll()
        self.assertEqual(pilot.state(self.btc)['pause'], 'Pinned USD demo account identity changed')
        self.mt5.order_send.assert_not_called()

    def test_missing_midnight_keeps_existing_loss_threshold(self):
        self.prepare()
        self.upgrade()
        shared = pilot.SharedAccount(self.gold, self.btc)
        self.clock = (NOW // 86400 + 1) * 86400 + 120
        shared.check(self.mt5, 123, self.clock)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertEqual(risk['day_equity'], 10000)
        self.mt5.account_info.return_value.equity = 9899
        with self.assertRaisesRegex(ValueError, 'Daily equity loss'):
            shared.check(self.mt5, 123, self.clock + 1)
        self.mt5.account_info.return_value.equity = 10000
        with self.assertRaisesRegex(ValueError, 'Daily equity loss'):
            shared.check(self.mt5, 123, self.clock + 2)

    def test_migration_refuses_identity_and_unprotected_exposure(self):
        self.prepare()
        self.position(self.btc, BTC, 88)
        self.positions[0].sl = 0
        with self.assertRaises(ValueError):
            self.upgrade()
        self.assertFalse((self.home / 'continuous-backup').exists())
        self.assertIsNotNone(pilot.state(self.btc)['end'])
        self.mt5.order_send.assert_not_called()

    def test_migration_rolls_back_both_journals_if_second_update_fails(self):
        self.prepare()
        before = [pilot.state(db) for db in (self.gold, self.btc)]
        risk = self.gold.execute('SELECT data FROM account_limits').fetchone()[0]
        self.btc.execute("CREATE TRIGGER reject_migration BEFORE UPDATE ON pilot BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        self.btc.commit()
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'test failure'):
            self.upgrade()
        self.assertEqual([pilot.state(db) for db in (self.gold, self.btc)], before)
        self.assertEqual(self.gold.execute('SELECT data FROM account_limits').fetchone()[0], risk)
        self.mt5.order_send.assert_not_called()

    def test_legacy_exposure_pause_clears_only_after_verified_reconciliation(self):
        self.prepare()
        reason = 'Account exposure unavailable or pending orders require review'
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        risk['pause'] = reason
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(risk),))
        p = pilot.state(self.btc)
        p['pause'] = reason
        pilot.save(self.btc, p)
        original_orders = self.mt5.orders_get.side_effect
        for orders in (None, (object(),)):
            self.mt5.orders_get.side_effect = lambda *args, **kwargs: orders
            with self.assertRaises(ValueError):
                self.upgrade()
            self.assertEqual(pilot.state(self.btc)['pause'], reason)
            self.assertFalse((self.home / 'continuous-backup').exists())
        self.mt5.orders_get.side_effect = original_orders
        self.upgrade()
        self.assertIsNone(pilot.state(self.btc)['pause'])
        self.assertIsNone(json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])['pause'])
        self.mt5.order_send.assert_not_called()

    def test_migration_preserves_latched_account_loss_pause(self):
        self.prepare()
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        risk['pause'] = 'Daily equity loss limit reached'
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(risk),))
        self.upgrade()
        self.assertEqual(json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])['pause'], risk['pause'])
        with self.assertRaisesRegex(ValueError, 'Daily equity loss'):
            pilot.SharedAccount(self.gold, self.btc).check(self.mt5, 123, NOW)
        self.mt5.order_send.assert_not_called()


class DeployedIdentityTest(unittest.TestCase):
    def test_deployed_identity_predates_jev_m5(self):
        # The reviewed deployed version has no jev_m5.py; hashing it would refuse every migration.
        hashed = []
        def capture(files):
            hashed.extend(files)
            raise LookupError('stop before MT5')
        with patch('sys.argv', ['migrate', '--reviewed-code-sha256', 'x']), \
                patch.object(Path, 'read_bytes', lambda path: path.name.encode()), \
                patch.object(pilot, 'digest', capture), self.assertRaises(LookupError):
            migration['main']()
        self.assertEqual(set(hashed), set(pilot.SOURCES) - {'jev_m5.py'})


if __name__ == '__main__':
    unittest.main()
