"""Fake MT5 boundary for a supervised, never-live gold smoke order."""
import unittest
import tempfile
import os
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace as Record
from unittest.mock import Mock, patch

from demo_one_shot import arm_once, build_entry_request, main, open_journal, process_once


NOW = 251 * 900


def fake_mt5(*, enabled=False):
    mt5 = Mock(TIMEFRAME_M15=15, TRADE_ACTION_DEAL=1, ORDER_TYPE_BUY=0,
               ORDER_TYPE_SELL=1, ORDER_TIME_GTC=0, ORDER_FILLING_FOK=0,
               ORDER_FILLING_IOC=1, SYMBOL_TRADE_MODE_FULL=4,
               SYMBOL_FILLING_FOK=1, SYMBOL_FILLING_IOC=2,
               DEAL_REASON_SL=4, DEAL_REASON_TP=5)
    mt5.account_info.return_value = Record(trade_mode=0, login=123,
        server="VTMarkets-Demo", trade_allowed=enabled, trade_expert=enabled,
        equity=10000, currency="USD")
    mt5.terminal_info.return_value = Record(connected=True, trade_allowed=enabled,
        tradeapi_disabled=False)
    mt5.symbol_select.return_value = True
    mt5.symbol_info_tick.return_value = Record(bid=100, ask=100.1, time=NOW,
        time_msc=NOW * 1000)
    mt5.copy_rates_from_pos.return_value = [dict(time=(i + 1) * 900,
        open=100, high=101, low=99, close=100) for i in range(250)]
    mt5.symbol_info.return_value = Record(name="XAUUSD-VIP", point=.01,
        trade_tick_size=.01, digits=2, volume_min=.01, volume_max=100,
        volume_step=.01, trade_mode=4, trade_exemode=2, filling_mode=1,
        order_mode=49, trade_stops_level=10, trade_freeze_level=0)
    mt5.positions_get.return_value = ()
    mt5.orders_get.return_value = ()
    mt5.order_calc_profit.return_value = -4
    mt5.history_orders_get.return_value = ()
    return mt5


