import json
import os
from pathlib import Path
import runpy
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace as Record
from unittest.mock import patch

import demo_pilot as pilot
import demo_one_shot as execution
from instruments import GOLD, BTC, BTC_STRATEGY
from test_demo_one_shot import fake_mt5, NOW

migration = runpy.run_path(str(Path(__file__).with_name('migrate-two-symbol-pilot.py')))


class TwoSymbolTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.gold = pilot.open_state(self.home / 'gold.sqlite3', 123)
        self.btc = pilot.open_state(self.home / 'btc.sqlite3', 123, BTC)
        self.addCleanup(self.gold.close)
        self.addCleanup(self.btc.close)
        self.mt5 = fake_mt5(enabled=True)
        self.mt5.account_info.return_value.balance = 10000
        self.positions = []
        self.deals = []
        self.mt5.positions_get.side_effect = lambda **kw: tuple(p for p in self.positions if not kw or p.symbol == kw['symbol'])
        self.mt5.history_deals_get.side_effect = lambda *args: tuple(self.deals)
        self.mt5.order_check.return_value = Record(retcode=0)
        original = self.mt5.symbol_info.return_value
        self.mt5.symbol_info.side_effect = lambda symbol: Record(**{**vars(original), 'name': symbol,
            'currency_profit': 'USD', 'trade_contract_size': 1 if symbol == BTC else 100})
        self.clock = NOW
        for p in (patch.dict(os.environ, {'MT5_SERVER_OFFSET_SECONDS': '0'}),
                  patch('time.time', side_effect=lambda: self.clock)):
            p.start()
            self.addCleanup(p.stop)
        pilot.activate(self.mt5, self.gold, 123, NOW, NOW + 3600, self.home / 'gold.pause')
        p = pilot.state(self.gold)
        p.update(strategy=pilot.TREND_STRATEGY, code='previous', pause='Pinned USD demo account unavailable')
        pilot.save(self.gold, p)

    def migrate(self):
        return migration['migrate'](self.mt5, self.gold, 123, self.clock, pilot.identity(), 'previous', self.home / 'backup.sqlite3')

    def position(self, db, symbol, ticket=77):
        execution.arm_once(db, 'buy', NOW)
        request = dict(symbol=symbol, type=0, volume=.01, price=100.1, sl=96, tp=106,
                       comment=f'kwg-pilot-{ticket}', magic=execution.MAGIC, type_filling=0)
        execution._update(db, state='open', request_json=json.dumps(request), order_id=ticket,
            position_ticket=ticket, volume=.01, opened_at=NOW, entry_equity=10000)
        self.positions.append(Record(ticket=ticket, symbol=symbol, type=0, volume=.01, price_open=100.1,
            sl=96, tp=106, magic=execution.MAGIC, comment=request['comment'], profit=0))
        self.deals.append(Record(ticket=ticket+100, order=ticket, position_id=ticket, symbol=symbol,
            entry=0, type=0, volume=.01, price=100.1, magic=execution.MAGIC,
            comment=request['comment'], profit=0, commission=0, swap=0, fee=0, time=NOW))

    def test_migration_preserves_open_gold_pause_history_and_risk(self):
        self.position(self.gold, GOLD)
        old = pilot.state(self.gold)
        attempt = dict(execution._attempt(self.gold))
        result = self.migrate()
        self.assertEqual(dict(execution._attempt(self.gold)), attempt)
        for key in ('start', 'end', 'initial_balance', 'initial_equity', 'peak', 'day_equity', 'pause'):
            self.assertEqual(pilot.state(self.gold)[key], old[key])
        backup = sqlite3.connect(result['backup'])
        self.addCleanup(backup.close)
        self.assertEqual(pilot.state(backup), old)
        self.assertIsNone(pilot.state(self.btc))
        self.mt5.order_send.assert_not_called()
        with self.assertRaises(ValueError):
            self.migrate()

    def test_btc_activation_preserves_expiry_and_allows_owned_gold_position(self):
        self.position(self.gold, GOLD)
        self.migrate()
        shared = pilot.SharedAccount(self.gold, self.btc)
        pilot.activate_btc(self.mt5, self.gold, self.btc, 123, NOW, self.home, shared)
        btc = pilot.state(self.btc)
        self.assertEqual((btc['strategy'], btc['start'], btc['end']), (BTC_STRATEGY, NOW, NOW+3600))
        self.assertIsNone(btc['pause'])
        self.assertEqual(pilot.state(self.gold)['pause'], 'Pinned USD demo account unavailable')
        self.mt5.copy_rates_from_pos.assert_called_with(BTC, self.mt5.TIMEFRAME_M15, 1, 250)
        self.mt5.order_send.assert_not_called()
        with self.assertRaises(ValueError):
            pilot.activate_btc(self.mt5, self.gold, self.btc, 123, NOW, self.home, shared)

    def test_shared_loss_limit_latches_across_restart_and_symbols(self):
        self.migrate()
        self.mt5.account_info.return_value.equity = 9899
        shared = pilot.SharedAccount(self.gold, self.btc)
        with self.assertRaisesRegex(ValueError, 'Daily equity loss'):
            shared.check(self.mt5, 123, NOW)
        self.mt5.account_info.return_value.equity = 10000
        with self.assertRaisesRegex(ValueError, 'Daily equity loss'):
            pilot.SharedAccount(self.gold, self.btc).check(self.mt5, 123, NOW+1)
        self.mt5.order_send.assert_not_called()

    def test_shared_history_accepts_both_owned_symbols_rejects_unrelated_activity(self):
        self.position(self.gold, GOLD)
        self.migrate()
        self.position(self.btc, BTC, 88)
        shared = pilot.SharedAccount(self.gold, self.btc)
        shared.check(self.mt5, 123, NOW)
        self.deals.append(Record(type=0, symbol=BTC, comment='manual', position_id=999, magic=0))
        with self.assertRaisesRegex(ValueError, 'Unrelated account activity'):
            shared.check(self.mt5, 123, NOW)

    def test_unowned_or_unprotected_position_blocks_migration(self):
        self.position(self.gold, GOLD)
        self.positions[0].sl = 0
        with self.assertRaises(ValueError):
            self.migrate()
        self.assertFalse((self.home/'backup.sqlite3').exists())
        self.mt5.order_send.assert_not_called()

    def test_btc_entry_uses_btc_contract_and_never_gold_journal(self):
        self.position(self.gold, GOLD)
        self.migrate()
        shared = pilot.SharedAccount(self.gold, self.btc)
        pilot.activate_btc(self.mt5, self.gold, self.btc, 123, NOW, self.home, shared)
        p = pilot.state(self.btc)
        p['last_bar'] = NOW - 1800
        pilot.save(self.btc, p)
        def send(request):
            self.assertEqual(request['symbol'], BTC)
            ticket = 88
            self.positions.append(Record(ticket=ticket, symbol=BTC, type=request['type'], volume=.01,
                price_open=request['price'], sl=request['sl'], tp=request['tp'], magic=execution.MAGIC,
                comment=request['comment'], profit=0))
            self.deals.append(Record(ticket=188, order=ticket, position_id=ticket, symbol=BTC,
                entry=0, type=request['type'], volume=.01, price=request['price'], magic=execution.MAGIC,
                comment=request['comment'], profit=0, commission=0, swap=0, fee=0, time=NOW))
            return Record(retcode=10009, order=ticket, deal=188)
        self.mt5.order_send.side_effect = send
        with patch('demo_pilot.assess', return_value={'bar_time': NOW-900, 'signal': 'long', 'reason': 'evaluated'}), \
                patch('demo_pilot.entry_allowed', return_value=True):
            first = pilot.poll_once(self.mt5, self.btc, 123, NOW, self.home/'btc.pause', shared=shared)
            self.assertEqual(first['execution']['status'], 'open', first)
            pilot.poll_once(self.mt5, self.btc, 123, NOW, self.home/'btc.pause', shared=shared)
            pilot.poll_once(self.mt5, self.btc, 123, NOW, self.home/'btc.pause', shared=shared, bootstrap=True)
        self.assertEqual(self.mt5.order_send.call_count, 1)
        self.assertEqual(execution._attempt(self.gold)['position_ticket'], 77)
        self.assertEqual(execution._attempt(self.btc)['position_ticket'], 88)
        self.assertEqual(len(self.positions), 2)

    def test_wrong_symbol_request_and_journal_are_rejected(self):
        self.position(self.btc, GOLD)
        report = execution.process_once(self.mt5, self.btc, NOW, allow_entry=False)
        self.assertEqual(report['status'], 'needs_attention')
        with self.assertRaises(ValueError):
            execution.open_journal(self.home/'gold.sqlite3', 123, BTC)
        with self.assertRaises(ValueError):
            execution.build_entry_request(self.mt5, 123, 'buy', NOW, 0, execution=True, symbol=BTC)
        self.mt5.order_send.assert_not_called()

    def test_btc_standby_reports_without_gold_quotes_or_order(self):
        self.migrate()
        shared = pilot.SharedAccount(self.gold, self.btc)
        report = pilot.poll_once(self.mt5, self.btc, 123, NOW, self.home/'btc.pause', shared=shared)
        self.assertEqual(report['symbol'], BTC)
        self.assertEqual(report['health']['quote'], 'fresh')
        self.assertEqual(report['pilot']['status'], 'standby')
        self.assertEqual(report['pilot']['strategy'], BTC_STRATEGY)
        self.mt5.order_send.assert_not_called()

    def test_btc_expiry_closes_only_its_owned_position(self):
        self.position(self.gold, GOLD)
        self.migrate()
        shared = pilot.SharedAccount(self.gold, self.btc)
        pilot.activate_btc(self.mt5, self.gold, self.btc, 123, NOW, self.home, shared)
        self.position(self.btc, BTC, 88)
        self.clock = NOW + 3601
        self.mt5.symbol_info_tick.return_value.time = self.clock
        self.mt5.symbol_info_tick.return_value.time_msc = self.clock * 1000
        def close(request):
            self.assertEqual((request['symbol'], request['position'], request['type']), (BTC, 88, 1))
            self.positions[:] = [p for p in self.positions if p.symbol != BTC]
            self.deals.append(Record(ticket=999, order=998, position_id=88, symbol=BTC,
                entry=1, type=1, volume=.01, price=100, magic=execution.MAGIC,
                comment=request['comment'], profit=0, commission=0, swap=0, fee=0, time=self.clock, reason=0))
            return Record(retcode=10009, order=998, deal=999)
        self.mt5.order_send.side_effect = close
        report = pilot.poll_once(self.mt5, self.btc, 123, self.clock, self.home/'btc.pause', shared=shared)
        self.assertEqual(report['execution']['status'], 'closed')
        self.assertEqual(report['pilot']['status'], 'expired')
        self.assertEqual([p.symbol for p in self.positions], [GOLD])
        self.assertEqual(self.mt5.order_send.call_count, 1)


if __name__ == '__main__':
    unittest.main()
