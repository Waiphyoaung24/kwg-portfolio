"""Previously reviewed manual receipts remain strict across strategy deployments."""
import json
import unittest
from types import SimpleNamespace as Record

import demo_pilot as pilot
import test_two_symbol_pilot as two_symbol
from test_demo_one_shot import NOW


class AcknowledgedDealsTest(unittest.TestCase):
    def setUp(self):
        two_symbol.TwoSymbolTest.setUp(self)
        two_symbol.TwoSymbolTest.migrate(self)
        self.receipt = dict(ticket=591104975, order=805998437, position_id=805998317,
            symbol='BTCUSD', type=0, entry=1, reason=0, magic=0, comment='', time=NOW,
            time_msc=NOW * 1000, volume=4.0, price=83894.57,
            profit=-187.76, commission=0.0, swap=0.0, fee=0.0)
        self.deals.append(Record(**self.receipt))
        self.mt5.account_info.return_value.balance = 10000 - 187.76
        risk = json.loads(self.gold.execute('SELECT data FROM account_limits').fetchone()[0])
        risk['acknowledged_manual_deals'] = [self.receipt.copy()]
        self.gold.execute('UPDATE account_limits SET data=?', (json.dumps(risk),))
        self.gold.commit()

    def test_exact_acknowledgement_reconciles_costs_without_orders(self):
        pilot.SharedAccount(self.gold, self.btc).check(self.mt5, 123, NOW)
        self.mt5.order_send.assert_not_called()

    def test_changed_receipt_is_rejected(self):
        self.deals[0].price += 1
        with self.assertRaisesRegex(ValueError, 'Acknowledged manual deal history changed'):
            pilot.SharedAccount(self.gold, self.btc).check(self.mt5, 123, NOW)

    def test_missing_acknowledged_receipt_is_rejected(self):
        self.deals.clear()
        with self.assertRaisesRegex(ValueError, 'Acknowledged manual deal history changed'):
            pilot.SharedAccount(self.gold, self.btc).check(self.mt5, 123, NOW)

    def test_new_manual_deal_is_not_implicitly_acknowledged(self):
        self.deals.append(Record(**{**self.receipt, 'ticket': 591104976}))
        with self.assertRaisesRegex(ValueError, 'Unrelated account activity'):
            pilot.SharedAccount(self.gold, self.btc).check(self.mt5, 123, NOW)
