"""Offline boundary and end-to-end checks; no OAuth, network, broker or generated code."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from batch3_adapter import adapt_synthetic, encode, sha, simulator
from batch3_runner import research_module, run_fixture, provider_fixture_module
from gold_experiment import RISK, digest, source_hashes
from test_research_gold import packet_fixture

spec = importlib.util.spec_from_file_location('batch3_rehearsal', Path(__file__).with_name('rehearse-batch3.py'))
rehearse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearse)
GOOD = {'response': '{"kind":"ema20_slope_filter","lookback_bars":3,"hypothesis":"Synthetic"}',
        'tool_calls': [], 'usage': {'input_tokens': 100, 'output_tokens': 30, 'total_tokens': 130},
        'delay_seconds': 0}


class Batch3Test(unittest.TestCase):
    def test_worker_success_usage_and_no_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'attempt'
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic-canary', 'MT5_PASSWORD': 'synthetic-canary'}):
                result = run_fixture(packet_fixture(), GOOD, output)
            self.assertEqual(result['status'], 'parsed_synthetic')
            self.assertEqual(result['usage'], GOOD['usage'])
            self.assertEqual((result['fake_requests'], result['model_requests']), (1, 0))
            self.assertEqual(result['promotion_status'], 'blocked')
            self.assertIsNone(result['cost_usd'])
            request = json.loads((output / 'request.json').read_bytes())
            self.assertEqual(request['max_output_tokens'], 2048)
            self.assertEqual(request['tools'], [])
            with self.assertRaises(FileExistsError):
                run_fixture(packet_fixture(), GOOD, output)

    def test_fail_closed_limits_usage_tools_and_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            for index, fixture in enumerate((
                    {**GOOD, 'tool_calls': [{'name': 'order_send'}]},
                    {**GOOD, 'response': 'x' * 16385},
                    {**GOOD, 'usage': None},
                    {**GOOD, 'usage': {'input_tokens': 100, 'output_tokens': 2049, 'total_tokens': 2149}},
                    {**GOOD, 'response': '{"token":"never persist this"}'})):
                output = Path(folder) / str(index)
                result = run_fixture(packet_fixture(), fixture, output)
                self.assertEqual(result['status'], 'worker_failed')
                self.assertFalse((output / 'proposal.json').exists())
                self.assertFalse((output / 'response.json').exists())
                self.assertNotIn('never persist', (output / 'result.json').read_text())
            for status in (401, 302, 429, 500):
                output = Path(folder) / ('http-' + str(status))
                result = run_fixture(packet_fixture(), {**GOOD, 'http_status': status}, output)
                self.assertEqual(result['status'], 'worker_failed')
                self.assertFalse((output / 'proposal.json').exists())
                with self.assertRaises(FileExistsError):
                    run_fixture(packet_fixture(), GOOD, output)
            output = Path(folder) / 'timeout'
            result = run_fixture(packet_fixture(), {**GOOD, 'delay_seconds': 2}, output, deadline=.1)
            self.assertEqual(result['status'], 'deadline_exceeded')
            self.assertLess(result['elapsed_seconds'], 2)
            with self.assertRaises(FileExistsError):
                run_fixture(packet_fixture(), GOOD, output)
            with self.assertRaises(ValueError):
                run_fixture({**packet_fixture(), 'limitations': ['historical_costs_unverified']}, GOOD,
                            Path(folder) / 'real')
            self.assertFalse((Path(folder) / 'real').exists())

    def test_pinned_provider_source_required(self):
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / 'provider.py'
            changed.write_bytes(b'# unpinned synthetic source')
            with self.assertRaisesRegex(ValueError, 'Pinned provider'):
                provider_fixture_module().prepare_source(changed, Path('unused.patch'))

    def test_adapter_tampering_coverage_and_development_only(self):
        data, windows, costs, clock = rehearse.fixtures()
        baseline = simulator()(data, windows=windows, cost_profile=costs)
        dataset_raw, baseline_raw = encode(data), encode(baseline)
        manifest = {'schema_version': 1, 'mode': 'synthetic-only',
            'dataset_sha256': sha(dataset_raw), 'baseline_sha256': sha(baseline_raw),
            'code_sha256': source_hashes(), 'windows': windows, 'risk': RISK,
            'policy_sha256': research_module().POLICY_SHA256,
            'cost_sha256': digest(costs), 'clock_sha256': digest(clock)}
        packet, audit = adapt_synthetic(dataset_raw, baseline_raw, manifest, costs, clock)
        self.assertEqual(packet['development']['last_bar'], windows['development']['end'])
        self.assertNotIn('validation', packet)
        self.assertNotIn('clock_evidence', packet)
        self.assertEqual(audit['cost_evidence'], costs)
        self.assertEqual(audit['clock_evidence'], clock)
        for key in ('dataset_sha256', 'baseline_sha256', 'cost_sha256', 'clock_sha256', 'policy_sha256'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                adapt_synthetic(dataset_raw, baseline_raw, {**manifest, key: '0' * 64}, costs, clock)
        for kind in ('cost', 'clock', 'report'):
            bad_costs, bad_clock, bad_report = copy.deepcopy(costs), copy.deepcopy(clock), copy.deepcopy(baseline)
            changed = copy.deepcopy(manifest)
            if kind == 'cost':
                bad_costs['commission']['effective_to'] = 1000
                changed['cost_sha256'] = digest(bad_costs)
            elif kind == 'clock':
                bad_clock['effective_to'] = 1000
                changed['clock_sha256'] = digest(bad_clock)
            else:
                bad_report['runs']['lower']['windows']['development']['summary']['net_pnl_usd'] += 1
                changed['baseline_sha256'] = sha(encode(bad_report))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                adapt_synthetic(dataset_raw, encode(bad_report), changed, bad_costs, bad_clock)

    def test_complete_flow_is_repeatable_and_unqualified(self):
        policy = json.loads(Path(__file__).with_name('evaluation-policy.json').read_bytes())
        self.assertEqual(digest(policy), research_module().POLICY_SHA256)
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'first', Path(folder) / 'second'
            result = rehearse.rehearsal(first)
            self.assertEqual(result, rehearse.rehearsal(second))
            self.assertEqual((first / 'comparison.json').read_bytes(), (second / 'comparison.json').read_bytes())
            self.assertEqual(result['promotion_status'], 'blocked')
            self.assertEqual(result['qualification'], 'unqualified')
            self.assertEqual(result['gate_verdict']['decision'], 'inconclusive')
            self.assertIn('evidence_incomplete', result['gate_verdict']['reasons'])
            self.assertEqual(result['risk_sha256'], digest(RISK))
            self.assertTrue(any(window['trades'] != 0 for scenario in result['deltas'].values()
                                for window in scenario.values()))
            baseline = json.loads((first / 'baseline.json').read_bytes())
            self.assertGreater(baseline['runs']['lower']['windows']['development']['summary']['trades'], 0)
            self.assertEqual(len(baseline['runs']['lower']['folds']), 3)
            self.assertFalse(baseline['holdout']['evaluated'])


if __name__ == '__main__':
    unittest.main()
