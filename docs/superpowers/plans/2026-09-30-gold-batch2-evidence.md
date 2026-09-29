# Batch 2 evidence checkpoint — 2026-09-30

The owner selected Batch 2 qualification after the supervised demo execution
tests. The immediate deliverable is dated, read-only broker evidence. This
checkpoint does not authorize another order, cancel the existing pending
order, or enable continuous strategy execution.

## Current evidence and gaps

- The owner reports a gold pending order in MT5. Its current fill/cancel state
  still needs a broker query; do not restart the desktop or resubmit an entry.
- The MCP observer reports Algo Trading on and refuses its signal-only check.
  That guard remains unchanged. The new evidence probe can inspect the pinned
  demo while Algo is on without calling an order API.
- The MCP baseline remains unqualified, using hypothetical historical costs.
  Lower/middle/stress validation reports contain 30/31/30 trades and net results
  of -305.195/-445.94/-186.87 USD. These previously inspected reports are
  diagnostic, not fresh promotion evidence.
- The original dataset SHA-256 is
  `ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614`.
  No private dataset was downloaded or re-evaluated for this checkpoint.

The [current VT Markets server-time guide](https://get.vtmarkets.help/hc/en-us/articles/37317868198297-What-is-VT-Markets-GMT-offset-or-server-time)
says the server uses GMT+2, or GMT+3 during daylight saving time. This supports
checking the currently observed +3-hour offset; it does not supply a dated
transition schedule for every historical candle. Do not apply a constant
10800-second correction to the entire historical dataset without evidence.

The [current commission guide](https://get.vtmarkets.help/hc/en-us/articles/37317570987545-What-fees-commissions-are-charged-for-trading)
distinguishes account tiers. Public terms and current terminal swap values
alone do not establish the exact account's historical fee coverage. Preserve
`cost_status: incomplete` until account tier, commission, dated swap rates,
rollover time/timezone, and effective coverage are sourced. Use public terms
only, as requested by the owner; leave uncovered history explicitly unqualified.

## Safe VPS evidence capture

Use the committed revision's raw URL for `batch2-evidence.py` when downloading
it. Its expected SHA-256 is
`b7f524a11b2ddeca4e72667fb9150a3ebc53cfbdb278fc21122db98a5d20b022`.
Check that hash before copying the file into `/opt/trading/`. Copying this
standalone probe requires no image rebuild, container restart, or network change.

Then run these commands in the existing interactive VPS SSH session:

```bash
docker exec kwg-mt5-desktop cat /opt/status/execution.json
docker exec -it kwg-mt5-desktop bash -lc 'wine /opt/python/python.exe /opt/trading/batch2-evidence.py --login "$MT5_DEMO_LOGIN" --server-offset-seconds 10800'
```

The login environment variable expands inside the container. Do not substitute
an SSH passphrase or print the container environment. Share only the probe JSON
and sanitized execution JSON; retain the dated transcript privately.

The probe takes three quote/contract/broker-state samples two seconds apart.
It publishes counts, whether positions have both SL and TP, current contract
specifications and swaps, raw tick epochs, adjusted quote age, and host UTC.
It omits account numbers, tickets, balances, credentials and tokens. An unavailable
positions/orders query refuses capture rather than reporting zero. MT5 documents
that distinction in [orders_get](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersget_py).
These samples are spot checks, not atomic reconciliation or historical qualification.

## Qualification gates after capture

1. Review the pending/open/closed state against the existing execution journal.
   Preserve broker-held protection; resolve uncertain ownership or failed queries
   before deployment changes. Cancellation requires an explicit owner action.
2. Record current account-tier public terms with retrieval date and source hashes.
   Bind costs to effective dates; obtain rollover/timezone evidence without
   assuming that swap-free administration rules apply to this account.
3. Establish historical timestamp interpretation and DST coverage for the frozen
   dataset, or start a prospectively dated dataset whose evidence can be traced.
4. Run the existing simulator/evaluator only with covered inputs and the approved
   evaluation policy. Preserve holdout separation, minimum trade/day/fold gates,
   and the `simulator_provenance_unverified` cap until report provenance is verified.
5. Produce a reproducible baseline result that identifies every remaining blocker.
   Batch 3 research and strategy promotion remain blocked until required gates pass.

## Local validation

104 Python tests passed, including a pending-order inspection with Algo on,
wrong-account rejection, and unavailable-query rejection. The probe reuses the
existing account, quote and contract readers. Docker packaging includes it for a
future reviewed build; no VPS process or broker order was changed locally.
