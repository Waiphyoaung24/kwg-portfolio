import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import gold_experiment as exp

from gold_experiment import (SCENARIOS, compare_reports, digest, entry_allowed,
                             SOURCES, experiment_identity, prepare_experiment, research_input, source_hashes,
                             validate_candidate)
CODES = {name: 'b' * 64 for name in SOURCES}


def report_metadata(manifest):
    return {'identity': experiment_identity(manifest),
            'dataset_sha256': manifest['dataset_sha256'],
            'code_sha256': manifest['code_sha256'],
            'windows_sha256': digest(manifest['windows']),
            'cost_profile_sha256': None, 'cost_profile_status': 'hypothetical',
            'qualification': 'unqualified', 'mode': 'hypothetical-trade-simulation',
            'holdout': {'start_index': 8000, 'bars': 2000, 'evaluated': False}}

spec = importlib.util.spec_from_file_location('compare_gold', Path(__file__).with_name('compare-gold.py'))
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def fixture():
    return {'schema_version': 1, 'symbol': 'XAUUSD-VIP', 'timeframe': 'M15',
            'source': {'start_pos': 1}, 'captured_at': 10002 * 900,
            'current_contract_specification': {'point': .01},
            'bars': [{'time': (i + 1) * 900, 'open': 100, 'high': 101,
                      'low': 99, 'close': 100, 'spread': 2} for i in range(10000)]}


