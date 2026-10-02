import copy
import json
from pathlib import Path
import tempfile
import unittest

from batch2_adapter import adapt_baseline, protocol_draft, save_adapter, utc_daily
from batch3_adapter import encode, sha, simulator
from batch3_runner import research_module
from gold_experiment import source_hashes
from test_batch3_rehearsal import rehearse


class BaselineAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, windows, costs, _ = rehearse.fixtures()
        data['timestamp_basis'] = 'utc'
        cls.raw = [encode(data), encode(windows), encode(costs)]
        report = simulator()(data, windows=windows, cost_profile=costs)
        report.update(dataset_sha256=sha(cls.raw[0]), windows_sha256=sha(cls.raw[1]),
                      cost_profile_sha256=sha(cls.raw[2]), code_sha256={
                          k: source_hashes()[k] for k in ('simulate-gold.py', 'replay-gold.py', 'gold_signal.py')})
        cls.report = report
        cls.clock = encode({'timestamp_basis': 'utc', 'status': 'unreviewed'})

    def adapt(self, raw=None, report=None, protocol=None):
        return adapt_baseline(*(raw or self.raw), encode(report or self.report), self.clock,
                              protocol or protocol_draft(1))

    def test_draft_never_starts_collection(self):
        draft = protocol_draft(1)
        for key in ('collection_start', 'windows', 'holdout'):
            self.assertIsNone(draft[key])
        self.assertEqual(draft['status'], 'prepared_not_started')
        self.assertEqual(draft['policy_sha256'], research_module().POLICY_SHA256)
        with self.assertRaises(ValueError):
            protocol_draft(True)

    def test_full_cli_report_reconciles_but_never_qualifies(self):
        result = self.adapt()
        self.assertTrue(result['baseline_reproduced'])
        self.assertEqual(result['identity']['report_sha256'], sha(encode(self.report)))
        self.assertEqual(result['qualification'], 'unqualified')
        self.assertEqual(result['validation']['observed_days'], 0)
        self.assertEqual(result['promotion_status'], 'blocked')
        self.assertEqual(result['model_requests'], 0)
        self.assertEqual(len(result['validation']['folds']), 3)
        self.assertTrue(all(f['days'] == 0 for f in result['validation']['folds']))
        self.assertTrue(all(len(k) == 10 for k in result['validation']['daily_returns']))
        self.assertFalse(result['holdout']['evaluated'])
        self.assertNotIn('proposal', result)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'audit.json'
            save_adapter(target, result)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                save_adapter(target, result)
            self.assertEqual(target.read_bytes(), before)

    def test_report_and_time_or_protocol_tampering_rejected(self):
        changed = copy.deepcopy(self.report)
        changed['runs']['lower']['windows']['validation']['summary']['net_pnl_usd'] += 1
        with self.assertRaises(ValueError):
            self.adapt(report=changed)
        data = json.loads(self.raw[0])
        data['timestamp_basis'] = 'raw_broker_epoch_unqualified'
        with self.assertRaises(ValueError):
            self.adapt(raw=[encode(data), *self.raw[1:]])
        changed = protocol_draft(1)
        changed['risk_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.adapt(protocol=changed)
        costs = json.loads(self.raw[2])
        costs['commission']['status'] = 'verified_current'
        with self.assertRaises(ValueError):
            self.adapt(raw=[*self.raw[:2], encode(costs)])

    def test_malformed_json_roots_and_utc_midnight(self):
        with self.assertRaises(ValueError):
            self.adapt(raw=[encode([]), *self.raw[1:]])
        returns = utc_daily({'equity_curve': [
            {'bar_time': 85500, 'equity': 110000},
            {'bar_time': 86400, 'equity': 121000}]}, 100000)
        self.assertEqual(list(returns), ['1970-01-01', '1970-01-02'])
        self.assertAlmostEqual(returns['1970-01-01'], .1)
        self.assertAlmostEqual(returns['1970-01-02'], .1)

    def test_type_substitutions_and_overflow_rejected(self):
        changed = copy.deepcopy(self.report)
        changed['holdout']['evaluated'] = 0
        with self.assertRaises(ValueError):
            self.adapt(report=changed)
        changed = protocol_draft(1)
        changed['schema_version'] = True
        with self.assertRaises(ValueError):
            self.adapt(protocol=changed)
        from batch2_adapter import load
        for raw in (b'{"unused":1e999}', b'[]', b'{"x":1,"x":2}'):
            with self.assertRaises(ValueError):
                load(raw)

    def test_wrong_instrument_rejected(self):
        for key, value in (('symbol', 'OTHER'), ('timeframe', 'H1')):
            data = json.loads(self.raw[0])
            data[key] = value
            raw = [encode(data), *self.raw[1:]]
            report = copy.deepcopy(self.report)
            report['dataset_sha256'] = sha(raw[0])
            with self.assertRaises(ValueError):
                self.adapt(raw=raw, report=report)


if __name__ == '__main__':
    unittest.main()
