# Dated broker evidence intake — October 2, 2026 Bangkok

Status: owner executed the read-only capture and the agent read its summary
directly from the Codex terminal. Direct agent SSH still rejects publickey
authentication. No prospective run started.
The old private Windows session-record location was checked; that directory
currently contains no files. Its previous references are not new evidence.

## Owner capture result

Private `broker-intake-S7u11LUf/current-contract.json` parsed with three
samples at October 1 19:58:49–19:58:53 UTC. All three quotes were fresh; the
capture assertions required Algo off, zero gold positions/pending orders and
the expected mode/symbol. A byte hash printed after these assertions.
Cost status remains incomplete; clock status remains current_spot_checks_only.
No dated coverage or qualifying observed days are established by this capture.

Terminal paste omitted the opening subshell delimiter while retaining its
closing `)`. The resulting shell syntax error occurred after the Python
summary; `set -e` had been applied to the interactive shell and SSH closed.
Do not rerun or overwrite this capture. Reconnect and verify the saved byte
hash read-only first. The earlier interrupted attempt must also be preserved.
Owner subsequently ran the read-only SSH hash command; the saved file's
SHA-256 matched the capture summary exactly. Saved-byte verification is complete.
No coverage status changed. A Git-ignored local destination was prepared for
owner transfer of this same allowlisted probe artifact, not any credentials.

Owner then printed the saved allowlisted contract summary: exact symbol,
USD profit currency, points swap mode, directional swap values and triple-swap
weekday are present. Commission remains null. The configured offset remains
10800 seconds. These are current captured fields only; no effective rate
interval, commission applicability, rollover settlement clock or historical
DST mapping was established. Detailed numeric broker values remain private.
Interpretation reference: [MetaQuotes symbol properties](https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants).

Next read-only host-clock check, at the VPS prompt:

```bash
date -u +'%Y-%m-%dT%H:%M:%SZ'
timedatectl show -p Timezone -p NTPSynchronized -p NTP
```

This reports current host synchronization only; it does not prove the host was
synchronized at capture time or across the evaluation interval. The remaining
exact-symbol sessions require the full dated MT5 Specification. The account's
applicable fee terms require a broker source; commission null is not zero.

Owner supplied the command output: October 1 20:03:54 UTC,
Timezone=Etc/UTC, NTP=yes, NTPSynchronized=yes. Current host synchronization
check passes for that report. It is about five minutes after the contract
capture; do not backdate this check or use it to qualify broker DST coverage.
No qualifying observation interval was started.

## Specification session crop received

Follow-up: owner supplied 030710 and 030724 crops from the same Specification
window. The first shows XAUUSD-VIP, Gold US Dollar, contract size 100 and USD
margin/profit currencies. The second explicitly shows swap type In points,
matching directional values and daily multipliers, and overlaps the session
table. Current Specification symbol identity and swap units are now visible
across the owner-provided crops; the earlier header omission is resolved.
New pixels were saved privately as specification-header.png and
specification-swap-mode.png alongside the session crop; copy hashes matched.
Capture times come from owner-provided filenames, not an independently visible
host/broker clock. Current evidence is not historical effective coverage.

The header displays tick size 0.00 and tick value 0, unlike the saved SDK
snapshot's nonzero values. Preserve both representations; do not overwrite
precise SDK values from rounded/possibly different-time UI displays or claim
full contract reconciliation. No simulator contract inputs changed.
Outstanding sources: applicable account commission terms and effective dates,
rollover settlement timezone/time, rate-change/calendar history and broker
offset coverage for a frozen future protocol.

Owner supplied Screenshot 2026-10-02 030544.png. Visible quote sessions:
Monday–Thursday 01:00–23:58; Friday 01:00–23:57. Visible trade sessions:
Monday–Thursday 01:01–23:58; Friday 01:01–23:57. Sunday/Saturday rows are
blank. Daily swap multipliers are Monday/Tuesday/Thursday/Friday 1,
Wednesday 3. Directional values visually match the saved current probe.

The crop omits the symbol name and visible capture clock. Treat it as
owner-attributed current Specification evidence, not independently established
exact-symbol applicability or historical effective coverage. Request the top
of the same window showing XAUUSD-VIP and contract/swap mode. Original pixels
are preserved privately at .batch3-vibe/broker-intake-S7u11LUf/
specification-sessions.png; copied-byte hashes matched. No runtime values were
promoted to verified_historical.

Conditional on this schedule and the declared GMT+3 offset, the smoke's
September 30 21:00–21:45 UTC missing raw slots fall in the overnight closure
00:00–00:45 server time, before the 01:00 quote reopening. This supports the
break hypothesis but does not date the schedule to September 30 or establish
the blocking reasons for the two missing observation candles/baseline rows.
The smoke remains partial; historical costs/clock/session coverage and the
future qualifying protocol are still pending.

## First owner-terminal capture

