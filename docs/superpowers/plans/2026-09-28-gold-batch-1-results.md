# Batch 1 implementation state

The read-only verifier and bounded collector are implemented locally. The
collector accepts only uninterrupted five-second samples with 0–30-second
gold tick age, 250 valid completed M15 bars, and two consecutive 15-minute
bar transitions. It records sampled spread and allowlisted current contract
properties. It does not write observer state or place orders.

Local checks: 36 Python tests passed on 2026-09-28. A live collection report
has **not** been captured or verified in this implementation run. The current
MT5 server cannot be reached by this workspace's non-interactive SSH key.
The data result is therefore **inconclusive**, not passed. The account-specific
commission and swap schedule is still unknown; cost status is **incomplete**.

Next: deploy the exact committed verifier/helpers to the VPS without
recreating MT5, confirm demo identity and Algo Trading off, run one finite
collection in an open gold session, and privately retain its JSON and hashes.
Record actual fee provenance separately. No order path is enabled.
