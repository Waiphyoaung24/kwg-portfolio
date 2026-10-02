"""Offline boundary and end-to-end checks; no OAuth, network, broker or generated code."""
import copy
import csv
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from batch3_adapter import adapt_synthetic, encode, sha, simulator
from batch3_runner import research_module, run_fixture, provider_fixture_module, preflight, SANDBOX_IMAGE
from gold_experiment import RISK, digest, source_hashes
from test_research_gold import packet_fixture

spec = importlib.util.spec_from_file_location('batch3_rehearsal', Path(__file__).with_name('rehearse-batch3.py'))
rehearse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rehearse)
GOOD = {'response': '{"kind":"ema20_slope_filter","lookback_bars":3,"hypothesis":"Synthetic"}',
        'tool_calls': [], 'usage': {'input_tokens': 100, 'output_tokens': 30, 'total_tokens': 130},
        'delay_seconds': 0}


class Batch3Test(unittest.TestCase):
    def test_docker_rehearsal_checks_complete_auth_audit(self):
        import runpy
        from unittest.mock import Mock
        module=runpy.run_path(str(Path(__file__).with_name('rehearse-auth-isolation.py')))
        base={'sandbox_cleanup_verified':True,'os_sandbox':True,'isolation_probe_passed':True}
        good=[dict(base,status='parsed_synthetic',auth_audit={'refreshes':1,'clears':0,'inference_posts':1}),
              dict(base,status='worker_failed',auth_audit={'refreshes':1,'clears':1,'inference_posts':0})]
        bad=[dict(base,status='parsed_synthetic',auth_audit={'refreshes':0,'clears':0,'inference_posts':1}),
             dict(base,status='worker_failed',auth_audit={'refreshes':0,'clears':0,'inference_posts':0}),
             dict(base,status='worker_failed',auth_audit={'refreshes':1,'clears':0,'inference_posts':1})]
        with tempfile.TemporaryDirectory() as folder:
            for index,response in enumerate(bad):
                invoke=Mock(side_effect=good[:index]+[response])
                with patch.dict(module['rehearse'].__globals__,{'run_fixture':invoke}):
                    result=module['rehearse'](Path(folder)/str(index))
                self.assertFalse(result['passed'])
                self.assertFalse(result['cases'][-1]['passed'])
                self.assertEqual(invoke.call_count,index+1)

    def test_docker_rehearsal_preserves_failure_without_retry(self):
        import runpy
        module=runpy.run_path(str(Path(__file__).with_name('rehearse-auth-isolation.py')))
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)/'attempt'
            response={'status':'parsed_synthetic','sandbox_cleanup_verified':False,
                'os_sandbox':True,'auth_audit':{'inference_posts':1},'isolation_probe_passed':True}
            from unittest.mock import Mock
            invoke=Mock(return_value=response)
            with patch.dict(module['rehearse'].__globals__,{'run_fixture':invoke}):
                result=module['rehearse'](output)
            self.assertFalse(result['passed'])
            self.assertEqual(invoke.call_count,1)
            self.assertFalse(result['real_credential_transport_verified'])
            self.assertFalse(result['billing_ceiling_verified'])
            self.assertTrue((output/'summary.json').is_file())

    def test_preflight_never_treats_docker_as_production_approval(self):
        from subprocess import CompletedProcess, TimeoutExpired
        with patch('batch3_runner.subprocess.run',side_effect=[
                CompletedProcess([],0,b'linux\n',b''),
                CompletedProcess([],0,(SANDBOX_IMAGE+'\n').encode(),b'')]) as called:
            result=preflight()
        self.assertTrue(result['docker_engine_available'])
        self.assertTrue(result['pinned_image_available'])
        self.assertFalse(result['production_isolation_verified'])
        self.assertFalse(result['billing_ceiling_verified'])
        self.assertEqual(result['dispatch_status'],'blocked')
        self.assertEqual(result['model_requests'],0)
        self.assertEqual(called.call_args_list[0].args[0][-3:],['info','--format','{{.OSType}}'])
        self.assertEqual(called.call_args_list[1].args[0][-5:],['image','inspect','--format','{{.Id}}',SANDBOX_IMAGE])
        for failure in (OSError('PRIVATE_CANARY'),TimeoutExpired('PRIVATE_CANARY',10)):
            with patch('batch3_runner.subprocess.run',side_effect=failure):
                result=preflight()
            self.assertFalse(result['docker_engine_available'])
            self.assertNotIn('PRIVATE_CANARY',str(result))

    def test_auth_fixture_through_isolated_worker(self):
        with tempfile.TemporaryDirectory() as folder:
            for index, (expired, refresh, status, expected_posts) in enumerate([
                    (False,'success',200,1),(True,'success',200,1),
                    (True,'permanent',200,0),(True,'timeout',200,0),
                    (True,'stale',200,0),(False,'success',401,1)]):
                output=Path(folder)/str(index)
                result=run_fixture(packet_fixture(),{**GOOD,'http_status':status},output,
                    auth_fixture={'expired':expired,'refresh':refresh})
                success=refresh=='success' and status==200
                self.assertEqual(result['status'],'parsed_synthetic' if success else 'worker_failed')
                self.assertEqual(result['auth_audit']['inference_posts'],expected_posts)
                self.assertEqual(result['auth_audit']['refreshes'],int(expired))
                self.assertEqual(result['model_requests'],0)
                frozen=json.loads((output/'auth-fixture.json').read_bytes())
                self.assertEqual(frozen,{'expired':expired,'refresh':refresh})
                self.assertEqual(json.loads((output/'request.json').read_bytes())['auth_fixture_sha256'],digest(frozen))
                for path in output.glob('*.json'):
                    self.assertNotIn(b'CANARY',path.read_bytes())
                with self.assertRaises(FileExistsError):
                    run_fixture(packet_fixture(),GOOD,output,auth_fixture={'expired':False,'refresh':'success'})
            result=run_fixture(packet_fixture(),GOOD,Path(folder)/'timeout',deadline=.5,
                auth_fixture={'expired':True,'refresh':'delay'})
            self.assertEqual(result['status'],'deadline_exceeded')
            self.assertIsNone(result.get('auth_audit'))
            for bad in ({'expired':1,'refresh':'success'},{'expired':False,'refresh':'real'},
                        {'expired':False,'refresh':'success','token':'forbidden'}):
                with self.assertRaises(ValueError):
                    run_fixture(packet_fixture(),GOOD,Path(folder)/'invalid',auth_fixture=bad)
            self.assertFalse((Path(folder)/'invalid').exists())

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
            candidate = json.loads((first / 'candidate.json').read_bytes())
            self.assertEqual((first / 'comparison.csv').read_bytes(), (second / 'comparison.csv').read_bytes())
            self.assertEqual(result['comparison_csv_sha256'], sha((first / 'comparison.csv').read_bytes()))
            with (first / 'comparison.csv').open(newline='') as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 6)
            for row in rows:
                self.assertEqual(row['evidence_mode'], 'synthetic_fixture')
                self.assertEqual(row['qualification'], 'unqualified')
                self.assertEqual(row['promotion_status'], 'blocked')
                scenario, window = row['scenario'], row['window']
                before = baseline['runs'][scenario]['windows'][window]['summary']['net_pnl_usd']
                after = candidate['runs'][scenario]['windows'][window]['summary']['net_pnl_usd']
                self.assertEqual(float(row['baseline_net_pnl_usd']), before)
                self.assertEqual(float(row['candidate_net_pnl_usd']), after)
                self.assertEqual(float(row['difference_usd']), after - before)
            self.assertGreater(baseline['runs']['lower']['windows']['development']['summary']['trades'], 0)
            self.assertEqual(len(baseline['runs']['lower']['folds']), 3)
            self.assertFalse(baseline['holdout']['evaluated'])


if __name__ == '__main__':
    unittest.main()
