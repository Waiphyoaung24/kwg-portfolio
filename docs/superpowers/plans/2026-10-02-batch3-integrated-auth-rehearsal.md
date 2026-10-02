# Integrated authentication boundary rehearsal

Goal: exercise fake credentials/refresh and the pinned provider through the
existing bounded worker, without adding a live dispatch route. Reuse the auth
fixture and single-request provider tests. Budget remains USD 0 additional spend;
paid billing fallback enforcement and real OS isolation remain external blockers.

1. Move the existing memory-only fake-auth helper into a reusable stdlib module;
   preserve its original tests. No production storage/SDK imports.
2. Add an explicit optional fake-auth fixture to the synthetic runner. Require
   a strict schema, hash-pin the helper in the attempt, preserve clean child
   environment and use the same deadlines/no-tools/request limits.
3. Test successful fresh/expired fake credentials, failed refresh, HTTP 401,
   delayed refresh and invalid fixture shapes through actual child execution.
   Verify outputs contain no fake credentials; failed attempts cannot be reused.
4. Run focused/full checks and fresh review. Save a private rehearsal receipt.

This is production-path preparation, not production transport verification.
No real OAuth token, inference, broker data, order or promotion.

Implemented: original fake-auth helper extracted and reused by existing tests
and fixed worker. Auth input/helper identities hash-pinned; inputs saved before
execution. Actual-child test first failed on missing optional parameter, then
passed; frozen-input regression first failed, then passed. Original four auth
checks and six worker/rehearsal tests pass. Fresh scoped review clean.

Preserved local rehearsal summary:
`.superpowers/sdd/batch3-integrated-auth-20261002-01/summary.json`.
One refresh/one fake inference success; failed refresh zero inference; HTTP401
one attempt and no refresh; delayed auth parent timeout with unknown counts.
All model requests zero. OS and billing verification remain false, not inferred
from Python isolation flags or fixture success. Docker unavailable; no engine
started and no real credential access added. Archived sealed snapshot unchanged.
