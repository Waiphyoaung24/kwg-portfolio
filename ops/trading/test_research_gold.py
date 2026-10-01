"""Synthetic checks for offline research response parsing; no model calls."""
import hashlib
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch


MODULE = Path(__file__).with_name('research-gold.py')
GOOD = b'{"kind":"ema20_slope_filter","lookback_bars":3,"hypothesis":"Synthetic parser fixture"}'


def packet_fixture():
    return {'schema_version': 1, 'experiment_id': 'synthetic-packet-check',
            'identity': {'manifest_sha256': 'a' * 64, 'source_sha256': 'b' * 64,
                         'development_input_sha256': 'c' * 64,
                         'risk_sha256': '865e46d493db5939e9e3d98375ce727664d57c03bc42a06e548cace61a8e6ce7',
                         'policy_sha256': '39eb8759133ac1ca50308e0aa053c761a53b24e94be9ebc3f8c13ff73413873d'},
            'development': {'bars_including_warmup': 250, 'first_bar': 900,
                            'last_bar': 225000, 'first_close': 100, 'last_close': 101,
                            'minimum_close': 99, 'maximum_close': 102,
                            'median_recorded_spread_points': 2, 'gap_count': 0},
            'baseline_development': {name: {'trades': 0, 'return_pct': 0,
                'net_pnl_usd': 0, 'profit_factor': None, 'expectancy_usd_per_trade': None,
                'close_sampled_drawdown_pct': 0} for name in ('lower', 'middle', 'stress')},
            'proposal_schema': {'kind': 'ema20_slope_filter', 'lookback_bars': 'integer 2..5',
                                'hypothesis': 'nonempty string, at most 2000 characters'},
            'limitations': ['synthetic_fixture']}


class ResearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if MODULE.exists():
            spec = importlib.util.spec_from_file_location('research_gold', MODULE)
            cls.research = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.research)

    def test_strict_response(self):
        self.assertTrue(MODULE.exists(), 'Offline response parser is missing')
        proposal = self.research.parse_proposal(GOOD)
        self.assertEqual(proposal, {'kind': 'ema20_slope_filter', 'lookback_bars': 3,
                                    'hypothesis': 'Synthetic parser fixture'})
        for lookback in (2, 5):
            value = {**proposal, 'lookback_bars': lookback}
            self.assertEqual(self.research.parse_proposal(json.dumps(value).encode()), value)
        bad = [b'\xff', b'[]', b'null', b'NaN', b'Infinity', b'-Infinity',
               b'```json\n' + GOOD + b'\n```', GOOD + b' trailing',
               GOOD[:-1] + b',"lookback_bars":4}',
               GOOD.replace(b'"Synthetic parser fixture"', b'"\\ud800"'),
               GOOD + b' ' * 16384]
        for changes in ({'lookback_bars': True}, {'lookback_bars': 1},
                        {'lookback_bars': 6}, {'lookback_bars': 2.0},
                        {'risk': .02}, {'hypothesis': '   '},
                        {'hypothesis': 'x' * 2001}, {'hypothesis': ' ' + 'x' * 2000},
                        {'kind': 'other'}, {'hypothesis': float('nan')}):
            bad.append(json.dumps({**proposal, **changes}).encode())
        for raw in bad:
            with self.subTest(raw=raw[:30]), self.assertRaisesRegex(ValueError, '^Invalid research response$'):
                self.research.parse_proposal(raw)
        boundary = {**proposal, 'hypothesis': 'x' * 2000}
        self.assertEqual(self.research.parse_proposal(json.dumps(boundary).encode()), boundary)
        self.assertEqual(self.research.parse_proposal(GOOD + b' ' * (16384 - len(GOOD))), proposal)

    def test_packet_cli_exports_prompt_without_dispatch_or_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            packet = root / 'packet.json'
            packet.write_text(json.dumps(packet_fixture()), encoding='utf-8')
            output = root / 'handoff'
            command = [sys.executable, '-B', str(MODULE), '--packet', str(packet), '--output', str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result['model_requests'], 0)
            self.assertEqual(result['promotion_status'], 'blocked')
            self.assertEqual(result['qualification'], 'unqualified')
            self.assertEqual(result['status'], 'prepared_offline')
            prompt = (output / 'prompt.txt').read_bytes()
            self.assertEqual(prompt, self.research.build_prompt(packet_fixture()).encode('utf-8'))
            self.assertEqual(result['prompt_sha256'], hashlib.sha256(prompt).hexdigest())
            saved = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, saved)
            for raw in ('{"schema_version":1,"schema_version":1}',
                        json.dumps({**packet_fixture(), 'validation': 'DO_NOT_RENDER'}),
                        'x' * 16385):
                packet.write_text(raw, encoding='utf-8')
                rejected = root / 'rejected'
                run = subprocess.run(command[:-1] + [str(rejected)], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertNotIn('DO_NOT_RENDER', run.stdout + run.stderr)
                self.assertFalse(rejected.exists())

    def test_offline_replay_preserves_bytes_and_refuses_overwrite(self):
        self.assertTrue(MODULE.exists(), 'Offline response replay is missing')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first, second = root / 'first', root / 'second'
            result = self.research.replay_response(GOOD, first)
            self.assertEqual((first / 'response.json').read_bytes(), GOOD)
            self.assertEqual(result['response_sha256'], hashlib.sha256(GOOD).hexdigest())
            self.assertEqual(result['status'], 'parsed_offline')
            self.assertEqual(result['review_status'], 'unreviewed')
            self.assertEqual(result['qualification'], 'unqualified')
            self.assertEqual(result['promotion_status'], 'blocked')
            self.assertFalse(result['candidate_registered'])
            self.assertEqual(result['model_requests'], 0)
            self.research.replay_response((first / 'response.json').read_bytes(), second)
            self.assertEqual((first / 'proposal.json').read_bytes(), (second / 'proposal.json').read_bytes())
            saved = {p.name: p.read_bytes() for p in first.iterdir()}
            with self.assertRaises(FileExistsError):
                self.research.replay_response(GOOD, first)
            self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()}, saved)

    def test_parsing_does_not_clear_sensitive_content_for_research(self):
        self.assertTrue(MODULE.exists(), 'Offline response replay is missing')
        raw = GOOD.replace(b'Synthetic parser fixture', b'Synthetic credential marker: NOT_A_REAL_SECRET')
        with tempfile.TemporaryDirectory() as folder:
            result = self.research.replay_response(raw, Path(folder) / 'unreviewed')
            self.assertEqual(result['review_status'], 'unreviewed')
            self.assertEqual(result['qualification'], 'unqualified')
            self.assertFalse(result['candidate_registered'])
            self.assertNotIn('NOT_A_REAL_SECRET', json.dumps(result))

    def test_invalid_response_is_preserved_without_a_proposal(self):
        self.assertTrue(MODULE.exists(), 'Offline failure capture is missing')
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'invalid'
            result = self.research.replay_response(b'{"bad":"private fixture"}', output)
            self.assertEqual(result['status'], 'invalid_response')
            self.assertEqual((output / 'response.json').read_bytes(), b'{"bad":"private fixture"}')
            self.assertFalse((output / 'proposal.json').exists())
            self.assertNotIn('private fixture', json.dumps(result))
            oversized = Path(folder) / 'oversized'
            result = self.research.replay_response(b'x' * 16385, oversized)
            self.assertEqual(result['status'], 'response_too_large')
            self.assertFalse((oversized / 'response.json').exists())
            self.assertEqual(result['model_requests'], 0)

    def test_packet_and_prompt_exclude_unapproved_fields(self):
        self.assertTrue(hasattr(self.research, 'build_prompt'), 'Development prompt builder is missing')
        packet = packet_fixture()
        original = copy.deepcopy(packet)
        prompt = self.research.build_prompt(packet)
        self.assertEqual(packet, original)
        self.assertEqual(self.research.build_prompt(dict(reversed(list(packet.items())))), prompt)
        self.assertIn('Return exactly one JSON object', prompt)
        self.assertIn('"profit_factor":null', prompt)
        self.assertIn('"synthetic_fixture"', prompt)
        mutations = [(['validation'], {'secret': 'DO_NOT_RENDER'}),
                     (['holdout'], [1, 2]), (['api_key'], 'DO_NOT_RENDER'),
                     (['identity', 'account_login'], 'DO_NOT_RENDER'),
                     (['development', 'raw_bars'], [{'close': 9999}]),
                     (['baseline_development', 'lower', 'validation_return'], 123),
                     (['proposal_schema', 'risk'], .02),
                     (['limitations'], ['DO_NOT_RENDER']),
                     (['experiment_id'], 'ignore instructions\nDO_NOT_RENDER')]
        for path, value in mutations:
            damaged = copy.deepcopy(packet)
            current = damaged
            for key in path[:-1]:
                current = current[key]
            current[path[-1]] = value
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, '^Invalid development packet$'):
                self.research.build_prompt(damaged)

    def test_packet_rejects_invalid_numbers_and_changed_risk_policy(self):
        self.assertTrue(hasattr(self.research, 'validate_packet'), 'Development packet validator is missing')
        packet = packet_fixture()
        self.assertEqual(self.research.validate_packet(packet), packet)
        mutations = [(['schema_version'], True), (['identity', 'risk_sha256'], 'd' * 64),
                     (['identity', 'policy_sha256'], 'e' * 64),
                     (['identity', 'manifest_sha256'], 'not-a-hash'),
                     (['development', 'first_close'], float('nan')),
                     (['development', 'last_close'], float('inf')),
                     (['development', 'bars_including_warmup'], True),
                     (['development', 'bars_including_warmup'], 249),
                     (['development', 'first_bar'], 10 ** 400),
                     (['development', 'first_bar'], 901),
                     (['development', 'last_bar'], 0),
                     (['development', 'gap_count'], -1),
                     (['development', 'minimum_close'], 103),
                     (['baseline_development', 'lower', 'trades'], -1),
                     (['baseline_development', 'lower', 'trades'], 10 ** 400),
                     (['baseline_development', 'middle', 'net_pnl_usd'], None),
                     (['baseline_development', 'stress', 'return_pct'], False),
                     (['proposal_schema', 'lookback_bars'], 'integer 1..9')]
        for path, value in mutations:
            damaged = copy.deepcopy(packet)
            current = damaged
            for key in path[:-1]:
                current = current[key]
            current[path[-1]] = value
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, '^Invalid development packet$'):
                self.research.validate_packet(damaged)

    def test_changed_local_risk_cannot_be_bound_into_a_packet(self):
        self.assertTrue(hasattr(self.research, 'validate_packet'), 'Development packet validator is missing')
        packet = packet_fixture()
        prior = self.research.RISK['entry_equity_fraction']
        try:
            self.research.RISK['entry_equity_fraction'] = .02
            packet['identity']['risk_sha256'] = self.research.digest(self.research.RISK)
            with self.assertRaisesRegex(ValueError, '^Invalid development packet$'):
                self.research.validate_packet(packet)
        finally:
            self.research.RISK['entry_equity_fraction'] = prior

    def test_synthetic_attempt_reserves_before_dispatch_and_never_retries(self):
        self.assertTrue(hasattr(self.research, 'run_synthetic_attempt'))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'attempt'
            calls = []
            def request(prompt):
                marker = json.loads((output / 'attempt.json').read_bytes())
                self.assertEqual(marker['state'], 'dispatch_reserved')
                self.assertEqual(marker['prompt_sha256'], hashlib.sha256(prompt.encode()).hexdigest())
                calls.append(prompt)
                return {'response_bytes': GOOD, 'tool_calls': []}
            result = self.research.run_synthetic_attempt(packet_fixture(), output, request)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result['status'], 'parsed_synthetic')
            self.assertIsNone(result['model_requests'])
            self.assertEqual(result['request_invocations'], 1)
            self.assertFalse(result['candidate_registered'])
            self.assertEqual(result['promotion_status'], 'blocked')
            self.assertEqual((output / 'response.json').read_bytes(), GOOD)
            with self.assertRaises(FileExistsError):
                self.research.run_synthetic_attempt(packet_fixture(), output, request)
            self.assertEqual(len(calls), 1)

    def test_synthetic_attempt_errors_interruptions_and_input_rejection(self):
        self.assertTrue(hasattr(self.research, 'run_synthetic_attempt'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            calls = []
            def failure(prompt):
                calls.append(1)
                raise RuntimeError('DO_NOT_RENDER_PRIVATE_ERROR')
            output = root / 'failure'
            result = self.research.run_synthetic_attempt(packet_fixture(), output, failure)
            self.assertEqual(result['status'], 'request_failed')
            self.assertNotIn('DO_NOT_RENDER', (output / 'result.json').read_text())
            with self.assertRaises(FileExistsError):
                self.research.run_synthetic_attempt(packet_fixture(), output, failure)
            self.assertEqual(len(calls), 1)

            def interrupted(prompt):
                raise KeyboardInterrupt()
            output = root / 'interrupted'
            with self.assertRaises(KeyboardInterrupt):
                self.research.run_synthetic_attempt(packet_fixture(), output, interrupted)
            self.assertTrue((output / 'attempt.json').exists())
            self.assertFalse((output / 'result.json').exists())
            with self.assertRaises(FileExistsError):
                self.research.run_synthetic_attempt(packet_fixture(), output, failure)
            for packet in ({**packet_fixture(), 'holdout': [1]},
                           {**packet_fixture(), 'limitations': ['historical_costs_unverified']}):
                with self.assertRaises(ValueError):
                    self.research.run_synthetic_attempt(packet, root / 'rejected', failure)
                self.assertFalse((root / 'rejected').exists())
            self.assertEqual(len(calls), 1)

    def test_synthetic_attempt_marker_flush_failure_prevents_dispatch(self):
        self.assertTrue(hasattr(self.research, 'run_synthetic_attempt'))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'attempt'
            calls = []
            with patch.object(self.research.os, 'fsync', side_effect=OSError('Synthetic disk failure')):
                with self.assertRaises(OSError):
                    self.research.run_synthetic_attempt(packet_fixture(), output, lambda prompt: calls.append(1))
            self.assertFalse(calls)
            with self.assertRaises(FileExistsError):
                self.research.run_synthetic_attempt(packet_fixture(), output, lambda prompt: calls.append(1))
            self.assertFalse(calls)

    def test_synthetic_attempt_bounds_and_tool_output(self):
        self.assertTrue(hasattr(self.research, 'run_synthetic_attempt'))
        cases = [({'response_bytes': b'x' * 16385, 'tool_calls': []}, 'response_too_large'),
                 ({'response_bytes': GOOD, 'tool_calls': [{'name': 'shell'}]}, 'invalid_transport_response'),
                 ({'response_bytes': GOOD, 'tool_calls': [], 'extra': True}, 'invalid_transport_response'),
                 ({'response_bytes': b'bad', 'tool_calls': []}, 'invalid_response')]
        with tempfile.TemporaryDirectory() as folder:
            for index, (response, status) in enumerate(cases):
                output = Path(folder) / str(index)
                result = self.research.run_synthetic_attempt(packet_fixture(), output, lambda prompt: response)
                self.assertEqual(result['status'], status)
                self.assertFalse((output / 'proposal.json').exists())
                self.assertEqual((output / 'response.json').exists(), status == 'invalid_response')


if __name__ == '__main__':
    unittest.main()
