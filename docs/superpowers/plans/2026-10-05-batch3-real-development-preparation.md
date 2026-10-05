# Batch 3 — real development preparation checkpoint

Date: 2026-10-05, Asia/Bangkok. Offline adapter implemented and tested.
**Gate C remains incomplete:** the real dataset is not accessible here, no real
packet has been produced and no real inference entry has been enabled or sealed.

## Reuse and implementation

The existing `gold_experiment.prepare_experiment`, `research_input`, simulator
and `research-gold.py` packet/prompt validator already cover this experiment.
`batch3_adapter.adapt_real` adds the small bridge to the existing Batch 3 packet
schema; the synthetic adapter and legacy model/transport behavior stay intact.
No dependencies, provider framework or trading authority were added.

- Require the exact retained dataset byte checksum
  `ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`.
  There is no CLI hash override or permission to substitute another export.
- Require a frozen manifest matching the current evaluator sources, fixed
  chronological windows, risk and hypothetical scenarios. Check the evaluation
  policy against the existing pinned policy hash.
- Recompute the baseline from the verified data and compare the entire report,
  including metadata and reserved-data status. Recheck evaluator source hashes
  after computation. Rehashing an altered report cannot authenticate it.
- Reuse the development-only summary builder: first 6,000 bars including warmup;
  no validation or reserved price/performance records, account details or raw bars
  enter the model prompt. Prior inspection is still disclosed through limitations.
- Retain `validation_previously_inspected`, `reserved_bars_signal_replayed`,
  `historical_costs_unverified`, `broker_timestamps_unqualified` and
  `slippage_assumed`. The audit remains unqualified, provenance-unverified and
  dispatch/promotion-blocked, with zero model requests.
- Bound each input to 32 MiB and use the existing strict JSON parser. Refuse
  duplicate keys, nonfinite values, invalid identities and an existing output.
  Require an existing owner/SYSTEM-only protected output parent, then verify
  every written file's private ACL. Preserve partial outputs on failure.

`batch3_adapter.py` now has an offline CLI taking `--dataset`, `--baseline`,
`--manifest` and `--output`. It saves `packet.json`, `audit.json` and the existing
prompt preparation artifacts. It neither loads tokens nor makes HTTP requests.

## Actual data access blocker

The recorded source is the frozen VPS export:
`/opt/kwg-gold-research/datasets/gold-history-20260928.json`.
Its provenance and prior inspection are documented in the
[original experiment results](2026-09-28-gold-first-experiment-results.md).

A read-only SSH checksum check using batch mode, strict existing host-key
verification and the available key returned `Permission denied (publickey)`.
There was no successful remote read or VPS state change. A filename search of
the local Desktop and Downloads, including ignored project files but excluding
browser profiles/dependency trees, found no `gold-history*.json` copy.
This is not proof that no copy exists elsewhere.

The owner has been asked for an existing local file path or working SSH alias.
Do not request passwords/keys, change SSH settings, re-export data or substitute
synthetic input to work around the missing bytes. No real packet, new real
manifest/baseline hash or final real-attempt identity can be claimed yet.

## Verification and preserved operational evidence

Six new credential-free tests exercise development-only prompt content,
fixed-hash refusal, manifest/policy drift, forged metrics/candidates/reserved
evaluation, malformed inputs and exclusive private-output behavior. Their
success fixture deliberately overrides the dataset hash **inside the test
process only**; it supplies no real-data acceptance evidence.

The native synthetic CLI check passed owner/SYSTEM file ACL verification,
existing-output refusal and unchanged output hashes. Production registry stayed
empty. Receipt:
`.batch3-vibe/gold-development/native-fixture-20261005-02/receipt.json`, SHA256
`25ff962ab6630f4aa74bb16d56bcf24ecc1e7afd366dfae7852cdd127d147ee3`.
Its explicit synthetic mode and test-only hash override prevent interpreting
these artifacts as a real packet. The first failed native attempt directory,
`.batch3-vibe/gold-development/native-fixture-20261005`, is preserved:
it detected that a newly created child directory inherited private permissions
while the existing directory checker required protected inheritance. The CLI
now verifies files beneath the protected parent without weakening that checker.

The first full-suite run encountered four sandbox permission errors in existing
temporary-file replacement and loopback tests. Owner-context regression passed
191 tests in 53.546 seconds after the final CLI correction. Registration/crypto
dependency tests and Docker rehearsals were not
rerun for this offline adapter change; their October 3 evidence is historical.

An open-only check today could open the harmless canary and gold registration;
no credential contents were read by that probe. Listing the private development
directory was also allowed. This still does not prove restricted credential
denial on the actual future execution path; retain the
[spending checkpoint's isolation limitation](2026-10-05-batch3-zero-spend-results.md).

Context7's [HTTPX environment documentation](https://github.com/encode/httpx/blob/master/docs/environment_variables.md)
confirms what `trust_env=False` controls. It does not establish OS network
isolation. The existing Docker/proxy boundary must still be verified for the
final real inference path; changing HTTP client options cannot replace it.

## Resume after access is supplied

1. Verify the existing export's exact checksum before private copying or replay.
   Use `.batch3-vibe/gold-development`, initialized with verified owner/SYSTEM
   permissions; do not reuse synthetic or failed preparation paths.
2. Use the existing `compare-gold.py prepare` and `finalize` commands to freeze
   a current-source manifest. Run `simulate-gold.py` twice with that frozen
   manifest, verify byte-identical baseline reports, then run the adapter:

   ```powershell
   python -I -S -B -c "import sys,runpy;sys.path.insert(0,sys.argv[1]);runpy.run_path(sys.argv[1]+'/batch3_adapter.py',run_name='__main__')" C:/Users/wai19/Desktop/kwg-portfolio/ops/trading --dataset <verified-private-file> --baseline <current-baseline> --manifest <current-frozen-manifest> --output <new-path-under-private-development-root>
   ```

3. Review and freeze the packet/prompt and minimum real controller changes.
   Current account and supported-fake snapshots remain historical seals;
   this adapter addition does not create a sealed production inference path.
   Reuse the account controller's pinned runtime, fixed proxy, inspection,
   independent cleanup and private registry mechanisms where possible. Real
   inference needs a distinct fixed worker and credential-free parser, not removal
   of fake guards or relabeling a fake seal.
4. Verify actual restricted credential access, network bypass denials and forced
   termination cleanup using fake credentials before any real-token transfer.
   Bind final source, packet, baseline, model `gpt-6-astra`, medium reasoning,
   schema and limits into a concrete single attempt for owner authorization.
5. After that authorization, immediately recheck saved provider $0 controls and
   token freshness. Use only reviewed same-account renewal if needed. Reserve
   one durable attempt; no retry, fallback, tools, orders or automatic promotion.

No real model request, renewal, credit change, trade, deployment or push ran.
Batch 2 qualification remains deferred. This checkpoint supplies preparation
code and evidence, not permission to dispatch or qualifying-data credit.
