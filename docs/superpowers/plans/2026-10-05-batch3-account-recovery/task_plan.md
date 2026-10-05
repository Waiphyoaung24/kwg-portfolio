# Account verification recovery after Docker failure

Status: owner selected durable recovery; implementation and 15 focused offline
tests complete. Changed-source sealing and native proof are pending manual
owner preparation. No live account/provider request has run. The owner already
authorized work toward fresh account verification and provider $0 checks; real
inference still needs separate concrete approval.

## Evidence and existing constraints

Owner's corrected read-only inspector reports Linux Docker available; the fixed
worker image ID and proxy repository digest both match. All eight exact-owned
containers and both networks from the failed account attempt are absent; both
inventories have zero unexpected prefix matches. This is current absence
evidence, not a rewritten historical cleanup receipt.

Source remains a6eecea6c3f0fb19bd68ff9a436a47947ce81538. Account seal remains
91322fb34a145c10b04d357694bca6a75bca09ecfc7fd2c38145be2a88bfb56f.
Its existing acceptance is failed and consumed, with saved cleanup false.
No credential snapshots were opened; marker presence is not proof that every
possible provider operation was absent. Model requests remain zero.

Private .batch3-vibe reads remain denied to the agent. Preparation/live checks
that need those files must run manually in the legitimate owner context. No
profile loosening, old attempt deletion, receipt editing or unchanged-code
resealing. Preserve original manifests, receipts and renewal markers.

## Alternatives

| Approach | Benefit | Cost / limitation |
| --- | --- | --- |
| Durable account verification IDs (recommended) | Fresh account evidence can be obtained after infrastructure recovery or evidence expiry; each round is independently logged and consumed. | Account controller, guardian path validation, approval binding and owner workflow need a small coordinated change and new native proof. |
| One-shot Docker preflight | Detects engine/image failure before consuming the existing kind of account acceptance. | Does not solve future post-preflight failure or five-minute evidence expiry; changed sealed code still allows only one acceptance. |
| External CLIProxyAPI account/catalog check | Existing personal proxy is running. | Rejected: it cannot satisfy this gateway's signed account binding, credential isolation and native receipt requirements. |

The owner selected the first approach. Existing direction
remains reuse of the native trusted runner, gpt-5.6-sol, same OAuth app/account,
no paid fallback and one separately approved development proposal.

## Current implementation and owner handoff

gold_account.py requires an explicit canonical verification ID for accept,
reserves a distinct immutable round after read-only Docker/image/predecessor
checks, validates guardian scope and records the round ID. The historical
ownership policy is checked against its own pinned seal before exact resource
absence queries, even when current policy changed. Global renewal markers and
atomic publication semantics are preserved. Docker command failures record a
bounded operation name. gold_proposal.py requires approval to name that exact
round and the SHA of its receipt; there is no latest/successful fallback.

Fifteen focused offline account/crypto/proposal tests pass. They cover actual
controller refusal before reservation/credential access on preflight failure,
round replay, old-record preservation, correct image identity bases, historical
seal/ownership refusal, uncertain/live resource inventory, guardian path scope,
unknown renewal persistence, exact approved receipt, stale/billing/approval
refusal and experiment-wide proposal reservation. Tests use fake credentials
and workspace temporary files; no private runtime or Docker/provider access.
The Windows sandbox temporary folder denied an existing atomic-replacement
test, so the test launcher uses a public workspace temp folder without changing
the runtime publication code.

Next manual owner command:

    & 'C:\Users\wai19\Desktop\kwg-portfolio\.superpowers\sdd\gold-account-recovery-20261005\prepare.ps1'

The hash-reviewed wrapper checks the exact parent/scoped sources/index, reruns
focused tests and read-only owner preflight, commits only the reviewed paths,
creates fresh account/proposal seals and runs their native boundary and forced
termination checks. It compares old failed-record file hashes before/after and
requires the production registry empty. It validates unchanged supported
transport/parser/fixture bytes and the pinned prior 14-case matrix before reusing
that historical matrix; it never invokes supported readiness again. No account
acceptance, renewal, catalog, approval writer or model dispatch occurs.

If preparation fails after commit, preserve partial seals/consumed native checks
and share the redacted output; do not repeat the preparation command. On success,
share its source/seals/intent summary. The next owner verification helper must
be bound to those actual new identities and one explicit fresh round ID. Old
gold-live-verification-20261005/verify.ps1 remains obsolete and must not be run.

