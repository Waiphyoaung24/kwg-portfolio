"""Only synthetic consent, receipts and exclusive temporary fixture writes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gold_proposal as proposal
from batch3_runner import write_once
import proposal_approval_candidate as candidate


class ApprovalCandidateTest(unittest.TestCase):
    def inputs(self):
        receipt = dict(seal_sha256='c'*64, verification_id='d'*32, accepted_at=1050,
            passed=True, cleanup_verified=True, required_model_present=True,
            server_account_verified=True, production_isolation_verified=True, model_requests=0)
        return dict(displayed_review=proposal.request_review().encode('utf-8'), answer='APPROVE',
            approved_at=1000, now=1100, seal_sha='a'*64, intent_sha='b'*64,
            account_sha='c'*64, verification_id='d'*32, receipt_raw=json.dumps(receipt).encode())

    def prepare(self, **updates):
        self.assertTrue(callable(getattr(candidate, 'prepare_approval', None)), 'Approval candidate missing')
        return candidate.prepare_approval(**{**self.inputs(), **updates})

    def test_runtime_review_bytes_hash_and_exact_eleven_fields(self):
        self.assertTrue(callable(getattr(candidate, 'review_bytes', None)), 'Runtime review renderer missing')
        raw = candidate.review_bytes()
        self.assertEqual(raw, proposal.request_review().encode('utf-8'))
        self.assertTrue(raw.endswith(b'\n')); self.assertNotIn(b'\r', raw)
        self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(proposal.sha(raw), '1358b7a8531287bb196d0ccccf44d31fad68040be924e0d1da4577178bc808c3')
        value = self.prepare()
        self.assertEqual(set(value), {'mode', 'seal_sha256', 'intent_sha256', 'approved_at', 'expires_at',
            'one_proposal_authorized', 'additional_spend_usd', 'account_seal_sha256',
            'account_verification_id', 'account_receipt_sha256', 'request_review_sha256'})
        self.assertEqual(value['approved_at'], 1000); self.assertEqual(value['expires_at'], 2800)
        self.assertEqual(value['account_receipt_sha256'], proposal.sha(self.inputs()['receipt_raw']))
        proposal.approval_gate(value, 'a'*64, 'b'*64, 1100)

    def test_absent_consent_does_not_parse_receipt_or_invoke_helpers(self):
        self.assertTrue(callable(getattr(candidate, 'prepare_approval', None)), 'Approval candidate missing')
        with patch.object(candidate, 'strict_json') as parse, patch.object(proposal, 'read_private') as read, \
                patch.object(proposal, 'reserve_production') as reserve, patch.object(proposal.subprocess, 'run') as run:
            for answer in (None, '', 'approve', True, 'APPROVE '):
                with self.assertRaisesRegex(ValueError, 'Explicit human approval'):
                    candidate.prepare_approval(**{**self.inputs(), 'answer': answer, 'receipt_raw': b'invalid'})
            parse.assert_not_called(); read.assert_not_called(); reserve.assert_not_called(); run.assert_not_called()

    def test_changed_review_bom_and_windows_newlines_refuse(self):
        raw = self.inputs()['displayed_review']
        for altered in (raw.replace(b'\n', b'\r\n'), b'\xef\xbb\xbf'+raw, raw.rstrip(),
                        raw.replace(b'"stream": true', b'"stream": false')):
            with self.subTest(altered=altered), self.assertRaises(ValueError): self.prepare(displayed_review=altered)

    def test_freshness_and_exact_receipt_identity_refuse_stale_or_wrong_inputs(self):
        for updates in ({'approved_at': -701}, {'approved_at': 1106}, {'approved_at': True},
                        {'now': float('nan')}, {'seal_sha': 'z'*64}, {'intent_sha': '../bad'},
                        {'account_sha': 'e'*64}, {'verification_id': 'e'*32}):
            with self.subTest(updates=updates), self.assertRaises(ValueError): self.prepare(**updates)
        receipt = json.loads(self.inputs()['receipt_raw'])
        for updates in ({'accepted_at': 799}, {'accepted_at': 1106}, {'accepted_at': True},
                        {'passed': False}, {'cleanup_verified': False}, {'model_requests': 1},
                        {'model_requests': False}, {'required_model_present': False}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                self.prepare(receipt_raw=json.dumps({**receipt, **updates}).encode())

    def test_old_wrong_schema_and_mismatched_bindings_refuse_in_runtime(self):
        value = self.prepare()
        old = {key: val for key, val in value.items() if key != 'request_review_sha256'}
        for bad in (old, {**value, 'request_review_sha256': 'f'*64}, {**value, 'extra': True},
                    {**value, 'seal_sha256': 'f'*64}, {**value, 'intent_sha256': 'f'*64}):
            with self.assertRaises(ValueError): proposal.approval_gate(bad, 'a'*64, 'b'*64, 1100)

    def test_synthetic_exclusive_write_preserves_first_bytes(self):
        value = self.prepare()
        with tempfile.TemporaryDirectory(prefix='kwg-FAKE-approval-') as folder:
            target = Path(folder)/'FAKE-approval-fixture.json'
            digest = write_once(target, value)
            raw = target.read_bytes()
            self.assertEqual(digest, proposal.sha(raw))
            with self.assertRaises(FileExistsError): write_once(target, {**value, 'approved_at': 1100})
            self.assertEqual(target.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
