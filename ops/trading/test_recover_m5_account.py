import importlib.util
import json
from pathlib import Path
import unittest

import demo_pilot as pilot
import test_acknowledged_deals as acknowledged
from test_demo_one_shot import NOW


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        acknowledged.AcknowledgedDealsTest.setUp(self)
        spec = importlib.util.spec_from_file_location('recover_m5', Path(__file__).with_name('recover-m5-account-pause.py'))
        self.recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.recovery)
        for db, strategy, pause in ((self.gold, pilot.M5_JEV_STRATEGY, self.recovery.PAUSE),
                                   (self.btc, pilot.BTC_SCALP_STRATEGY, 'Paused by owner')):
            p = pilot.state(self.gold).copy()
            p.update(code=self.recovery.PREVIOUS, strategy=strategy, pause=pause,
                     end=None, run_policy='continuous', jev_mode='shadow')
            with db:
                db.execute('INSERT OR REPLACE INTO pilot VALUES (1,?)', (json.dumps(p),))
        r = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        r.update(code=self.recovery.PREVIOUS, pause=self.recovery.PAUSE, end=None, run_policy='continuous')
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(r),))
        self.original = r

    def review(self):
        return self.recovery.review(self.mt5, self.gold, self.btc, 123, NOW, self.home, pilot.identity())

    def test_recovery_preserves_owner_pause_receipts_and_risk(self):
        risk, records = self.review()
        self.assertIsNone(risk['pause'])
        self.assertIsNone(records[0]['pause'])
        self.assertEqual(records[1]['pause'], 'Paused by owner')
        self.assertEqual(records[0]['strategy'], pilot.M5_JEV_STRATEGY)
        for key in ('start', 'initial_balance', 'initial_equity', 'day_equity', 'acknowledged_manual_deals'):
            self.assertEqual(risk[key], self.original[key])
        self.assertEqual(pilot.state(self.gold)['pause'], self.recovery.PAUSE)
        self.mt5.order_send.assert_not_called()

    def test_other_pause_refuses(self):
        p = pilot.state(self.gold);p['pause'] = 'Daily equity loss limit reached';pilot.save(self.gold,p)
        with self.assertRaises(ValueError): self.review()

    def test_owner_gold_pause_refuses(self):
        (self.home/'gold-pilot.pause').touch()
        with self.assertRaises(ValueError): self.review()

    def test_changed_manual_history_refuses(self):
        self.deals[0].profit = -1
        with self.assertRaises(ValueError): self.review()

    def test_apply_backs_up_and_preserves_btc_owner_pause(self):
        backup = self.home/'recovery-backup'
        self.recovery.recover(self.mt5,self.gold,self.btc,123,NOW,self.home,pilot.identity(),backup)
        self.assertTrue((backup/'gold.sqlite3').exists())
        self.assertTrue((backup/'btc.sqlite3').exists())
        self.assertIsNone(pilot.state(self.gold)['pause'])
        self.assertEqual(pilot.state(self.btc)['pause'],'Paused by owner')
        self.mt5.order_send.assert_not_called()
