"""Credential-free adapter checks; the hash override is test-only synthetic data."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import batch3_adapter as adapter
from batch3_runner import research_module
from gold_experiment import prepare_experiment, source_hashes
from test_gold_experiment import fixture, report_metadata
from test_simulate_gold import SPEC


class RealDevelopmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = fixture()
        data['current_contract_specification'] = SPEC
        data['account_login'] = 'ACCOUNT_SECRET_CANARY'
        data['bars'][6000].update(open=9999, high=10000, low=9998, close=9999)
        data['bars'][8000].update(open=8888, high=8889, low=8887, close=8888)
        cls.dataset = adapter.encode(data)
        cls.dataset_sha = adapter.sha(cls.dataset)
        cls.manifest = {**prepare_experiment(data, cls.dataset_sha, source_hashes()), 'status': 'frozen'}
        cls.baseline = {**adapter.simulator()(data, windows=cls.manifest['windows']),
                        **report_metadata(cls.manifest)}

    def adapt(self, *, dataset=None, baseline=None, manifest=None):
        with patch.object(adapter, 'FROZEN_DATASET_SHA256', self.dataset_sha):
            return adapter.adapt_real(self.dataset if dataset is None else dataset,
                adapter.encode(self.baseline if baseline is None else baseline),
                adapter.encode(self.manifest if manifest is None else manifest))

    def test_development_only_prompt_and_unqualified_audit(self):
        packet, audit = self.adapt()
        prompt = research_module().build_prompt(packet)
        self.assertEqual(packet['development']['bars_including_warmup'], 6000)
        self.assertEqual(packet['development']['last_bar'], 6000 * 900)
        for withheld in ('9999', '8888', 'ACCOUNT_SECRET_CANARY', '"validation"', '"holdout"'):
            self.assertNotIn(withheld, prompt)
        self.assertNotIn('synthetic_fixture', packet['limitations'])
        self.assertIn('reserved_bars_signal_replayed', packet['limitations'])
        self.assertIn('historical_costs_unverified', packet['limitations'])
        self.assertTrue(audit['baseline_reproduced'])
        self.assertFalse(audit['provenance_verified_for_real_data'])
        self.assertEqual((audit['model_requests'], audit['qualification'], audit['dispatch_status']),
                         (0, 'unqualified', 'blocked'))

    def test_fixed_hash_rejects_substitution_before_simulation(self):
        with patch.object(adapter, 'simulator') as simulate:
            with self.assertRaises(ValueError):
                adapter.adapt_real(self.dataset, adapter.encode(self.baseline), adapter.encode(self.manifest))
            with self.assertRaises(ValueError):
                self.adapt(dataset=self.dataset + b' ')
            simulate.assert_not_called()

    def test_manifest_and_policy_drift_refused(self):
        for field, value in (('status', 'prepared'), ('dataset_sha256', '0' * 64),
                             ('timestamp_basis', 'utc_verified'), ('risk', {}), ('extra', True)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.adapt(manifest={**self.manifest, field: value})
        with patch.object(adapter, 'research_module') as research:
            research.return_value.RISK_SHA256 = '0' * 64
            with self.assertRaises(ValueError):
                self.adapt()

    def test_modified_metric_and_reserved_evaluation_refused(self):
        for mutation in ('metric', 'candidate', 'holdout'):
            baseline = copy.deepcopy(self.baseline)
            if mutation == 'metric':
                baseline['runs']['lower']['windows']['development']['summary']['net_pnl_usd'] += 1
            elif mutation == 'candidate':
                baseline['candidate'] = {'kind': 'ema20_slope_filter', 'lookback_bars': 3, 'hypothesis': 'fake'}
            else:
                baseline['holdout']['evaluated'] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.adapt(baseline=baseline)

    def test_duplicate_nonfinite_oversized_and_nonbytes_refused(self):
        with patch.object(adapter, 'FROZEN_DATASET_SHA256', self.dataset_sha):
            for raw in (b'{"status":"frozen","status":"frozen"}', b'{"x":NaN}',
                        b'{"x":1e999}', b'x' * (adapter.MAX_INPUT_BYTES + 1), 'text'):
                with self.subTest(kind=type(raw).__name__), self.assertRaises(ValueError):
                    adapter.adapt_real(self.dataset, adapter.encode(self.baseline), raw)

    def test_cli_preserves_existing_output_and_refuses_unprotected_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, raw in (('dataset', self.dataset), ('baseline', adapter.encode(self.baseline)),
                              ('manifest', adapter.encode(self.manifest))):
                (root/name).write_bytes(raw)
            output = root/'prepared'
            argv = ['adapter', '--dataset', str(root/'dataset'), '--baseline', str(root/'baseline'),
                    '--manifest', str(root/'manifest'), '--output', str(output)]
            with patch('sys.argv', argv), patch('gold_account.private_acl', side_effect=ValueError):
                with self.assertRaises(SystemExit) as refused:
                    adapter.main()
                self.assertEqual(refused.exception.code, 2)
                self.assertFalse(output.exists())
            with patch('sys.argv', argv), patch('gold_account.private_acl'), \
                    patch.object(adapter, 'FROZEN_DATASET_SHA256', self.dataset_sha):
                adapter.main()
                saved = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
                with patch.object(adapter, 'adapt_real') as adapt, self.assertRaises(SystemExit) as replay:
                    adapter.main()
                self.assertEqual(replay.exception.code, 2)
                adapt.assert_not_called()
                self.assertEqual(saved, {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()})
                self.assertEqual(json.loads((output/'audit.json').read_bytes())['model_requests'], 0)


if __name__ == '__main__':
    unittest.main()
