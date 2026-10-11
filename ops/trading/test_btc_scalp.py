"""Timed BTC demo exits, isolation and migration regression checks."""
import json
from pathlib import Path
import runpy
from types import SimpleNamespace as Record
from unittest.mock import patch

import demo_pilot as pilot
import demo_one_shot as execution
from instruments import BTC, GOLD, BTC_SCALP_STRATEGY
from test_two_symbol_pilot import TwoSymbolTest
from test_demo_one_shot import NOW

migration = runpy.run_path(str(Path(__file__).with_name('migrate-btc-scalp.py')))


class BtcScalpTest(TwoSymbolTest):
    def start_scalp(self):
        self.position(self.gold, GOLD)
        self.migrate()
        self.shared = pilot.SharedAccount(self.gold, self.btc)
        pilot.activate_btc(self.mt5, self.gold, self.btc, 123, NOW, self.home, self.shared)
        self.position(self.btc, BTC, 88)
        for db in (self.gold, self.btc):
            p = pilot.state(db)
            p.update(end=None, run_policy='continuous', pause=None)
            if db is self.btc:
                p['strategy'] = BTC_SCALP_STRATEGY
            pilot.save(db, p)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        risk.update(end=None, run_policy='continuous', pause=None)
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(risk),))

    def tick_scalp(self, seconds):
        self.clock = NOW + seconds
        self.mt5.symbol_info_tick.return_value.time = self.clock
        self.mt5.symbol_info_tick.return_value.time_msc = self.clock * 1000
        # Close must work without entry evaluation, including a blocked spread.
        with patch('demo_pilot.read_gold', side_effect=ValueError('ATR or spread outside allowed range')):
            return pilot.poll_once(self.mt5, self.btc, 123, self.clock, self.home/'btc.pause', shared=self.shared)

    def fill_close(self, request):
        self.assertEqual((request['symbol'], request['position'], request['type'], request['volume']), (BTC, 88, 1, .01))
        self.positions[:] = [p for p in self.positions if p.symbol != BTC]
        self.deals.append(Record(ticket=999, order=998, position_id=88, symbol=BTC,
            entry=1, type=1, volume=.01, price=99.1, magic=execution.MAGIC,
            comment=request['comment'], profit=-.01, commission=0, swap=0, fee=0,
            time=self.clock, reason=0))
        self.mt5.account_info.return_value.balance -= .01
        return Record(retcode=10009, order=998, deal=999)

    def test_timer_closes_losing_trade_once_even_when_paused_and_spread_blocked(self):
        self.start_scalp()
        self.positions[1].profit = -.01
        self.mt5.order_send.side_effect = self.fill_close
        self.tick_scalp(59)
        self.mt5.order_send.assert_not_called()
        p = pilot.state(self.btc)
        p['pause'] = 'Paused by owner'
        pilot.save(self.btc, p)
        result = self.tick_scalp(60)
        self.assertEqual(result['execution']['status'], 'closed')
        self.assertEqual(result['execution']['close_reason'], 'timed')
        self.assertEqual(result['pilot']['realized_net_usd'], -.01)
        self.assertEqual([p.symbol for p in self.positions], [GOLD])
        self.tick_scalp(65)
        self.assertEqual(self.mt5.order_send.call_count, 1)
        self.assertEqual(pilot.cooldown_remaining(self.btc, pilot.state(self.btc), NOW+119), 1)
        self.assertEqual(pilot.cooldown_remaining(self.btc, pilot.state(self.btc), NOW+120), 0)

    def test_ambiguous_close_is_not_sent_twice_after_restart(self):
        self.start_scalp()
        self.mt5.order_send.side_effect = TimeoutError('lost response')
        self.tick_scalp(60)
        self.tick_scalp(65)
        self.assertEqual(self.mt5.order_send.call_count, 1)
        self.assertEqual(execution._attempt(self.btc)['phase'], 'close')
        self.assertEqual(execution._attempt(self.btc)['state'], 'needs_attention')

    def test_stale_quote_defers_timer_until_fresh(self):
        self.start_scalp()
        self.mt5.order_send.side_effect = self.fill_close
        self.clock = NOW+60
        with patch('demo_pilot.read_gold', side_effect=ValueError('stale')):
            pilot.poll_once(self.mt5, self.btc, 123, self.clock, self.home/'btc.pause', shared=self.shared)
        self.mt5.order_send.assert_not_called()
        self.tick_scalp(65)
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_m1_request_keeps_lot_and_spread_limits(self):
        self.mt5.copy_rates_from_pos.return_value = [dict(time=NOW-(250-i)*60, open=100, high=101, low=99, close=100) for i in range(250)]
        request = execution.build_entry_request(self.mt5, 123, 'buy', NOW, 0, execution=True,
            bar_seconds=60, trend_demo=True, symbol=BTC)
        self.assertEqual(request['volume'], .01)
        self.mt5.copy_rates_from_pos.assert_called_with(BTC, self.mt5.TIMEFRAME_M1, 1, 250)
        self.mt5.symbol_info_tick.return_value.ask = 101
        with self.assertRaisesRegex(ValueError, 'ATR or spread'):
            execution.build_entry_request(self.mt5, 123, 'buy', NOW, 0, execution=True,
                bar_seconds=60, trend_demo=True, symbol=BTC)

    def test_migration_preserves_limits_and_open_position(self):
        self.start_scalp()
        for db in (self.gold, self.btc):
            p = pilot.state(db)
            p['code'] = migration['PREVIOUS_CODE']
            if db is self.btc:
                p['strategy'] = pilot.BTC_STRATEGY
            pilot.save(db, p)
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        risk['code'] = migration['PREVIOUS_CODE']
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(risk),))
        before = dict(execution._attempt(self.btc))
        result = migration['migrate'](self.mt5, self.gold, self.btc, 123, NOW, pilot.identity(),
            migration['PREVIOUS_CODE'], self.home/'scalp-backup')
        self.assertEqual(dict(execution._attempt(self.btc)), before)
        after = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        for key in ('initial_balance', 'initial_equity', 'day_equity', 'peak', 'start', 'end'):
            self.assertEqual(after[key], risk[key])
        self.assertEqual(pilot.state(self.btc)['strategy'], BTC_SCALP_STRATEGY)
        self.assertEqual(result['order_sent'], False)
        self.mt5.order_send.assert_not_called()

    def test_changed_code_never_sends_timed_close(self):
        self.start_scalp()
        p = pilot.state(self.btc)
        p['code'] = 'changed'
        pilot.save(self.btc, p)
        self.tick_scalp(60)
        self.mt5.order_send.assert_not_called()

    def test_migration_refuses_account_pause_without_resetting_it(self):
        self.start_scalp()
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        risk.update(code=migration['PREVIOUS_CODE'], pause='Daily equity loss limit reached')
        with self.gold:
            self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(risk),))
        with self.assertRaises(ValueError):
            migration['review'](self.mt5, self.gold, self.btc, 123, NOW, pilot.identity(), migration['PREVIOUS_CODE'])
        self.assertEqual(json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0]), risk)
        self.mt5.order_send.assert_not_called()

    def test_confirmed_close_can_reenter_only_after_cooldown_on_new_bar(self):
        self.start_scalp()
        self.mt5.order_send.side_effect = self.fill_close
        self.tick_scalp(60)
        p = pilot.state(self.btc)
        p['last_bar'] = NOW - 60
        pilot.save(self.btc, p)
        def enter(request):
            self.assertNotIn('position', request)
            self.assertEqual((request['symbol'], request['volume']), (BTC, .01))
            self.positions.append(Record(ticket=89, symbol=BTC, type=request['type'], volume=.01,
                price_open=request['price'], sl=request['sl'], tp=request['tp'], magic=execution.MAGIC,
                comment=request['comment'], profit=0))
            self.deals.append(Record(ticket=189, order=89, position_id=89, symbol=BTC,
                entry=0, type=request['type'], volume=.01, price=request['price'], magic=execution.MAGIC,
                comment=request['comment'], profit=0, commission=0, swap=0, fee=0, time=self.clock))
            return Record(retcode=10009, order=89, deal=189)
        self.mt5.order_send.side_effect = enter
        for elapsed, sends in ((119, 1), (120, 2), (125, 2)):
            self.clock = NOW + elapsed
            self.mt5.symbol_info_tick.return_value.time = self.clock
            self.mt5.symbol_info_tick.return_value.time_msc = self.clock * 1000
            self.mt5.copy_rates_from_pos.return_value = [dict(time=(self.clock//60-250+i)*60,
                open=100, high=101, low=99, close=100) for i in range(250)]
            with patch('demo_pilot.assess', return_value=dict(bar_time=self.clock//60*60-60, signal='long', reason='evaluated')), patch('demo_pilot.entry_allowed', return_value=True):
                result = pilot.poll_once(self.mt5, self.btc, 123, self.clock, self.home/'btc.pause', shared=self.shared)
            self.assertEqual(self.mt5.order_send.call_count, sends, result)
        self.assertEqual(execution._attempt(self.btc)['position_ticket'], 89)
