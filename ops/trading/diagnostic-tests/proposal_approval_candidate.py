"""In-memory future coordinator candidate; no launcher, private IO or writer."""
from gold_proposal import BOUND, approval_gate, request_review, sha
from trusted_oauth_transport import strict_json


def review_bytes():
    return request_review().encode('utf-8')


def prepare_approval(*, displayed_review, answer, approved_at, now, seal_sha,
                     intent_sha, account_sha, verification_id, receipt_raw):
    """Prepare data only. Signed identity/billing/native proofs are separate gates."""
    if answer != 'APPROVE':
        raise ValueError('Explicit human approval required')
    if (type(now) is not int or type(approved_at) is not int
            or not now-1800 < approved_at <= now+5):
        raise ValueError('Fresh original human timestamp required')
    if type(displayed_review) is not bytes or displayed_review != review_bytes():
        raise ValueError('Exact runtime review bytes required')
    for digest in (seal_sha, intent_sha, account_sha):
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Exact source and intent hashes required')
    if type(receipt_raw) is not bytes or len(receipt_raw) > BOUND:
        raise ValueError('Bounded receipt bytes required')
    receipt = strict_json(receipt_raw)
    if (not isinstance(receipt, dict) or receipt.get('seal_sha256') != account_sha
            or receipt.get('verification_id') != verification_id
            or type(receipt.get('accepted_at')) is not int or not now-300 <= receipt['accepted_at'] <= now+5
            or type(receipt.get('model_requests')) is not int or receipt['model_requests'] != 0
            or any(receipt.get(key) is not True for key in ('passed', 'cleanup_verified',
                'required_model_present', 'server_account_verified', 'production_isolation_verified'))):
        raise ValueError('Fresh exact account receipt required')
    value = dict(mode='one_real_development_proposal', seal_sha256=seal_sha, intent_sha256=intent_sha,
        approved_at=approved_at, expires_at=approved_at+1800, one_proposal_authorized=True,
        additional_spend_usd=0, account_seal_sha256=account_sha, account_verification_id=verification_id,
        account_receipt_sha256=sha(receipt_raw), request_review_sha256=sha(displayed_review))
    approval_gate(value, seal_sha, intent_sha, now)
    return value
