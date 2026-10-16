import importlib.util
import json
from pathlib import Path
import unittest
import demo_pilot as pilot
from test_recover_m5_account import RecoveryTest
from test_demo_one_shot import NOW

class ExposureRecoveryTest(unittest.TestCase):
    def setUp(self):
        RecoveryTest.setUp(self)
        spec = importlib.util.spec_from_file_location('recover_exposure', Path(__file__).with_name('recover-m5-exposure-pause.py'))
        self.recovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.recovery)
        for db, strategy in ((self.gold,pilot.M5_JEV_STRATEGY),(self.btc,pilot.BTC_M5_JEV_STRATEGY)):
            p=pilot.state(db)
            p.update(code=self.recovery.PREVIOUS, strategy=strategy, jev_mode='veto',
                     pause=self.recovery.PAUSE, reporting_start=1792048262.9843044, reporting_end=1792221062.9843044)
            pilot.save(db,p)
        risk=json.loads(self.gold.execute('select data from account_limits').fetchone()[0])
        risk.update(code=self.recovery.PREVIOUS,pause=self.recovery.PAUSE)
        self.gold.execute('update account_limits set data=?',(json.dumps(risk),));self.gold.commit()
        self.original=risk

    def test_recovery_preserves_every_unrelated_field_and_history(self):
        old=[pilot.state(d) for d in (self.gold,self.btc)]
        self.recovery.recover(self.mt5,self.gold,self.btc,123,NOW,self.home,pilot.identity(),self.home/'backup')
        risk=json.loads(self.gold.execute('select data from account_limits').fetchone()[0])
        for k,v in self.original.items():
            if k not in ('code','pause','last_poll'):self.assertEqual(risk[k],v,k)
        for before,db in zip(old,(self.gold,self.btc)):
            after=pilot.state(db)
            self.assertIsNone(after['pause'])
            for k,v in before.items():
                if k not in ('code','pause','last_bar','last_poll','reason'):self.assertEqual(after[k],v,k)
        self.mt5.order_send.assert_not_called()

    def test_owner_pause_or_changed_window_refuses(self):
        for key,value in (('pause','Paused by owner'),('reporting_end',1792221063)):
            p=pilot.state(self.btc);previous=p[key];p[key]=value;pilot.save(self.btc,p)
            with self.assertRaises(ValueError):self.recovery.review(self.mt5,self.gold,self.btc,123,NOW,self.home,pilot.identity())
            p[key]=previous;pilot.save(self.btc,p)
        (self.home/'btc-pilot.pause').touch()
        with self.assertRaises(ValueError):self.recovery.review(self.mt5,self.gold,self.btc,123,NOW,self.home,pilot.identity())
