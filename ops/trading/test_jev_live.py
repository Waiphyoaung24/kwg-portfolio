import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import jev_live
from test_observe_gold import history
from test_simulate_gold import SPEC

class LiveTest(unittest.TestCase):
    def test_mid_candle_start_is_manual_only_and_never_calls_orders(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); sdk=Mock(); sdk.order_send.side_effect=AssertionError('Orders forbidden')
            def read(mt5,login,now,health,**kwargs):
                self.assertTrue(kwargs['execution'])
                health['sampled_at']=251*900+60
                return Mock(bid=100.,ask=100.01),history()
            with patch.dict('os.environ',{'MT5_DEMO_LOGIN':'123','MT5_SERVER_OFFSET_SECONDS':'0'}), \
                 patch.object(jev_live,'read_gold',side_effect=read),patch.object(jev_live,'read_contract',return_value=SPEC):
                jev_live.run(sdk,root,root/'feed.json',once=True)
            value=json.loads((root/'feed.json').read_text())
            self.assertEqual(value['status'],'ready')
            self.assertFalse(value['sample']['eligible'])
            sdk.order_send.assert_not_called()

    def test_failed_feed_clears_old_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.dict('os.environ',{'MT5_DEMO_LOGIN':'123','MT5_SERVER_OFFSET_SECONDS':'0'}), \
                 patch.object(jev_live,'read_gold',side_effect=ValueError('private diagnostic')):
                jev_live.run(Mock(),root,root/'feed.json',once=True)
            value=json.loads((root/'feed.json').read_text())
            self.assertEqual(value['status'],'unavailable')
            self.assertNotIn('sample',value)
            self.assertNotIn('private diagnostic',str(value))
