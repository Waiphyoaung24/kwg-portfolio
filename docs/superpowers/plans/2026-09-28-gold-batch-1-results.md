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

The owner ran the existing one-shot verifier on the VPS at
2026-09-28 11:31:48 UTC. NTP reported synchronized. MT5 reported a gold tick
with raw timestamp 1790605908.096 against host epoch 1790595108.272, an age
of -10799.824 seconds. The latest raw M15 bar was 1790604900, also about
three hours ahead of the host's completed-bar schedule. The pinned demo
terminal was connected and 250 bars were fetched, but the future-time guard
correctly blocked readiness. VT Markets documents GMT+3 server display time
during daylight saving; MetaQuotes documents Python data as UTC. That
discrepancy needs independent verification before any translation of raw
timestamps. No offset is applied or assumed by the running code.
Sources: [VT Markets server time](https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time);
[MetaQuotes Python tick/bar UTC note](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py).

At 2026-09-28 12:06:19 UTC, the owner ran Windows Python under Wine in the
same container. `time.time()`, aware UTC and local time all agreed at
12:06:19+00:00. This rules out a mis-set Wine/Python wall clock as the
three-hour lead. Host files at that time were still old:
`verify-demo.py` SHA-256 `4555b34a...`, `mt5_data.py` `83a38b85...`,
and `gold_qualification.py` was absent. Pinned diagnostic deployment and
raw-time qualification remained unverified at that point.

Next: deploy the exact committed verifier/helpers to the VPS without
recreating MT5, confirm demo identity and Algo Trading off, run one finite
collection in an open gold session, and privately retain its JSON and hashes.
Record actual fee provenance separately. No order path is enabled.