class EntryRequestTest(unittest.TestCase):
    def test_preview_is_protected_minimum_lot_without_sending(self):
        mt5 = fake_mt5()
        request = build_entry_request(mt5, 123, "buy", NOW, 0, execution=False)
        self.assertEqual((request["action"], request["type"], request["volume"],
                          request["type_filling"]), (1, 0, .01, 0))
        self.assertEqual(request["symbol"], "XAUUSD-VIP")
        self.assertLess(request["sl"], 100)
        self.assertGreater(request["tp"], 100.1)
        self.assertTrue(request["magic"])
        self.assertLessEqual(len(request["comment"]), 31)
        self.assertNotEqual(request["comment"], build_entry_request(
            mt5, 123, "buy", NOW, 0, execution=False)["comment"])
        mt5.order_send.assert_not_called()

    def test_execution_requires_enabled_terminal_and_correct_direction(self):
        mt5 = fake_mt5(enabled=True)
        request = build_entry_request(mt5, 123, "sell", NOW, 0, execution=True)
        self.assertEqual(request["type"], mt5.ORDER_TYPE_SELL)
        self.assertGreater(request["sl"], 100.1)
        self.assertLess(request["tp"], 100)
        mt5.terminal_info.return_value.trade_allowed = False
        with self.assertRaises(ValueError):
            build_entry_request(mt5, 123, "sell", NOW, 0, execution=True)
        mt5.order_send.assert_not_called()

    def test_occupied_symbol_and_missing_broker_metadata_block(self):
        for field, value in (("positions_get", (Record(symbol="XAUUSD-VIP"),)),
                             ("orders_get", (Record(symbol="XAUUSD-VIP"),))):
            mt5 = fake_mt5()
            getattr(mt5, field).return_value = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_entry_request(mt5, 123, "buy", NOW, 0, execution=False)
            mt5.order_send.assert_not_called()
        for field, value in (("filling_mode", 0), ("trade_stops_level", 500),
                             ("trade_freeze_level", 500), ("trade_tick_size", None)):
            mt5 = fake_mt5()
            setattr(mt5.symbol_info.return_value, field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                build_entry_request(mt5, 123, "buy", NOW, 0, execution=False)
            mt5.order_send.assert_not_called()

    def test_minimum_lot_risk_and_unknown_profit_block(self):
        for profit in (-11, None):
            mt5 = fake_mt5()
            mt5.order_calc_profit.return_value = profit
            with self.subTest(profit=profit), self.assertRaises(ValueError):
                build_entry_request(mt5, 123, "buy", NOW, 0, execution=False)
            mt5.order_send.assert_not_called()


class AttemptTest(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"MT5_SERVER_OFFSET_SECONDS": "0"})
        env.start()
        self.addCleanup(env.stop)
        clock = patch("demo_one_shot.time.time", return_value=NOW)
        clock.start()
        self.addCleanup(clock.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "one-shot.sqlite3"
        self.db = open_journal(self.path, 123)
        self.addCleanup(self.db.close)
        self.mt5 = fake_mt5(enabled=True)
        self.mt5.order_check.return_value = Record(retcode=0)
        self.mt5.history_deals_get.return_value = ()

    def test_arm_is_exclusive_and_survives_reopen(self):
        arm_id = arm_once(self.db, "buy", NOW)
        self.assertTrue(arm_id)
        with self.assertRaises(ValueError):
            arm_once(self.db, "sell", NOW)
        with self.assertRaises(ValueError):
            open_journal(self.path, 456)
        reopened = open_journal(self.path, 123)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.execute("SELECT count(*) FROM attempts").fetchone()[0], 1)
        self.assertEqual(reopened.execute("SELECT state FROM attempts").fetchone()[0], "armed")

    def test_new_attempt_keeps_closed_history_and_blocks_unresolved_one(self):
        first = arm_once(self.db, "buy", NOW)
        with self.db:
            self.db.execute("UPDATE attempts SET state='closed', closed_at=?, realized_net_usd=? WHERE id=?",
                            (NOW + 61, -.24, first))
        second = arm_once(self.db, "sell", NOW + 120)
        self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            arm_once(self.db, "buy", NOW + 121)
        self.assertEqual(process_once(self.mt5, self.db, NOW + 1021, allow_entry=False)["status"],
                         "disarmed")
        rows = self.db.execute("SELECT id, side, state, realized_net_usd FROM attempts ORDER BY rowid").fetchall()
        self.assertEqual([tuple(row) for row in rows],
                         [(first, "buy", "closed", -.24), (second, "sell", "disarmed", None)])

    def test_expired_arm_disarms_without_order(self):
        arm_once(self.db, "buy", NOW)
        result = process_once(self.mt5, self.db, NOW + 901)
        self.assertEqual(result["status"], "disarmed")
        self.mt5.order_send.assert_not_called()

    def test_restart_of_unsubmitted_arm_disarms(self):
        arm_once(self.db, "buy", NOW)
        reopened = open_journal(self.path, 123)
        self.addCleanup(reopened.close)
        self.assertEqual(process_once(self.mt5, reopened, NOW + 1, allow_entry=False)["status"],
                         "disarmed")
        self.mt5.order_send.assert_not_called()

    def test_order_check_rejection_does_not_send(self):
        arm_once(self.db, "buy", NOW)
        self.mt5.order_check.return_value = Record(retcode=10030)
        result = process_once(self.mt5, self.db, NOW)
        self.assertEqual(result["status"], "disarmed")
        self.mt5.order_send.assert_not_called()

    def test_python_sdk_without_symbol_filling_constants_reaches_broker_check(self):
        arm_once(self.db, "buy", NOW)
        del self.mt5.SYMBOL_FILLING_FOK
        del self.mt5.SYMBOL_FILLING_IOC
        self.mt5.order_check.return_value = Record(retcode=10030)
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "disarmed")
        self.mt5.order_check.assert_called_once()
        self.mt5.order_send.assert_not_called()

    def test_quote_goes_stale_during_order_check_and_blocks_send(self):
        arm_once(self.db, "buy", NOW)

        def check(request):
            self.mt5.symbol_info_tick.return_value.time = NOW - 31
            self.mt5.symbol_info_tick.return_value.time_msc = (NOW - 31) * 1000
            return Record(retcode=0)

        self.mt5.order_check.side_effect = check
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "disarmed")
        self.mt5.order_send.assert_not_called()

    def test_symbol_trading_conditions_change_during_check_and_block_send(self):
        arm_once(self.db, "buy", NOW)

        def check(request):
            self.mt5.symbol_info.return_value.trade_mode = 3
            return Record(retcode=0)

        self.mt5.order_check.side_effect = check
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "disarmed")
        self.mt5.order_send.assert_not_called()

    def test_gold_occupancy_appears_during_check_and_blocks_send(self):
        arm_once(self.db, "buy", NOW)

        def check(request):
            self.mt5.positions_get.return_value = (Record(symbol="XAUUSD-VIP"),)
            return Record(retcode=0)

        self.mt5.order_check.side_effect = check
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "disarmed")
        self.mt5.order_send.assert_not_called()

    def test_lost_entry_reply_freezes_and_restart_never_resends(self):
        arm_once(self.db, "buy", NOW)
        self.mt5.order_send.side_effect = TimeoutError("lost reply")
        result = process_once(self.mt5, self.db, NOW)
        self.assertEqual(result["status"], "needs_attention")
        self.assertEqual(self.db.execute("SELECT state FROM attempts").fetchone()[0],
                         "needs_attention")
        self.assertEqual(self.mt5.order_send.call_count, 1)
        reopened = open_journal(self.path, 123)
        self.addCleanup(reopened.close)
        process_once(self.mt5, reopened, NOW + 1)
        self.assertEqual(self.mt5.order_send.call_count, 1)
        self.assertTrue(self.mt5.positions_get.called)
        self.assertTrue(self.mt5.orders_get.called)
        self.assertTrue(self.mt5.history_deals_get.called)

    def test_crash_after_durable_submitting_never_resends(self):
        arm_once(self.db, "buy", NOW)
        self.mt5.order_send.side_effect = SystemExit("process died")
        with self.assertRaises(SystemExit):
            process_once(self.mt5, self.db, NOW)
        self.assertEqual(self.db.execute("SELECT state FROM attempts").fetchone()[0],
                         "submitting")
        reopened = open_journal(self.path, 123)
        self.addCleanup(reopened.close)
        self.assertEqual(process_once(self.mt5, reopened, NOW + 1,
                                      allow_entry=False)["status"], "needs_attention")
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_definite_entry_rejection_disarms_when_broker_has_no_fill(self):
        arm_once(self.db, "buy", NOW)
        self.mt5.order_send.return_value = Record(retcode=10030, order=0, deal=0)
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "disarmed")
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_success_requires_matching_protected_position_then_ticket_close(self):
        arm_once(self.db, "sell", NOW)
        position = None
        deals = []

        def positions_get(*, symbol):
            return () if position is None else (position,)

        def send(request):
            nonlocal position
            if "position" not in request:
                position = Record(ticket=77, identifier=77, symbol="XAUUSD-VIP",
                    magic=request["magic"], comment=request["comment"], volume=request["volume"],
                    type=request["type"], price_open=request["price"], sl=request["sl"], tp=request["tp"])
                deals.append(Record(position_id=77, entry=0, symbol="XAUUSD-VIP", magic=20260929,
                                    volume=.01, type=1, profit=0, commission=-.2,
                                    swap=0, fee=0, time=NOW))
                return Record(retcode=10009, order=77, deal=88)
            self.assertEqual(request["position"], 77)
            self.assertEqual(request["type"], self.mt5.ORDER_TYPE_BUY)
            position = None
            deals.append(Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=20260929,
                                order=78, ticket=89, volume=.01, type=0, profit=1, commission=0,
                                swap=0, fee=0, time=NOW + 61))
            return Record(retcode=10009, order=78, deal=89)

        self.mt5.positions_get.side_effect = positions_get
        self.mt5.order_send.side_effect = send
        self.mt5.history_deals_get.side_effect = lambda *args, **kwargs: tuple(deals)
        opened = process_once(self.mt5, self.db, NOW)
        self.assertEqual(opened["status"], "open")
        self.assertEqual(opened["volume"], .01)
        self.assertEqual(process_once(self.mt5, self.db, NOW + 59)["status"], "open")
        self.mt5.symbol_info_tick.return_value.time = NOW + 61
        self.mt5.symbol_info_tick.return_value.time_msc = (NOW + 61) * 1000
        self.assertEqual(process_once(self.mt5, self.db, NOW + 61)["status"], "closed")
        self.assertEqual(self.mt5.order_send.call_count, 2)
        self.assertEqual(self.db.execute("SELECT state FROM attempts").fetchone()[0], "closed")
        self.assertEqual(process_once(self.mt5, self.db, NOW + 62)["realized_net_usd"], .8)
        self.assertEqual(process_once(self.mt5, self.db, NOW + 62)["close_reason"], "timed")

    def test_reconcile_uses_broker_offset_and_reports_utc_close(self):
        arm_once(self.db, "buy", NOW)
        request = {"type": 0, "volume": .01, "comment": "kwg-demo-test"}
        with self.db:
            self.db.execute("UPDATE attempts SET state='needs_attention', phase='close', "
                            "request_json=?, order_id=77, deal_id=88, position_ticket=77, "
                            "opened_at=?, close_order_id=78, close_deal_id=89",
                            (json.dumps(request), NOW))
        deals = (
            Record(position_id=77, entry=0, symbol="XAUUSD-VIP", magic=20260929,
                   comment="kwg-demo-test", order=77, ticket=88, type=0,
                   volume=.01, profit=0, commission=0, swap=0, fee=0,
                   time=NOW + 10800),
            Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=20260929,
                   order=78, ticket=89, type=1, volume=.01, profit=-1,
                   commission=0, swap=0, fee=0, time=NOW + 61 + 10800),
        )

        def history(start, end):
            self.assertEqual(int(start.timestamp()), NOW - 120 + 10800)
            self.assertEqual(int(end.timestamp()), NOW + 62 + 60 + 10800)
            return deals

        self.mt5.history_deals_get.side_effect = history
        with patch.dict(os.environ, {"MT5_SERVER_OFFSET_SECONDS": "10800"}):
            result = process_once(self.mt5, self.db, NOW + 62, allow_entry=False)
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["closed_at"], NOW + 61)
        self.assertEqual(result["close_reason"], "timed")
        self.assertEqual(result["realized_net_usd"], -1)
        self.mt5.order_send.assert_not_called()

    def test_lost_timed_close_reply_then_stop_exit_is_attributed_to_stop(self):
        arm_once(self.db, "buy", NOW)
        position = None
        deals = []

        def send(request):
            nonlocal position
            if "position" in request:
                return None
            position = Record(ticket=77, symbol="XAUUSD-VIP", magic=request["magic"],
                              comment=request["comment"], volume=.01, type=0,
                              price_open=request["price"], sl=request["sl"], tp=request["tp"])
            deals.append(Record(position_id=77, entry=0, symbol="XAUUSD-VIP", magic=request["magic"],
                                comment=request["comment"], order=78, ticket=88, type=0,
                                volume=.01, price=request["price"], profit=0,
                                commission=0, swap=0, fee=0, time=NOW))
            return Record(retcode=10009, order=78, deal=88)

        self.mt5.positions_get.side_effect = lambda *, symbol: (position,) if position else ()
        self.mt5.history_deals_get.side_effect = lambda *args: tuple(deals)
        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "open")
        self.mt5.symbol_info_tick.return_value.time = NOW + 61
        self.mt5.symbol_info_tick.return_value.time_msc = (NOW + 61) * 1000
        self.assertEqual(process_once(self.mt5, self.db, NOW + 61)["status"], "needs_attention")
        position = None
        deals.append(Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=0,
                            order=79, ticket=89, type=1, reason=self.mt5.DEAL_REASON_SL,
                            volume=.01, profit=-4, commission=0, swap=0, fee=0,
                            time=NOW + 62))
        result = process_once(self.mt5, self.db, NOW + 62, allow_entry=False)
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["close_reason"], "stop loss")
        self.assertEqual(self.mt5.order_send.call_count, 2)

    def test_broker_protection_closes_before_first_position_read(self):
        arm_once(self.db, "buy", NOW)
        self.mt5.order_calc_profit.return_value = -10

        def send(request):
            self.mt5.account_info.return_value.equity = 9990
            self.mt5.history_orders_get.return_value = (
                Record(ticket=78, position_id=77, symbol="XAUUSD-VIP", magic=request["magic"],
                       type=request["type"], volume_initial=.01, sl=request["sl"],
                       tp=request["tp"], comment=request["comment"]),)
            self.mt5.history_deals_get.return_value = (
                Record(position_id=77, entry=0, symbol="XAUUSD-VIP", magic=request["magic"],
                       comment=request["comment"], order=78, ticket=88, type=request["type"],
                       volume=.01, price=request["price"], profit=0, commission=-.2,
                       swap=0, fee=0, time=NOW),
                Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=0,
                       comment="sl 96.10", order=79, ticket=89, type=1,
                       reason=self.mt5.DEAL_REASON_SL, volume=.01, profit=-4,
                       commission=0, swap=0, fee=0, time=NOW + 1))
            return Record(retcode=10009, order=78, deal=88)

        self.mt5.order_send.side_effect = send
        result = process_once(self.mt5, self.db, NOW + 1)
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["close_reason"], "stop loss")
        self.assertEqual(result["realized_net_usd"], -4.2)

    def test_manual_early_close_after_observed_position_needs_attention(self):
        arm_once(self.db, "buy", NOW)
        position = None
        deals = []

        def send(request):
            nonlocal position
            position = Record(ticket=77, symbol="XAUUSD-VIP", magic=request["magic"],
                              comment=request["comment"], volume=.01, type=request["type"],
                              price_open=request["price"], sl=request["sl"], tp=request["tp"])
            deals.append(Record(position_id=77, entry=0, symbol="XAUUSD-VIP",
                                magic=request["magic"], comment=request["comment"],
                                order=78, ticket=88, type=0, volume=.01, price=request["price"],
                                profit=0, commission=0, swap=0, fee=0, time=NOW))
            return Record(retcode=10009, order=78, deal=88)

        self.mt5.positions_get.side_effect = lambda *, symbol: () if position is None else (position,)
        self.mt5.history_deals_get.side_effect = lambda *args: tuple(deals)
        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "open")
        position = None
        deals.append(Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=0,
                            type=1, reason=0, volume=.01, profit=1, commission=0,
                            swap=0, fee=0, time=NOW + 1))
        self.assertEqual(process_once(self.mt5, self.db, NOW + 1)["status"], "needs_attention")

    def test_fast_close_without_historical_protection_stays_unknown(self):
        arm_once(self.db, "buy", NOW)

        def send(request):
            self.mt5.history_deals_get.return_value = (
                Record(position_id=77, entry=0, symbol="XAUUSD-VIP", magic=request["magic"],
                       comment=request["comment"], order=78, ticket=88, type=request["type"],
                       volume=.01, price=request["price"], profit=0, commission=0,
                       swap=0, fee=0, time=NOW),
                Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=0,
                       comment="manual close", order=79, ticket=89, type=1,
                       reason=0, volume=.01, profit=1, commission=0,
                       swap=0, fee=0, time=NOW + 1))
            return Record(retcode=10009, order=78, deal=88)

        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW + 1)["status"], "needs_attention")

    def test_fast_stop_exit_with_missing_target_is_not_confirmed(self):
        arm_once(self.db, "buy", NOW)

        def send(request):
            self.mt5.history_orders_get.return_value = (
                Record(ticket=78, position_id=77, symbol="XAUUSD-VIP", magic=request["magic"],
                       type=request["type"], volume_initial=.01, sl=request["sl"], tp=0),)
            self.mt5.history_deals_get.return_value = (
                Record(position_id=77, entry=0, symbol="XAUUSD-VIP", magic=request["magic"],
                       comment=request["comment"], order=78, ticket=88, type=request["type"],
                       volume=.01, price=request["price"], profit=0, commission=0,
                       swap=0, fee=0, time=NOW),
                Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=0,
                       order=79, ticket=89, type=1, reason=self.mt5.DEAL_REASON_SL,
                       volume=.01, profit=-4, commission=0, swap=0, fee=0, time=NOW + 1))
            return Record(retcode=10009, order=78, deal=88)

        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW + 1)["status"], "needs_attention")

    def test_missing_protection_never_reports_open(self):
        arm_once(self.db, "buy", NOW)

        def send(request):
            self.mt5.positions_get.return_value = (Record(ticket=77, identifier=77,
                symbol="XAUUSD-VIP", magic=request["magic"], comment=request["comment"],
                volume=request["volume"], type=request["type"], price_open=request["price"],
                sl=0, tp=request["tp"]),)
            return Record(retcode=10009, order=77, deal=88)

        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "needs_attention")
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_partial_fill_uses_broker_volume(self):
        arm_once(self.db, "buy", NOW)

        def send(request):
            self.mt5.positions_get.return_value = (Record(ticket=77, identifier=77,
                symbol="XAUUSD-VIP", magic=request["magic"], comment=request["comment"],
                volume=.005, type=request["type"], price_open=request["price"],
                sl=request["sl"], tp=request["tp"]),)
            return Record(retcode=10010, order=77, deal=88)

        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW)["volume"], .005)
        self.assertEqual(self.db.execute("SELECT state FROM attempts").fetchone()[0], "open")

    def test_unrelated_position_does_not_confirm_entry(self):
        arm_once(self.db, "buy", NOW)

        def send(request):
            self.mt5.positions_get.return_value = (Record(ticket=77, identifier=77,
                symbol="XAUUSD-VIP", magic=1, comment="someone-else", volume=.01,
                type=request["type"], price_open=request["price"],
                sl=request["sl"], tp=request["tp"]),)
            return Record(retcode=10009, order=78, deal=88)

        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "needs_attention")

    def test_prior_magic_deals_cannot_close_unconfirmed_attempt(self):
        arm_once(self.db, "buy", NOW)
        self.mt5.order_send.return_value = None
        self.mt5.history_deals_get.return_value = (
            Record(position_id=88, entry=0, symbol="XAUUSD-VIP", magic=20260929,
                   comment="old-attempt", order=11, ticket=12,
                   profit=0, commission=0, swap=0, fee=0, time=NOW - 30),
            Record(position_id=88, entry=1, symbol="XAUUSD-VIP", magic=20260929,
                   comment="old-attempt", order=13, ticket=14,
                   profit=1, commission=0, swap=0, fee=0, time=NOW - 20))
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "needs_attention")

    def test_unrelated_gold_position_prevents_closed_result(self):
        arm_once(self.db, "buy", NOW)
        protected = None
        entered = False
        deals = []

        def send(request):
            nonlocal protected, entered
            if "position" not in request:
                entered = True
                protected = Record(ticket=77, identifier=77, symbol="XAUUSD-VIP",
                    magic=request["magic"], comment=request["comment"], volume=request["volume"],
                    type=request["type"], price_open=request["price"], sl=request["sl"], tp=request["tp"])
                return Record(retcode=10009, order=77, deal=88)
            protected = None
            deals.append(Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=20260929,
                                profit=1, commission=0, swap=0, fee=0, time=NOW + 61))
            return Record(retcode=10009, order=78, deal=89)

        def positions_get(*, symbol):
            if not entered:
                return ()
            if protected:
                return (protected,)
            return (Record(ticket=99, symbol="XAUUSD-VIP", magic=0, comment="other"),)

        self.mt5.order_send.side_effect = send
        self.mt5.positions_get.side_effect = positions_get
        self.mt5.history_deals_get.side_effect = lambda *args: tuple(deals)
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "open")
        self.mt5.symbol_info_tick.return_value.time = NOW + 61
        self.mt5.symbol_info_tick.return_value.time_msc = (NOW + 61) * 1000
        self.assertEqual(process_once(self.mt5, self.db, NOW + 61)["status"], "needs_attention")

    def test_lost_close_reply_keeps_position_and_never_retries(self):
        arm_once(self.db, "buy", NOW)
        position = None

        def send(request):
            nonlocal position
            if "position" not in request:
                position = Record(ticket=77, identifier=77, symbol="XAUUSD-VIP",
                    magic=request["magic"], comment=request["comment"], volume=request["volume"],
                    type=request["type"], price_open=request["price"], sl=request["sl"], tp=request["tp"])
                return Record(retcode=10009, order=77, deal=88)
            raise TimeoutError("close reply lost")

        self.mt5.positions_get.side_effect = lambda *, symbol: (position,) if position else ()
        self.mt5.order_send.side_effect = send
        self.assertEqual(process_once(self.mt5, self.db, NOW)["status"], "open")
        self.mt5.symbol_info_tick.return_value.time = NOW + 61
        self.mt5.symbol_info_tick.return_value.time_msc = (NOW + 61) * 1000
        self.assertEqual(process_once(self.mt5, self.db, NOW + 61)["status"], "needs_attention")
        process_once(self.mt5, self.db, NOW + 62, allow_entry=False)
        self.assertEqual(self.mt5.order_send.call_count, 2)
        self.assertIsNotNone(position.sl)


