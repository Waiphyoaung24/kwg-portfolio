# Batch 1 implementation state

The read-only verifier and bounded collector are implemented locally. The
collector accepts only uninterrupted five-second samples with 0–30-second
gold tick age, 250 valid completed M15 bars, and two consecutive 15-minute
bar transitions. It records sampled spread and allowlisted current contract
properties. It does not write observer state or place orders.

Local checks: 36 Python tests passed on 2026-09-28. The pinned read-only
diagnostic was deployed through the owner's SSH session. A 60-second private
collection was captured, but it did not qualify UTC freshness. The workspace's
non-interactive SSH key remains unavailable; owner-assisted VPS commands were
used. The data result is **inconclusive**, not passed. The account-specific
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

The owner then copied the pinned diagnostic files into the running
`kwg-mt5-desktop` container without a restart. All five downloaded files
passed SHA-256 checks; the container's `verify-demo.py`,
`mt5_data.py` and `gold_qualification.py` hashes matched the pinned
source. At 12:15:19 UTC, the new one-shot verifier still blocked: raw tick
age -10799.796 seconds, raw latest completed bar exactly 10800 seconds
ahead of the host's expected M15 bar, 250 bars fetched, bid 4164.30, ask
4164.57. The raw bar advanced 45 minutes between the 11:31 and 12:15
checks. Feed progression is observed, but absolute UTC timestamp semantics
and continuous freshness are not qualified.

A 60-second bounded private collection then ran from the deployed verifier
as `gold-raw-qualification-20260928-1215.json` in the MT5 home volume.
Its CLI summary reported `data_status=inconclusive`,
`accepted_sample_count=0`, no qualifying M15 transitions or spread
summary, and `cost_status=incomplete`. The private report was summarized
without copying it or account data into Git: 13 samples, raw tick timestamp
advance 59.78 seconds, apparent UTC age range -10799.896 to -10799.520
seconds, and one raw bar label 1790607600. This proves feed progression
over that minute, not UTC freshness or two bar boundaries.

Next: independently compare MT5 Market Watch server time with synchronized
UTC, establish a verified timestamp basis, then repeat a finite two-boundary
collection. Record account-specific fee provenance separately. No order
path is enabled.

At approximately 12:26 UTC, the private MT5 desktop's Market Watch clock
showed approximately 15:26. This independently corroborated a three-hour
server display offset for this session, though it does not resolve the
MetaQuotes documentation discrepancy or historical timestamp semantics.
The read-only verifier now offers an explicit 10800-second diagnostic offset;
raw tick and bar timestamps remain in its private report, and default
observer behavior is unchanged. Local suite: 37 tests passed. Live one-shot
and two-boundary qualification using this option are pending owner-assisted
deployment. Data status remains **inconclusive**.

The owner then deployed commit `ff70707`'s two changed verifier files into
the existing desktop container after matching SHA-256 checksums, without a
restart. At 12:34:40 UTC the one-shot verifier with the explicit 10800-second
offset reported a 0.204-second gold quote age, 250 completed M15 bars, and
latest adjusted bar time 1790597700 equal to the expected completed bar. Its
raw bar time was 1790608500. This is a **single-time readiness pass**, not
the required continuous two-boundary data qualification. The owner deferred
the long collector; cost-source checks are also pending. The observer remains
unchanged.
