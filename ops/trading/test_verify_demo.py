import unittest
from types import SimpleNamespace
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

spec = spec_from_file_location("verify_demo", Path(__file__).with_name("verify-demo.py"))
module = module_from_spec(spec)
spec.loader.exec_module(module)


class AccountGuardTest(unittest.TestCase):
    def test_only_matching_connected_demo_with_algo_off_passes(self):
        account = dict(trade_mode=0, login=123, server="VTMarkets-Demo")
        terminal = dict(connected=True, trade_allowed=False)
        module.validate_account(SimpleNamespace(**account), SimpleNamespace(**terminal), 123, "VTMarkets-Demo")
        for field, value in (("trade_mode", 2), ("login", 456), ("server", "other")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.validate_account(SimpleNamespace(**(account | {field: value})), SimpleNamespace(**terminal), 123, "VTMarkets-Demo")
        for field, value in (("connected", False), ("trade_allowed", True)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                module.validate_account(SimpleNamespace(**account), SimpleNamespace(**(terminal | {field: value})), 123, "VTMarkets-Demo")
        with self.assertRaises(ValueError):
            module.validate_account(None, None, 123, "VTMarkets-Demo")


if __name__ == "__main__":
    unittest.main()