## Proposed durable recovery contract

1. Keep old <seal>.accept records immutable. Fresh account-only verification
   rounds receive explicit canonical IDs under the current account seal. The
   same round ID cannot execute twice, including failed or unknown outcomes.
   Neither the wrapper nor controller silently retries with another ID.
2. Before reserving a new round, verify the sealed source, completed native
   boundary/termination evidence, owner ACLs and current Docker Linux engine
   and pinned image identities using an empty dedicated Docker configuration.
   A failed readiness check sends no provider request and reserves no round.
3. Require current exact-owned resource absence for the known failed predecessor
   before live recovery. Validate its original policy/ownership and source
   identity; a changed current policy cannot invalidate or hide old resources.
   Never use global prune, unrelated cleanup, a previous public result alone,
   or saved cleanup false as proof of absence.
4. Reuse the existing isolated workers, endpoint allowlist, JWT signature and
   client/subject/host checks, credential lock, deadlines and independent
   guardian. A new account round is limited to the existing account operations;
   it has no Responses POST, inference tool, broker or trade access.
5. Preserve the global renewal-started/completed ledger keyed by the exact
   saved registration identity. A fresh round ID must never bypass an unknown
   or consumed rotating refresh grant. Publication remains atomic and bound to
   the same account/client/host; no reenrollment or replacement OAuth app.
6. Include the round ID in its receipt and record bounded failure phase/operation
   categories, never raw token inputs, provider bodies or Docker stderr.
   Cleanup success and current signed catalog acceptance are still mandatory.
7. Extend the concrete proposal approval and owner verification audit to bind
   an exact account seal, verification round ID and receipt SHA. Proposal
   prerequisites load that exact receipt; never select a directory called
   latest or silently fall back to an older successful receipt.
8. Keep the five-minute account, provider-control and coding-denial checks and
   separate thirty-minute concrete proposal approval. Preserve experiment-wide
   production reservation, one POST, zero retry/fallback and unknown-outcome
   consumption. More account checks never authorize more proposals.

## Implementation and verification sequence

1. Confirm the chosen contract, then add focused synthetic regressions in the
   existing account/proposal tests before changing runtime code. Use fake
   credentials and temporary public test folders only.
2. Update gold_account.py for explicit verification-round reservation, minimal
   preflight and guardian validation of only canonical owned round paths. Keep
   native boundary and termination attempt naming separate. Update
   gold_proposal.py so the exact approval-bound account receipt is required.
   Do not change supported Responses transport or model selection.
3. Update the owner helper and preparation manifest/schema only where new source
   or receipt binding requires it. Test invalid/traversal IDs, duplicate round,
   missing or uncertain predecessor cleanup, unavailable Docker/wrong image,
   unknown renewal outcome, wrong account/seal/receipt, stale evidence and
   unauthorized proposal. Verify no provider call on preflight refusal and no
   replay even with a new account round ID.
4. Run focused offline account, crypto and proposal tests plus affected sealing
   checks. Preserve the previous 14-case matrix as historical evidence; assess
   whether changed policy/shared files require a new matrix rather than either
   repeating it blindly or claiming the old result proves new code.
5. Prepare one scoped owner commit/sealing/native-check workflow for the actual
   changed source. New seals certify the reviewed functional change, not a
   reset of the old failed acceptance. Use fresh independent native boundary
   and forced-termination tests for both affected controllers. Agent tools do
   not execute private owner helpers.
6. After current native proof and predecessor absence pass, perform one
   explicitly identified fresh account round in owner context. If it fails,
   preserve it and diagnose; do not automatically launch the next round.
7. Recheck the same account's saved provider controls and actual coding opens
   with real observation times. Credit use and automatic reload must be off;
   saved controls, exact binding and freshness are required. Do not infer $0
   enforcement from a local counter, plan subscription or zero balance.
8. Present the exact one-proposal intent for separate owner approval only after
   all verification is complete. No production reservation or model request
   occurs during this recovery milestone.

## Completion criteria

The original failed acceptance and renewal/proposal replay guards are preserved.
The chosen new contract has passing synthetic and actual native proofs. One
fresh signed account verification includes gpt-5.6-sol, cleanup succeeds, and
fresh same-account provider $0 controls and coding isolation pass. A concrete
proposal is ready for separate approval; dispatch is still blocked until that
approval. Batch 2 qualification remains deferred.
