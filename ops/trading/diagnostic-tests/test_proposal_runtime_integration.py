"""Compatibility tests for the pinned patch; all seals and approvals are fake."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import gold_account as account
import gold_proposal as proposal
import supported_gateway as gateway
from test_proposal_diagnostics import fake_http


def seal(folder):
    entries = [{'path': p.relative_to(folder).as_posix(), 'sha256': proposal.sha(p.read_bytes())}
               for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'manifest.json']
    raw = json.dumps(entries, sort_keys=True).encode()
    (folder/'manifest.json').write_bytes(raw)
    return proposal.sha(raw)


class RuntimeIntegrationTest(unittest.TestCase):
    def test_changed_source_requires_new_manifest_and_extra_files_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'code').mkdir()
            transport = root/'code/supported_oauth_transport.py'
            transport.write_bytes(b'FAKE_OLD_SOURCE')
            old = seal(root); proposal.verify_seal(root, old)
            transport.write_bytes(b'FAKE_PATCHED_SOURCE')
            with self.assertRaisesRegex(ValueError, 'Sealed file identity mismatch'):
                proposal.verify_seal(root, old)
            new = seal(root)
            self.assertNotEqual(old, new)
            with self.assertRaisesRegex(ValueError, 'Seal manifest identity mismatch'):
                proposal.verify_seal(root, old)
            proposal.verify_seal(root, new)
            (root/'unlisted-review.txt').write_bytes(b'FAKE_REVIEW')
            with self.assertRaisesRegex(ValueError, 'Unexpected sealed files'):
                proposal.verify_seal(root, new)

    def test_shared_account_transport_must_match_and_receipt_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sealed = root/'sealed-proposal-fixture'; account_sealed = root/'sealed-account-fixture'
            for folder in (sealed, account_sealed): (folder/'code').mkdir(parents=True)
            for name in proposal.ACCOUNT_FILES:
                raw = Path(name).read_bytes()
                (sealed/'code'/name).write_bytes(raw)
                (account_sealed/'code'/name).write_bytes(raw)
            (account_sealed/'readiness.json').write_text(json.dumps({'policy': account.POLICY}))
            receipt = dict(verification_id='d'*32)
            approval = dict(mode='one_real_development_proposal', seal_sha256='a'*64,
                intent_sha256='b'*64, approved_at=1000, expires_at=1300,
                one_proposal_authorized=True, additional_spend_usd=0,
                account_verification_id='d'*32, request_review_sha256=proposal.sha(proposal.request_review().encode()))
            seen = []
            def read(path):
                seen.append(path)
                if path.name.endswith('.approval.json'): return json.dumps(approval).encode()
                if path.name.endswith('.coding-denial.json'):
                    return json.dumps(dict(seal_sha256='a'*64, actual_coding_token=True, checked_at=1000,
                        registration_open_denied=True, canary_open_denied=True, credential_contents_read=False)).encode()
                if path.parent.parent == root/'account-readiness': return json.dumps(receipt).encode()
                return json.dumps(dict(passed=True, cleanup_verified=True, seal_sha256='a'*64)).encode()
            with patch.object(proposal, 'read_private', side_effect=read), \
                    patch.object(proposal, 'billing_gate'), patch.object(proposal.time, 'time', return_value=1100), \
                    patch.object(proposal.subprocess, 'run') as command:
                shared = account_sealed/'code/supported_oauth_transport.py'
                patched = shared.read_bytes()
                shared.write_bytes(b'FAKE_OLD_TRANSPORT')
                for matched in (False, True):
                    if matched: shared.write_bytes(patched)
                    approval['account_seal_sha256'] = seal(account_sealed)
                    receipt['seal_sha256'] = approval['account_seal_sha256']
                    approval['account_receipt_sha256'] = proposal.sha(json.dumps(receipt).encode())
                    seen.clear()
                    if not matched:
                        with self.assertRaisesRegex(ValueError, 'Shared account source differs'):
                            proposal.dispatch_prerequisites(root, sealed, 'a'*64, {}, 'b'*64)
                        self.assertFalse(any(p.parent.parent == root/'account-readiness' for p in seen))
                    else:
                        self.assertEqual(proposal.dispatch_prerequisites(root, sealed, 'a'*64, {}, 'b'*64),
                                         (approval['account_seal_sha256'], receipt))
                        self.assertEqual(seen[-1], root/'account-readiness'/
                            (approval['account_seal_sha256']+'.accept-'+'d'*32)/'receipt.json')
                        receipt['verification_id'] = 'e'*32
                        with self.assertRaisesRegex(ValueError, 'Exact approved account verification receipt required'):
                            proposal.dispatch_prerequisites(root, sealed, 'a'*64, {}, 'b'*64)
                command.assert_not_called()

    def test_old_or_mismatched_review_stops_before_followup_private_io(self):
        value = dict(mode='one_real_development_proposal', seal_sha256='a'*64, intent_sha256='b'*64,
            approved_at=1000, expires_at=1300, one_proposal_authorized=True, additional_spend_usd=0,
            account_seal_sha256='c'*64, account_verification_id='d'*32, account_receipt_sha256='e'*64)
        for update in ({}, {'request_review_sha256': 'f'*64}):
            with self.subTest(update=update), patch.object(proposal.time, 'time', return_value=1100), \
                    patch.object(proposal, 'read_private', return_value=json.dumps({**value, **update}).encode()) as read, \
                    patch.object(proposal, 'verify_seal') as verify, \
                    patch.object(proposal, 'reserve_production') as reserve, \
                    patch.object(proposal.subprocess, 'run') as command:
                with self.assertRaisesRegex(ValueError, 'Concrete fresh owner authorization required'):
                    proposal.dispatch_prerequisites(Path('FAKE_ROOT'), Path('FAKE_ROOT/sealed-proposal-fixture'),
                                                    'a'*64, {}, 'b'*64)
                self.assertEqual(read.call_count, 1)
                verify.assert_not_called(); reserve.assert_not_called(); command.assert_not_called()

    def test_success_worker_reply_still_reaches_credential_free_parser(self):
        http, calls = fake_http()
        from supported_oauth_transport import invoke_fake
        payload = {'operation': 'proposal', 'value': {'prompt': 'FAKE_PROMPT', 'access_token': 'FAKE_CANARY_ACCESS'}}
        output = io.BytesIO()
        with patch.object(proposal, 'watchdog'), patch.object(proposal.os, 'environ', {}), \
                patch.object(proposal.importlib.metadata, 'version', side_effect=lambda name: proposal.POLICY[name]), \
                patch.object(proposal, 'invoke_isolated', side_effect=lambda prompt, token: invoke_fake(prompt, token, http, None)), \
                patch.object(proposal.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps(payload).encode()))), \
                patch.object(proposal.sys, 'stdout', SimpleNamespace(buffer=output)):
            proposal.worker()
        result = proposal.decode_worker_response(0, output.getvalue())
        self.assertEqual(len(calls), 1)
        self.assertNotIn('FAKE_CANARY', json.dumps(result))
        parsed = io.StringIO()
        with patch.object(gateway, 'watchdog'), patch.object(gateway.os, 'environ', {}), \
                patch.object(gateway.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(json.dumps({'text': result['text']}).encode()))), \
                patch.object(gateway.sys, 'stdout', parsed):
            gateway.parse_worker()
        self.assertEqual(set(json.loads(parsed.getvalue())), {'kind', 'lookback_bars', 'hypothesis'})
        self.assertEqual(result['promotion_status'], 'blocked')

    def test_runtime_policies_and_file_closures_remain_unchanged(self):
        self.assertEqual(proposal.sha(proposal.request_review().encode()),
            '1358b7a8531287bb196d0ccccf44d31fad68040be924e0d1da4577178bc808c3')
        before = json.loads(Path('policy-before.json').read_text())
        self.assertEqual(before, dict(proposal=proposal.POLICY, account=account.POLICY, gateway=gateway.POLICY))
        self.assertIn('supported_oauth_transport.py', account.FILES)
        self.assertEqual(proposal.FILES, ('gold_proposal.py', *account.FILES))
        self.assertTrue(set(gateway.CODE_FILES) <= set(gateway.PARSER_FILES))
        self.assertFalse(proposal.POLICY['tools']); self.assertFalse(proposal.POLICY['trade_authority'])
        self.assertEqual(proposal.POLICY['production_dispatch'], 'blocked')
        self.assertEqual(account.POLICY['inference_dispatch'], 'blocked')


if __name__ == '__main__': unittest.main()