class CliTest(unittest.TestCase):
    def test_alternate_journal_name_cannot_arm_another_attempt(self):
        with tempfile.TemporaryDirectory() as root:
            alternate = Path(root) / "another.sqlite3"
            mt5 = fake_mt5(enabled=True)
            mt5.order_check.return_value = Record(retcode=0)
            mt5.order_send.return_value = None
            with (patch("demo_one_shot.Path.home", return_value=Path(root)),
                  patch("demo_one_shot.SNAPSHOT", Path(root) / "execution.json"),
                  patch("demo_one_shot.time.time", return_value=NOW),
                  patch.dict(os.environ, {"MT5_DEMO_LOGIN": "123",
                                       "MT5_SERVER_OFFSET_SECONDS": "0"}),
                  patch.dict(sys.modules, {"MetaTrader5": mt5}),
                  patch("sys.stderr", io.StringIO()),
                  patch.object(sys, "argv", ["demo_one_shot.py", "arm", "--side", "buy",
                                             "--state", str(alternate), "--enable-demo-execution"])):
                with self.assertRaises(SystemExit):
                    main()
            self.assertFalse(alternate.exists())

    def test_private_preview_creates_no_journal_and_never_sends(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "gold-one-shot.sqlite3"
            mt5 = fake_mt5()
            output = io.StringIO()
            with (patch("demo_one_shot.Path.home", return_value=Path(root)),
                  patch("demo_one_shot.time.time", return_value=NOW),
                  patch.dict(os.environ, {"MT5_DEMO_LOGIN": "123",
                                       "MT5_SERVER_OFFSET_SECONDS": "0"}),
                  patch.dict(sys.modules, {"MetaTrader5": mt5}),
                  patch.object(sys, "argv", ["demo_one_shot.py", "preview", "--side", "buy",
                                             "--state", str(state)]),
                  patch("sys.stdout", output)):
                main()
            self.assertFalse(state.exists())
            self.assertFalse(state.with_suffix(".lock").exists())
            preview = json.loads(output.getvalue())
            self.assertFalse(preview["order_sent"])
            self.assertEqual(preview["modeled_stop_pct_of_equity"], .04)
            mt5.order_send.assert_not_called()

    def test_resume_without_journal_is_inert(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "gold-one-shot.sqlite3"
            snapshot = Path(root) / "execution.json"
            with (patch("demo_one_shot.Path.home", return_value=Path(root)),
                  patch("demo_one_shot.SNAPSHOT", snapshot),
                  patch.object(sys, "argv", ["demo_one_shot.py", "resume", "--state", str(state)])):
                main()
            self.assertFalse(state.exists())
            self.assertEqual(json.loads(snapshot.read_text())["status"], "disarmed")


if __name__ == "__main__":
    unittest.main()