Run in the existing VPS SSH terminal. This reuses the deployed read-only probe;
it starts no observer, scheduler, model job or order. Each attempt uses a new
private directory. Preserve failed attempts too. Do not print the raw JSON.

```bash
(
set -eC
umask 077
run=$(mktemp -d /root/kwg-gold-research/evidence/broker-intake-XXXXXXXX)
docker exec kwg-mt5-desktop bash -lc \
  'wine /opt/python/python.exe /opt/trading/batch2-evidence.py --login "$MT5_DEMO_LOGIN" --server-offset-seconds 10800' \
  > "$run/current-contract.json"
python3 - "$run" <<'PY'
import hashlib, json, sys
from pathlib import Path
p = Path(sys.argv[1]) / 'current-contract.json'
raw = p.read_bytes()
data = json.loads(raw)
samples = data.get('samples')
assert data.get('mode') == 'batch2-read-only-evidence'
assert data.get('symbol') == 'XAUUSD-VIP'
assert isinstance(samples, list) and len(samples) == 3
assert all(s.get('algo_trading_on') is False
           and s.get('gold_positions') == 0
           and s.get('gold_pending_orders') == 0 for s in samples)
print('Private capture:', p)
print('SHA256:', hashlib.sha256(raw).hexdigest())
print('Cost status:', data.get('cost_status'))
print('Clock status:', data.get('timestamp_status'))
print('Sample UTCs:', [s.get('host_utc') for s in samples])
print('Quote states:', [s.get('quote', {}).get('quote') for s in samples])
PY
)
```

The 10800 argument reuses the smoke's configured offset as a declared
hypothesis. This capture does not establish that it remains correct or covers
future DST changes. Stale quotes do not automatically mean disconnection;
retain the outcome and compare it with documented exact-symbol sessions.

## Sources still required

### Account-type evidence received

Owner's portal screenshot 031046 shows an active MT5 demo account labelled
Standard STP on VTMarkets-Demo. Private original preserved as account-type.png;
copy hash matched. Account identifier and balance are intentionally omitted
from this document. This establishes the displayed account's current category;
the screenshot alone does not independently match the deployed pinned login
or provide an effective historical fee interval.

October 2 recheck of the official commission guide lists zero separate gold
commission for Standard STP, with trading costs included in spread. That
supports the current account-type fee interpretation, subject to applicability
to the pinned demo account. Do not derive zero from the SDK's null field or
mark historical coverage from a current webpage.

Official PNL-Weekend Swap guidance states 00:00 settlement and potential later
weekend adjustments. The article does not explicitly establish the required
account-specific settlement timezone and historical event calendar. Broker
confirmation of the demo's rollover timezone, applicable multipliers/holiday
adjustments and effective rate/commission dates remains necessary. No broker
message was sent, and no collection or research dispatch started.

Preserve private dated sources showing the exact XAUUSD-VIP symbol header and
full Specification: sessions, swap mode, directional rates, triple-rollover
day and contract units. Account type must be supported by applicable broker
account terms, not inferred from the symbol suffix. Keep account identifiers
private; passwords and OAuth tokens are never evidence inputs.

Obtain applicable commission terms and their effective dates, directional
funding-rate schedules and changes, rollover settlement clock/calendar and
dated broker offset changes. Retrieval time alone does not create an effective
coverage interval. A snapshot proves the value shown at capture, not an
unchanged rate between captures. Use existing broker statements/notices when
available; no trade is needed to manufacture funding evidence. No broker
support message has been sent or authorized by this preparation.

Current official sources rechecked October 2:

- [Product sessions](https://get.vtmarkets.help/hc/en-us/articles/37317499627289-What-are-the-trading-hours): consult the product Specification.
- [Account commissions](https://get.vtmarkets.help/hc/en-us/articles/37317570987545-What-fees-commissions-are-charged-for-trading): account-dependent; applicability and effective dates still need evidence.
- [Server clock](https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time): GMT+2/+3 guidance; not a verified interval-specific raw epoch mapping.

## Observation sample

Do not reset the existing observer database or backfill missing observations.
First freeze the future protocol, reviewed deployed code identities, evidence
coverage, UTC windows, diagnostics preservation and untouched holdout. Existing
observer rows before that freeze stay diagnostic. The local cost-validator
correction has not been deployed; distinguish its source hash from the deployed
collector and old sealed rehearsal snapshot.

Then use the existing observer to accumulate the unchanged 60 observed
validation days and three flat >=20-day folds. Require at least 100 closed
simulated strategy trades under the approved policy, not 100 broker orders.
No market order is needed for qualification. Calendar elapsed days, bootstrap
rows, historical warmup and retrospectively exported candles do not automatically
count as qualifying observations. Do not promise a completion date until the
accepted start and counting convention are frozen.

No new long-running preservation process or collection run is launched by this
document. Evidence coverage and retention remain prerequisites. Real Batch 3
dispatch remains blocked; see [handoff](2026-10-02-batch2-batch3-handoff.md).
