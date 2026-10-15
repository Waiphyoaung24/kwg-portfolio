import json
import unittest
from unittest.mock import patch

import demo_pilot as pilot
import jev_m5
from instruments import BTC, GOLD, validate_market
from test_jev_m5 import bars, receipt
import test_jev_m5_pilot as harness


class DualReceiptTest(unittest.TestCase):
    def test_btc_state_and_receipts_cannot_cross_symbols(self):
        market = bars()
        indicators = dict(ema20=102.4, ema50=102.2, atr14=.05)
        gold = jev_m5.state(market, 102.48, 102.49, indicators, captured_at=75302)
        btc = jev_m5.state(market, 102.48, 102.49, indicators, captured_at=75302, symbol=BTC)
        self.assertEqual(btc['symbol'], BTC)
        self.assertNotEqual(jev_m5.input_sha256(gold), jev_m5.input_sha256(btc))
        value = receipt(symbol=BTC, question_sha256=jev_m5.BTC_QUESTION_SHA256)
        self.assertEqual(jev_m5.validate_receipt(value, symbol=BTC), value)
        with self.assertRaises(ValueError):
            jev_m5.validate_receipt(value)
        with self.assertRaises(ValueError):
            jev_m5.validate_receipt(receipt(), symbol=BTC)
        self.assertTrue(jev_m5.allows(value, side='long', bar_time=600, input_sha256='a'*64, now=930, symbol=BTC)[0])
        self.assertFalse(jev_m5.allows(value, side='long', bar_time=600, input_sha256='a'*64, now=930)[0])

    def test_btc_m5_is_reviewed_and_uses_same_cooldown(self):
        validate_market(BTC, 300, True)
        p = {'strategy': pilot.BTC_M5_JEV_STRATEGY}
        self.assertEqual(pilot.candle_seconds(p), 300)
        self.assertTrue(pilot.trending(p))
        with patch('demo_pilot.evaluate', return_value={'signal':'none', 'ema20':2, 'ema50':1}) as evaluate:
            self.assertEqual(pilot.assess([], type('Tick', (), {'bid':1, 'ask':2})(), 1000, p)['signal'], 'long')
            self.assertEqual(evaluate.call_args.kwargs['symbol'], BTC)


class ReportingTest(unittest.TestCase):
    setUp = harness.JevM5PilotTest.setUp
    start = harness.JevM5PilotTest.start

    def test_window_filters_history_without_resetting_risk_or_floating(self):
        self.start()
        p = pilot.state(self.db)
        start = p['start'] + 100
        p.update(reporting_start=start, reporting_end=start+172800)
        pilot.save(self.db, p)
        for opened, net in ((start-1, -20), (start, 3), (start+172800, 9)):
            pilot.execution.arm_once(self.db, 'buy', int(opened))
            pilot.execution._update(self.db, state='closed', opened_at=opened, closed_at=opened+10, realized_net_usd=net)
        before = pilot.state(self.db)
        report = pilot.snapshot(self.mt5, self.db, p, {'status':'closed'}, start+172900, 123)
        self.assertEqual((report['completed_trades'], report['realized_net_usd']), (1, 3))
        self.assertEqual(len(report['recent_trades']), 1)
        self.assertEqual(report['floating_usd'], 0)
        self.assertEqual(report['reporting_start'], start)
        self.assertEqual(pilot.state(self.db), before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 3)


class BtcVetoTest(unittest.TestCase):
    start = harness.JevM5PilotTest.start
    tick = harness.JevM5PilotTest.tick
    rows = harness.JevM5PilotTest.rows
    provenance = harness.JevM5PilotTest.provenance

    def setUp(self):
        harness.JevM5PilotTest.setUp(self)
        self.start()
        self.db.execute("UPDATE metadata SET symbol=?", (BTC,))
        self.db.commit()
        info = self.mt5.symbol_info.return_value
        info.name, info.currency_profit, info.trade_contract_size = BTC, 'USD', 1
        p = pilot.state(self.db)
        p.update(strategy=pilot.BTC_M5_JEV_STRATEGY, jev_mode='veto', code=pilot.identity())
        pilot.save(self.db, p)

    def test_btc_waits_for_own_receipt_and_uses_protected_exit(self):
        from types import SimpleNamespace as Record
        from test_demo_one_shot import NOW
        def send(request):
            self.mt5.positions_get.return_value = (Record(ticket=77, symbol=BTC,
                magic=request['magic'], comment=request['comment'], type=request['type'],
                volume=request['volume'], price_open=request['price'], sl=request['sl'],
                tp=request['tp'], profit=0),)
            self.mt5.history_deals_get.return_value = (Record(ticket=78, order=77,
                position_id=77, symbol=BTC, magic=request['magic'], comment=request['comment'],
                entry=0, type=request['type'], volume=request['volume'], price=request['price'],
                time=self.clock, profit=0, commission=0, swap=0, fee=0),)
            return Record(retcode=10009, order=77, deal=78)
        self.mt5.order_send.side_effect = send
        self.tick(NOW + 300, bootstrap=True)
        self.assertEqual(self.tick(NOW + 600)['reason'], 'Waiting for Jev')
        feed = json.loads(pilot.feed_path(BTC).read_text())
        self.assertEqual(json.loads(feed['state_json'])['symbol'], BTC)
        self.assertFalse(self.feed.exists())
        digest = pilot.state(self.db)['pending_entry']['input_sha256']
        value = receipt(bar_time=NOW+300, completed=NOW+620, input_sha256=digest)
        jev_m5.store_receipt(self.receipts, value, received=NOW+620)
        self.assertEqual(self.tick(NOW+625)['reason'], 'Waiting for Jev')
        self.mt5.order_send.assert_not_called()
        value.update(symbol=BTC, question_sha256=jev_m5.BTC_QUESTION_SHA256)
        jev_m5.store_receipt(self.receipts.with_name('btc-jev-m5-receipts.sqlite3'), value, received=NOW+620, symbol=BTC)
        self.assertEqual(self.tick(NOW+630)['execution']['status'], 'open')
        self.assertEqual(self.mt5.order_send.call_count, 1)
        request = self.mt5.order_send.call_args.args[0]
        self.assertEqual((request['symbol'], request['volume']), (BTC, .01))
        self.assertLess(request['sl'], request['price'])
        self.assertGreater(request['tp'], request['price'])
        self.assertEqual(self.tick(NOW+700)['execution']['status'], 'open')
        self.assertEqual(self.mt5.order_send.call_count, 1)  # No 60-second timed liquidation.


class EntryClockTest(unittest.TestCase):
    def test_live_request_samples_after_quote_read(self):
        from test_demo_one_shot import NOW, fake_mt5
        mt5 = fake_mt5(enabled=True)
        mt5.symbol_info_tick.return_value.time_msc = (NOW + .2) * 1000
        with patch('time.time', return_value=NOW + .3):
            request = pilot.execution.build_entry_request(mt5, 123, 'buy', None, 0, execution=True)
        self.assertEqual(request['volume'], .01)
        self.assertEqual(request['symbol'], GOLD)
        with patch('time.time', return_value=NOW + .1), self.assertRaisesRegex(ValueError, 'ahead'):
            pilot.execution.build_entry_request(mt5, 123, 'buy', None, 0, execution=True)
        mt5.order_send.assert_not_called()