class ExperimentTest(unittest.TestCase):
    def test_cli_hash_exclusive_output_and_freeze(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'dataset.json'
            path.write_text(json.dumps(fixture()))
            raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                cli.checked_dataset(path, '0' * 64)
            data = cli.checked_dataset(path, raw_hash)
            prepared = prepare_experiment(data, raw_hash, source_hashes())
            frozen = cli.finalize(prepared, data, raw_hash)
            self.assertEqual(frozen['status'], 'frozen')
            self.assertEqual(frozen['windows'], prepared['windows'])
            with self.assertRaises(ValueError):
                cli.finalize({**prepared, 'dataset_sha256': '0' * 64}, data, raw_hash)
            output = Path(folder) / 'frozen.json'
            first_hash = cli.write_once(output, frozen)
            self.assertEqual(first_hash, hashlib.sha256(output.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                cli.write_once(output, frozen)

    def test_preparation_freezes_windows_and_rejects_corruption(self):
        data = fixture()
        manifest = prepare_experiment(data, 'a' * 64, CODES)
        self.assertEqual(manifest['windows']['development'],
                         {'start': 250 * 900, 'end': 6000 * 900})
        self.assertEqual(manifest['windows']['validation'],
                         {'start': 6001 * 900, 'end': 8000 * 900})
        self.assertEqual(manifest['reserved_start_index'], 8000)
        self.assertEqual(manifest['timestamp_basis'], 'raw_broker_epoch_unqualified')
        self.assertEqual(manifest['scenarios'], SCENARIOS)
        self.assertEqual(manifest, prepare_experiment(data, 'a' * 64, CODES))
        with self.assertRaises(ValueError):
            prepare_experiment(data, 'a' * 64, {'evaluator': 'b' * 64})
        ahead = {**data, 'captured_at': data['bars'][-1]['time'] - 10800}
        self.assertEqual(prepare_experiment(ahead, 'a' * 64, CODES)['windows'],
                         manifest['windows'])
        for mutation in ('duplicate', 'unordered', 'nan', 'bad_ohlc', 'bad_spread', 'short'):
            damaged = copy.deepcopy(data)
            if mutation == 'duplicate': damaged['bars'][8000]['time'] = damaged['bars'][7999]['time']
            if mutation == 'unordered': damaged['bars'][8000]['time'] = damaged['bars'][7999]['time'] - 900
            if mutation == 'nan': damaged['bars'][8000]['close'] = float('nan')
            if mutation == 'bad_ohlc': damaged['bars'][8000]['high'] = 98
            if mutation == 'bad_spread': damaged['bars'][8000]['spread'] = -1
            if mutation == 'short': damaged['bars'].pop()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                prepare_experiment(damaged, 'a' * 64, CODES)
        for key, value in [('symbol', 'BTCUSD'), ('timeframe', 'M5'), ('schema_version', 2)]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                prepare_experiment({**data, key: value}, 'a' * 64, CODES)
        with self.assertRaises(ValueError):
            prepare_experiment({**data, 'source': {'start_pos': 0}}, 'a' * 64, CODES)

    def test_candidate_shape_is_bounded(self):
        good = {'kind': 'ema20_slope_filter', 'lookback_bars': 3, 'hypothesis': 'Slope reduces noisy entries'}
        self.assertEqual(validate_candidate(good), good)
        for bad in ({**good, 'lookback_bars': True}, {**good, 'lookback_bars': 6},
                    {**good, 'risk': .02}, {**good, 'hypothesis': ''}):
            with self.assertRaises(ValueError):
                validate_candidate(bad)

    def test_registration_precedes_candidate_simulation(self):
        self.assertTrue(hasattr(exp, 'register_candidate'))
        manifest = prepare_experiment(fixture(), 'a' * 64, CODES)
        proposal = {'kind': 'ema20_slope_filter', 'lookback_bars': 3, 'hypothesis': 'Test slope'}
        with self.assertRaises(ValueError):
            exp.register_candidate(manifest, proposal, '2026-09-28T12:00:00+00:00')
        manifest['status'] = 'frozen'
        registration = exp.register_candidate(manifest, proposal, '2026-09-28T12:00:00+00:00')
        self.assertEqual(exp.validate_registration(registration, manifest, proposal), registration)
        with self.assertRaises(ValueError):
            exp.validate_registration({**registration, 'proposal_sha256': '0' * 64}, manifest, proposal)

    def test_slope_filter_uses_only_completed_window(self):
        bars = fixture()['bars'][:250]
        self.assertFalse(entry_allowed(bars, 'long', 3))
        bars[-1]['close'] = 101
        self.assertTrue(entry_allowed(bars, 'long', 3))
        self.assertFalse(entry_allowed(bars, 'short', 3))

    def test_research_input_excludes_validation_and_account_data(self):
        data = fixture()
        data['bars'][6000].update(open=9999, high=10000, low=9998, close=9999)
        data['account_login'] = 1344907
        manifest = prepare_experiment(data, 'a' * 64, CODES)
        manifest['status'] = 'frozen'
        summary = {'trades': 100, 'return_pct': 1, 'profit_factor': 1.2,
                   'close_sampled_drawdown_pct': 2, 'net_pnl_usd': 1000,
                   'expectancy_usd_per_trade': 10}
        baseline = {**report_metadata(manifest), 'runs': {
            scenario: {'costs': costs, 'windows': {'development': {
                'first_bar': manifest['windows']['development']['start'],
                'last_bar': manifest['windows']['development']['end'], 'summary': summary}}}
            for scenario, costs in SCENARIOS.items()}}
        result = research_input(data, manifest, baseline)
        encoded = json.dumps(result)
        self.assertNotIn('9999', encoded)
        self.assertNotIn('1344907', encoded)
        self.assertEqual(result['development']['bars_including_warmup'], 6000)
        baseline['dataset_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            research_input(data, manifest, baseline)

    def test_compare_rejects_identity_mismatch_and_never_promotes(self):
        manifest = prepare_experiment(fixture(), 'a' * 64, CODES)
        manifest['status'] = 'frozen'
        summary = {'trades': 100, 'return_pct': 1, 'profit_factor': 1.2,
                   'close_sampled_drawdown_pct': 2, 'net_pnl_usd': 1000,
                   'expectancy_usd_per_trade': 10}
        runs = {scenario: {'costs': manifest['scenarios'][scenario],
                           'windows': {window: {'summary': copy.deepcopy(summary),
                                                'first_bar': manifest['windows'][window]['start'],
                                                'last_bar': manifest['windows'][window]['end']}
                                       for window in ('development', 'validation')}}
                for scenario in manifest['scenarios']}
        baseline = {**report_metadata(manifest), 'runs': runs}
        candidate = copy.deepcopy(baseline)
        proposal = validate_candidate({'kind': 'ema20_slope_filter', 'lookback_bars': 3,
                                       'hypothesis': 'Slope reduces noisy entries'})
        candidate['candidate'] = proposal
        candidate['proposal_sha256'] = digest(proposal)
        result = compare_reports(baseline, candidate, manifest, proposal)
        self.assertEqual(result['promotion_status'], 'blocked')
        self.assertEqual(result['verdict'], 'rejected')
        self.assertEqual(result['deltas']['lower']['validation']['trades'], 0)
        candidate['dataset_sha256'] = '0' * 64
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'invalid')
        candidate['dataset_sha256'] = manifest['dataset_sha256']
        candidate['code_sha256'] = {}
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'invalid')
        candidate['code_sha256'] = manifest['code_sha256']
        candidate['cost_profile_status'] = 'historically-covered'
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'invalid')
        candidate['cost_profile_status'] = 'hypothetical'
        candidate['runs']['lower']['costs']['commission'] = 99
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'invalid')
        candidate['runs']['lower']['costs']['commission'] = SCENARIOS['lower']['commission']
        for scenario in SCENARIOS:
            revised = candidate['runs'][scenario]['windows']['validation']['summary']
            revised['return_pct'] = 1.3 if scenario == 'lower' else 1.1
            revised['profit_factor'] = 1.3
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'],
                         'promising_for_further_research')
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['promotion_status'], 'blocked')
        candidate['runs']['lower']['windows']['validation']['summary']['profit_factor'] = None
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'inconclusive')
        candidate['runs']['lower']['windows']['validation']['summary']['profit_factor'] = '1.2'
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'inconclusive')
        candidate['runs']['lower']['windows']['validation']['summary']['profit_factor'] = 1.2
        candidate['runs']['lower']['windows']['development']['summary']['profit_factor'] = None
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'inconclusive')
        candidate['runs']['lower']['windows']['development']['summary']['profit_factor'] = 1.2
        del candidate['runs']['lower']['windows']['development']['summary']['expectancy_usd_per_trade']
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'inconclusive')
        candidate['runs']['lower']['windows']['development']['summary']['expectancy_usd_per_trade'] = 10
        candidate['runs']['lower']['windows']['validation']['summary']['trades'] = 99
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'inconclusive')
        candidate['runs']['lower']['windows']['validation']['summary']['trades'] = 100
        candidate['identity']['manifest_sha256'] = 'd' * 64
        self.assertEqual(compare_reports(baseline, candidate, manifest, proposal)['verdict'], 'invalid')
