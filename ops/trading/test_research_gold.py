"""Synthetic checks for offline research response parsing; no model calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE = Path(__file__).with_name('research-gold.py')
GOOD = b'{"kind":"ema20_slope_filter","lookback_bars":3,"hypothesis":"Synthetic parser fixture"}'


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


if __name__ == '__main__':
    unittest.main()
