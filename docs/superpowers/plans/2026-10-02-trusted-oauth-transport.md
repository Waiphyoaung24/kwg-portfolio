# Dedicated trusted OAuth transport, disabled dispatch

Owner requested implementation/account binding with billing enforcement still
untested. Reuse pinned provider conversion/stream guards; do not attach auth
to the proposal worker or normal learning Agent. No real inference authorized.

1. Read-only owner-process binding check: fixed Vibe workspace store, bounded
   strict parsing, stored account matches JWT account claim, fingerprint only.
   Publish freshness and local consistency separately from signature/server
   authentication, which are not verified. No refresh or token-store writes.
2. Extract shared pinned provider definitions loader from existing fake harness.
   Dedicated trusted core supplies bound headers once, fixed endpoint/model,
   no tools/retries/proxy redirects, validates model/completion/usage/proposal.
   Public dispatch remains hard-disabled before any credential or HTTP access.
3. Fake transport tests: account mismatch/expiry/secret rejection, single POST,
   401/no resend, tool/usage validation and disabled dispatch; fresh review.
4. Run owner binding check to new private receipt, inspect selected metadata only.
   No token bytes, email or raw account ID in tool output/logs. Preserve receipts.

Actual production parent deadline/credential-process OS containment, current
source sealing and backend billing enforcement must pass before enabling
dispatch. This implementation does not provide a public live invocation route.
