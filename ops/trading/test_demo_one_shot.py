"""Fake MT5 boundary for a supervised, never-live gold smoke order."""
import unittest
from types import SimpleNamespace as Record
from unittest.mock import Mock

from demo_one_shot import build_entry_request


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


if __name__ == "__main__":
    unittest.main()
