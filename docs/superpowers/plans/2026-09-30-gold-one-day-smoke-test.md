# Gold one-day pipeline smoke test

Owner approved a one-day smoke test, not a reduction of qualification policy.
Reuse the running observer, exclusive exporter and evidence probe. No new
service, scheduler, dependency, trade or simulator-to-gate adapter is needed.

## Scope and success

The interval is 24 elapsed hours starting at the next future M15 **bar-open**
boundary. The first eligible candle completes 15 minutes later. Scheduled
closures are included in elapsed time, not counted as missing trading candles
without checking exact-symbol session evidence. This is not a pristine holdout
or a qualifying validation fold.

Keep Algo Trading off and place no new orders during this test. Existing
read-only observer collection continues. Do not reset its database or restart
the desktop to manufacture coverage.

Pass/fail checks at the end:

- Saved files parse, hashes match bytes and the observer backup passes SQLite
  integrity checking. Preserve originals and refuse overwrite.
- New observer rows belong to the declared interval; distinguish observed rows
  from baseline/bootstrap rows. Report duplicates, gaps and blocked periods;
  boundary checks alone do not establish uninterrupted uptime.
- Dated raw exports preserve OHLC and raw broker epochs. Match observer rows to
  raw candles only using supported current offset evidence; flag mismatches or
  offset changes. Historical bars preceding the start remain diagnostic.
- Start/end evidence records pinned demo checks, quote state, exposure counts,
  current offset and current costs. Snapshot rates do not cover the intervening
  interval or establish an actual rollover charge.
- Produce a private pipeline summary with individual check results and explicit
  blockers. No strategy P&L, acceptance or provenance-qualified evaluation is
  inferred from this report.

Qualification remains `prepared_but_blocked`: 60 observed validation days,
100 closed trades per strategy, original folds and remaining policy gates are
unchanged. Batch 3 is not unlocked by this smoke test.

## Start on the VPS

Run the following block once with Algo Trading off. The directory is private
and unique. The manifest is created before its future start. It records the
five deployed source hashes; reported hashes must match the already reviewed
source freeze. If any command fails, preserve the directory as failed and do
not treat it as an active successful test.

```bash
set -e
umask 077
run="/root/kwg-gold-research/evidence/smoke-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$run"
docker exec kwg-mt5-desktop sha256sum /opt/trading/gold_signal.py /opt/trading/mt5_data.py /opt/trading/observe-gold.py /opt/trading/gold_qualification.py /opt/trading/export-gold.py > "$run/source-sha256.txt"
python3 - "$run" <<'PY'
import json, sys, time
from datetime import datetime, timezone
from pathlib import Path
p = Path(sys.argv[1])
now = time.time()
start = (int(now) // 900 + 1) * 900
utc = lambda stamp: datetime.fromtimestamp(stamp, timezone.utc).isoformat()
hashes = dict((line.split()[1], line.split()[0]) for line in (p / 'source-sha256.txt').read_text().splitlines())
manifest = {'schema_version': 1, 'kind': 'pipeline_smoke_test',
            'status': 'prepared', 'created_at_utc': utc(now),
            'start_bar_utc': utc(start), 'end_bar_utc_exclusive': utc(start + 86400),
            'start_epoch': start, 'end_epoch_exclusive': start + 86400,
            'symbol': 'XAUUSD-VIP', 'timeframe': 'M15',
            'configured_offset_seconds': 10800, 'source_sha256': hashes,
            'qualification': 'prepared_but_blocked',
            'cost_coverage': 'unverified', 'historical_clock_coverage': 'unverified',
            'holdout': None, 'policy_thresholds_changed': False}
with (p / 'manifest.json').open('x') as out:
    json.dump(manifest, out, indent=2, sort_keys=True)
    out.write('\n')
print(json.dumps({'directory': str(p), 'start_utc': utc(start),
                  'finish_after_utc': utc(start + 86400 + 900)}))
PY
docker exec kwg-mt5-desktop bash -lc 'wine /opt/python/python.exe /opt/trading/batch2-evidence.py --login "$MT5_DEMO_LOGIN" --server-offset-seconds 10800' > "$run/start-contract.json"
python3 -m json.tool "$run/start-contract.json" >/dev/null
docker exec kwg-mt5-desktop bash -lc 'wine /opt/python/python.exe /opt/trading/export-gold.py --login "$MT5_DEMO_LOGIN" --bars 10000 --output "C:\users\mt5\smoke-start-$(date -u +%Y%m%dT%H%M%SZ).json"' > "$run/start-export-receipt.json"
python3 -m json.tool "$run/start-export-receipt.json" >/dev/null
sha256sum "$run/manifest.json" "$run/source-sha256.txt" "$run/start-contract.json" "$run/start-export-receipt.json"
```

Review the start-contract payload privately: Algo off, zero gold positions and
pending orders, successful pinned-demo capture. Retain stale samples as stale;
an unexpected blocked open-session capture requires investigation. If setup
finishes after the declared start, mark this attempt failed and prepare a new
future interval; do not backdate it. `prepared` alone does not claim successful
collection. The exporter receipt identifies the exclusive file in persistent
MT5 home; later copy and verify those exact bytes, not merely the receipt hash.

The owner supplies the directory/start/finish summary and capture results to
confirm setup; no credentials, account identifiers or deal tickets are needed.

## Finish after the printed time

1. Check host UTC is at least the printed finish time, allowing the final
   included candle to complete. Preserve a new exclusive end-contract probe,
   read-only verifier and raw export with their byte hashes. A closed-session
   stale quote is reported with session context, not forced fresh.
2. Back up the existing observer database through SQLite's read-only source and
   `Connection.backup` into a new private filename; require `integrity_check=ok`.
   Copy it and both exact raw exports to the private run directory, verify their
   hashes against actual saved bytes, and preserve the deployed source hashes
   again. Source changes during the interval are a report blocker.
3. Review only rows whose normalized `bar_time` satisfies
   `start_epoch <= bar_time < end_epoch_exclusive`, with observation timestamps
   after candle completion. Report baseline/observed counts separately; raw
   exports must not fill missing live observation rows retrospectively.
4. Save a new exclusive private `smoke-report.json`: interval, artifact hashes,
   check results, missing observations, clock/cost limits and
   `qualification="prepared_but_blocked"`. Software/data delivery may pass
   while cost coverage remains blocked. Do not label a partial run successful.

The finish report uses existing data and Python stdlib. Exact finish commands
can be bound to the owner's confirmed run directory and source filenames after
start; no second collector or background job is introduced.
