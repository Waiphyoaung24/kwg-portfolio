"""Account/history reads must describe the same settlement snapshot."""
import json
from itertools import chain, repeat
from pathlib import Path
import runpy
import unittest
from types import SimpleNamespace as Record

import demo_pilot as pilot
from instruments import GOLD
from test_demo_one_shot import NOW
import test_continuous_pilot as continuous


class BalanceSnapshotTest(unittest.TestCase):
    setUp = continuous.ContinuousTest.setUp
    migrate = continuous.ContinuousTest.migrate
    prepare = continuous.ContinuousTest.prepare
    upgrade = continuous.ContinuousTest.upgrade
    position = continuous.ContinuousTest.position

    def prepare_settlement(self):
        self.prepare()
        self.position(self.gold, GOLD)
        self.upgrade()
        return pilot.SharedAccount(self.gold, self.btc)

    def test_settlement_between_account_and_history_does_not_latch(self):
        shared = self.prepare_settlement()
        old = Record(**vars(self.mt5.account_info.return_value))
        new = Record(**{**vars(old), 'balance': old.balance - 3.45})
        self.deals[0].profit = -3.45
        self.mt5.account_info.side_effect = chain([old], repeat(new))
        with self.assertRaises(pilot.BrokerUnavailable):
            shared.check(self.mt5, 123, NOW)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertIsNone(risk['pause'])
        self.assertTrue(risk['balance_check']['balance_changed'])
        self.mt5.account_info.side_effect = None
        self.mt5.account_info.return_value = new
        shared.check(self.mt5, 123, NOW)
        self.mt5.order_send.assert_not_called()

    def test_balance_changes_after_history_even_when_old_pair_matches(self):
        shared = self.prepare_settlement()
        old = Record(**vars(self.mt5.account_info.return_value))
        new = Record(**{**vars(old), 'balance': old.balance - 3.45})
        self.mt5.account_info.side_effect = chain([old], repeat(new))
        with self.assertRaises(pilot.BrokerUnavailable):
            shared.check(self.mt5, 123, NOW)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertIsNone(risk['pause'])
        self.mt5.order_send.assert_not_called()

    def test_stable_unexplained_difference_still_latches(self):
        shared = self.prepare_settlement()
        self.mt5.account_info.return_value.balance -= 3.45
        with self.assertRaises(pilot.BrokerUnavailable):
            shared.check(self.mt5, 123, NOW)
        # A new process must not reset the finite synchronization deadline.
        shared = pilot.SharedAccount(self.gold, self.btc)
        with self.assertRaisesRegex(ValueError, 'balance and deal history disagree'):
            shared.check(self.mt5, 123, NOW + 30)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertEqual(risk['pause'], 'Account balance and deal history disagree')
        self.assertAlmostEqual(risk['balance_check']['difference'], -3.45)
        self.assertFalse(risk['balance_check']['balance_changed'])
        self.mt5.order_send.assert_not_called()

    def test_incomplete_successful_history_blocks_then_recovers(self):
        shared = self.prepare_settlement()
        self.mt5.account_info.return_value.balance -= 3.45
        with self.assertRaises(pilot.BrokerUnavailable):
            shared.check(self.mt5, 123, NOW)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertIsNone(risk['pause'])
        # Simulate the terminal completing its history synchronization.
        self.deals[0].profit = -3.45
        shared.check(self.mt5, 123, NOW + 5)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertIsNone(risk['pause'])
        self.assertNotIn('balance_pending_since', risk)
        self.mt5.order_send.assert_not_called()

    def test_second_account_read_enforces_loss_guard(self):
        shared = self.prepare_settlement()
        old = Record(**vars(self.mt5.account_info.return_value))
        new = Record(**{**vars(old), 'balance': old.balance - 101, 'equity': 9899})
        self.mt5.account_info.side_effect = chain([old], repeat(new))
        with self.assertRaisesRegex(ValueError, 'Daily equity loss limit reached'):
            shared.check(self.mt5, 123, NOW)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertEqual(risk['pause'], 'Daily equity loss limit reached')
        self.mt5.order_send.assert_not_called()

    def test_poll_blocks_orders_and_recovers_both_symbols(self):
        self.prepare_settlement()
        self.mt5.account_info.return_value.balance -= 3.45
        for db, symbol in ((self.gold, 'gold'), (self.btc, 'btc')):
            report = pilot.poll_once(self.mt5, db, 123, NOW, self.home / (symbol + '.pause'),
                                     shared=pilot.SharedAccount(self.gold, self.btc))
            self.assertIsNone(report['health'])
            self.assertTrue(pilot.state(db)['recovering'])
            self.assertIsNone(pilot.state(db)['pause'])
        self.mt5.order_send.assert_not_called()
        self.deals[0].profit = -3.45
        for db, symbol in ((self.gold, 'gold'), (self.btc, 'btc')):
            pilot.poll_once(self.mt5, db, 123, NOW + 5, self.home / (symbol + '.pause'),
                            shared=pilot.SharedAccount(self.gold, self.btc))
            self.assertFalse(pilot.state(db).get('recovering', False))
            self.assertIsNone(pilot.state(db)['pause'])
        self.mt5.order_send.assert_not_called()

    def test_upgrade_preserves_limits_strategy_and_positions(self):
        self.prepare_settlement()
        migration = runpy.run_path(str(Path(__file__).with_name('migrate-btc-scalp.py')))
        previous = migration['BALANCE_PREVIOUS_CODE']
        for db in (self.gold, self.btc):
            p = pilot.state(db)
            p['code'] = previous
            if db is self.btc:
                p['strategy'] = 'btc-ema-v1-m1-scalp-60'
            pilot.save(db, p)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        risk['code'] = previous
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(risk),))
        trade = dict(pilot.execution._attempt(self.gold))
        migration['migrate'](self.mt5, self.gold, self.btc, 123, NOW, pilot.identity(), previous,
                             self.home / 'balance-snapshot-backup')
        updated = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        self.assertEqual({**updated, 'code': previous}, risk)
        self.assertEqual(dict(pilot.execution._attempt(self.gold)), trade)
        self.assertEqual(pilot.state(self.btc)['strategy'], 'btc-ema-v1-m1-scalp-60')
        self.mt5.order_send.assert_not_called()
