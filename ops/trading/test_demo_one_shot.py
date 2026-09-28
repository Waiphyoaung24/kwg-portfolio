"""Fake MT5 boundary for a supervised, never-live gold smoke order."""
import unittest
import tempfile
import os
import io
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
               SYMBOL_FILLING_FOK=1, SYMBOL_FILLING_IOC=2)
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

    def test_quote_goes_stale_during_order_check_and_blocks_send(self):
        arm_once(self.db, "buy", NOW)

        def check(request):
            self.mt5.symbol_info_tick.return_value.time = NOW - 31
            self.mt5.symbol_info_tick.return_value.time_msc = (NOW - 31) * 1000
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
                                    profit=0, commission=-.2, swap=0, fee=0, time=NOW))
                return Record(retcode=10009, order=77, deal=88)
            self.assertEqual(request["position"], 77)
            self.assertEqual(request["type"], self.mt5.ORDER_TYPE_BUY)
            position = None
            deals.append(Record(position_id=77, entry=1, symbol="XAUUSD-VIP", magic=20260929,
                                profit=1, commission=0, swap=0, fee=0, time=NOW + 61))
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
    def test_private_preview_creates_no_journal_and_never_sends(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "one-shot.sqlite3"
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
            self.assertIn('"order_sent": false', output.getvalue())
            mt5.order_send.assert_not_called()

    def test_resume_without_journal_is_inert(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root) / "one-shot.sqlite3"
            with (patch("demo_one_shot.Path.home", return_value=Path(root)),
                  patch.object(sys, "argv", ["demo_one_shot.py", "resume", "--state", str(state)])):
                main()
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
