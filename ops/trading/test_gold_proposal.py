import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import gold_proposal as proposal
import supported_oauth_transport as transport


class ProposalTest(unittest.TestCase):
    def test_concrete_approval_expires_and_cannot_authorize_credit_use(self):
        value=dict(mode='one_real_development_proposal',seal_sha256='a'*64,intent_sha256='b'*64,
            approved_at=1000,expires_at=2000,one_proposal_authorized=True,
            additional_spend_usd=0,account_seal_sha256='c'*64,
            account_verification_id='d'*32,account_receipt_sha256='e'*64,
            request_review_sha256=proposal.sha(proposal.request_review().encode()))
        proposal.approval_gate(value,'a'*64,'b'*64,1100)
        for update in ({'additional_spend_usd':1},{'additional_spend_usd':False},
                {'one_proposal_authorized':1},{'expires_at':1100},{'expires_at':3000},
                {'approved_at':1200},{'approved_at':False},{'seal_sha256':'other'},
                {'intent_sha256':'other'},{'account_seal_sha256':'z'*64},{'extra':True},
                {'account_verification_id':'../bad'},{'account_receipt_sha256':'z'*64}):
            with self.subTest(update=update),self.assertRaises(ValueError):
                proposal.approval_gate({**value,**update},'a'*64,'b'*64,1100)
        with self.assertRaises(ValueError): proposal.approval_gate(value,'a'*64,'b'*64,3001)

    def test_fresh_billing_requires_exact_saved_provider_controls_and_binding(self):
        intent=dict(client_id_sha256='client',subject_sha256='subject')
        value=dict(saved_at=datetime.fromtimestamp(1000,timezone.utc).isoformat(),
            billing_ceiling_verified=True,**intent,observations=dict(app_name='KWG Gold Research',
                gold_app_entries=1,app_plan_usage_allowed=True,manage_usage_followed_from_gold_connection=True,
                apps_credit_use_allowed=False,automatic_reload_enabled=False,save_button_enabled=False))
        proposal.billing_gate(value,intent,1100)
        for field,changed in (('apps_credit_use_allowed',True),('automatic_reload_enabled',True),
                ('save_button_enabled',True),('app_plan_usage_allowed',False),('gold_app_entries',2),
                ('manage_usage_followed_from_gold_connection',False),('app_name','Other')):
            wrong=copy.deepcopy(value);wrong['observations'][field]=changed
            with self.assertRaises(ValueError): proposal.billing_gate(wrong,intent,1100)
        for update in ({'client_id_sha256':'other'},{'subject_sha256':'other'},{'billing_ceiling_verified':False}):
            with self.assertRaises(ValueError): proposal.billing_gate({**value,**update},intent,1100)
        with self.assertRaises(ValueError): proposal.billing_gate(value,intent,1301)

    def test_missing_approval_stops_before_auth_network_or_production_reservation(self):
        root=Path('FAKE_ROOT');sealed=root/'sealed-proposal-fixture'
        with patch.object(proposal,'read_private',side_effect=FileNotFoundError) as read, \
                patch.object(proposal,'verify_seal') as seal,patch.object(proposal,'reserve_production') as reserve, \
                patch.object(proposal.subprocess,'run') as command:
            with self.assertRaises(FileNotFoundError): proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64)
            self.assertEqual(read.call_args.args[0],root/'proposal-readiness'/('a'*64+'.approval.json'))
            self.assertEqual(read.call_count,1);seal.assert_not_called();reserve.assert_not_called();command.assert_not_called()

    def test_account_receipt_binds_exact_signed_accepted_registration_and_model(self):
        record=dict(issuer='https://auth.openai.com',client_id='oaiapp_fixture',subject='fixture',
            ext_agent_host_id='host',access_token='FAKE_CANARY_ACCESS',expires_at=5000,dispatch_status='blocked')
        raw=json.dumps(record).encode()
        intent={key:proposal.sha(record[field].encode()) for field,key in (
            ('client_id','client_id_sha256'),('subject','subject_sha256'),('ext_agent_host_id','host_id_sha256'))}
        receipt=dict(seal_sha256='c'*64,passed=True,cleanup_verified=True,required_model_present=True,
            server_account_verified=True,production_isolation_verified=True,registration_sha256=proposal.sha(raw),
            accepted_at=1000,available_models=[proposal.MODEL],model_requests=0,**intent)
        self.assertEqual(proposal.accepted_account(raw,receipt,intent,'c'*64,1100),'FAKE_CANARY_ACCESS')
        for update in ({'registration_sha256':'other'},{'accepted_at':0},{'accepted_at':True},
                {'available_models':['other']},{'cleanup_verified':False},{'subject_sha256':'other'},
                {'server_account_verified':False},{'seal_sha256':'other'},{'model_requests':1}):
            with self.assertRaises(ValueError): proposal.accepted_account(raw,{**receipt,**update},intent,'c'*64,1100)
        stale=json.dumps({**record,'expires_at':1300}).encode()
        with self.assertRaises(ValueError): proposal.accepted_account(stale,{**receipt,'registration_sha256':proposal.sha(stale)},intent,'c'*64,1100)

    def test_dispatch_uses_only_the_approved_verification_id_and_exact_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sealed=root/'sealed-proposal-fixture';sealed.mkdir()
            account_sealed=root/'sealed-account-fixture';account_sealed.mkdir()
            (sealed/'code').mkdir();(account_sealed/'code').mkdir()
            for name in proposal.ACCOUNT_FILES:
                (sealed/'code'/name).write_bytes(b'fake')
                (account_sealed/'code'/name).write_bytes(b'fake')
            from gold_account import POLICY
            (account_sealed/'readiness.json').write_text(json.dumps(dict(policy=POLICY)))
            now=proposal.time.time()
            receipt=dict(verification_id='d'*32,seal_sha256='c'*64)
            raw=json.dumps(receipt).encode()
            approval=dict(mode='one_real_development_proposal',seal_sha256='a'*64,intent_sha256='b'*64,
                approved_at=int(now),expires_at=int(now)+300,one_proposal_authorized=True,
                additional_spend_usd=0,account_seal_sha256='c'*64,account_verification_id='d'*32,
                account_receipt_sha256=proposal.sha(raw),
                request_review_sha256=proposal.sha(proposal.request_review().encode()))
            seen=[]
            def read(path):
                seen.append(path)
                if path.name.endswith('.approval.json'): return json.dumps(approval).encode()
                if path.name.endswith('.coding-denial.json'):
                    return json.dumps(dict(seal_sha256='a'*64,actual_coding_token=True,checked_at=int(now),
                        registration_open_denied=True,canary_open_denied=True,credential_contents_read=False)).encode()
                if path.parent.parent==root/'account-readiness': return raw
                return json.dumps(dict(passed=True,cleanup_verified=True,model_requests=0,seal_sha256='a'*64)).encode()
            with patch.object(proposal,'read_private',side_effect=read),patch.object(proposal,'verify_seal'), \
                    patch.object(proposal,'billing_gate'),patch.object(proposal.subprocess,'run') as command:
                self.assertEqual(proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64),('c'*64,receipt))
                self.assertEqual(seen[-1],root/'account-readiness'/('c'*64+'.accept-'+'d'*32)/'receipt.json')
                approval['account_receipt_sha256']='e'*64
                with self.assertRaises(ValueError): proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64)
                approval['account_receipt_sha256']=proposal.sha(raw);approval['account_verification_id']='f'*32
                with self.assertRaises(ValueError): proposal.dispatch_prerequisites(root,sealed,'a'*64,{},'b'*64)
                command.assert_not_called()

    def test_experiment_reservation_is_exclusive_across_seals_and_survives_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            attempt=proposal.reserve_production(root,'e'*64,'a'*64,'b'*64)
            self.assertEqual(json.loads((attempt/'started.json').read_bytes())['state'],'outcome_unknown')
            with self.assertRaises(FileExistsError): proposal.reserve_production(root,'e'*64,'c'*64,'d'*64)
            self.assertEqual(len(list(root.iterdir())),1)
            for identity in ('../escape','e'*63,'z'*64):
                with self.assertRaises(ValueError): proposal.reserve_production(root,identity,'a'*64,'b'*64)

    def test_live_entry_refuses_host_and_legacy_public_dispatch_stays_closed(self):
        with self.assertRaises(ValueError): transport.invoke_isolated('prompt','FAKE_CANARY_ACCESS')
        with self.assertRaises(ValueError): transport.dispatch('prompt','FAKE_CANARY_ACCESS')
        self.assertEqual(proposal.POLICY['max_posts'],1)
        self.assertEqual(proposal.POLICY['retries'],0)
        self.assertIn('acl approved dstdomain -n api.openai.com\n',proposal.PROXY)
        self.assertNotIn('auth.openai.com',proposal.PROXY)
        self.assertFalse(proposal.POLICY['tools']);self.assertFalse(proposal.POLICY['trade_authority'])


if __name__=='__main__': unittest.main()
