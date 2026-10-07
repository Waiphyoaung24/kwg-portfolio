import { readFileSync } from 'node:fs';
import { normalizeStatus } from '../../ops/trading/worker/src/index.js';
import assert from 'node:assert/strict';
import { executionFields, statusFields } from './trading-status.mjs';

const report = { status: 'blocked', signal: 'none', checked_at: 100,
  reason: 'Gold quote is old', health: { terminal: 'connected', quote: 'stale',
    sampled_at: 100, quote_age_seconds: 90, tick_time: 10, history_count: 250, history_bar_time: 1 } };
let fields = statusFields(report, 105);
assert.equal(fields.state, 'Waiting for price');
assert.match(fields.connection, /Connected to demo/);
assert.match(fields.freshness, /Waiting for a fresh price/);
assert.match(fields.age, /90.000s/);
fields = statusFields(report, 131);
assert.equal(fields.state, 'Observer offline');
assert.match(fields.connection, /Unknown/);
assert.equal(fields.signal, 'Paused');
assert.match(statusFields({ ...report, health: null }, 105).connection, /Unknown/);
assert.match(statusFields({ ...report, health: { ...report.health, quote: 'future', quote_age_seconds: -100 } }, 105).freshness, /Future/);
assert.equal(statusFields({ ...report, health: { ...report.health, quote: 'fresh' } }, 105).freshness, 'Fresh at last check');
assert.match(statusFields({ ...report, health: { ...report.health, sampled_at: 101 } }, 100).connection, /Unknown/);
console.log('Trading status: stale/future quotes, history, independent readiness and browser expiry passed');
const priced = { ...report, status: 'observed', health: { ...report.health,
  quote: 'fresh', quote_age_seconds: 2, bid: 4100.25, ask: 4100.5 } };
assert.equal(statusFields(priced, 105).price, '4100.25 / 4100.50');
assert.equal(statusFields(priced, 129).price, '—');
for (const changes of [{ bid: null }, { ask: NaN }, { ask: 4000 }, { bid: -1 },
  { quote: 'stale' }, { terminal: 'guard_failed' }, { quote_age_seconds: -1 }]) {
  assert.equal(statusFields({ ...priced, health: { ...priced.health, ...changes } }, 105).price, '—');
}

const ready = { ...report, status: 'observing', health: { ...report.health, quote: 'fresh' } };
assert.equal(statusFields(ready, 105).state, 'Observing');
assert.equal(statusFields(ready, 105).signal, 'No setup yet');
assert.equal(statusFields({ ...ready, signal: 'long' }, 105).signal, 'Long setup');
assert.equal(statusFields({ ...ready, signal: 'short' }, 105).signal, 'Short setup');
assert.equal(statusFields({ ...ready, health: { ...ready.health, terminal: 'guard_failed' } }, 105).signal, 'Paused');
assert.match(statusFields(report, 105).guidance, /Leave the observer running/);
assert.match(statusFields(report, 131).guidance, /stopped reporting/);
assert.equal(statusFields({ ...report, health: null }, 105).state, 'Needs attention');

const execution = { mode: 'one-shot-demo', status: 'open', updated_at: 100,
  side: 'buy', volume: .01, opened_at: 99, closed_at: null, close_reason: null,
  realized_net_usd: null };
assert.equal(executionFields(null, 105).state, 'Unknown');
assert.equal(executionFields({ ...execution, status: 'disarmed' }, 105).state, 'Disarmed');
assert.equal(executionFields(execution, 105).state, 'Open');
assert.match(executionFields(execution, 105).guidance, /until one is hit/);
assert.match(executionFields({ ...execution, status: 'pending' }, 105).guidance, /Cancel it manually in MT5/);
assert.equal(executionFields(execution, 131).state, 'Unknown');
assert.equal(executionFields({ ...execution, status: 'needs_attention' }, 105).state, 'Needs attention');
const closedExecution = executionFields({ ...execution, status: 'closed',
  closed_at: 101, realized_net_usd: .8 }, 500);
assert.equal(closedExecution.state, 'Closed');
assert.match(closedExecution.closed, /1970/);
assert.match(closedExecution.result, /0\.80/);
assert.equal(closedExecution.guidance, 'The broker close was reconciled. This is a historical result.');
const desktopClose = executionFields({ ...execution, status: 'closed', close_reason: 'manual desktop',
  closed_at: 101, realized_net_usd: -.7 }, 500);
assert.equal(desktopClose.state, 'Closed');
assert.match(desktopClose.result, /-0\.70/);
assert.equal(desktopClose.guidance, 'Closed from MT5 desktop. This is a historical result.');


const contract = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/status-contract.json', import.meta.url)));
for (const item of contract.cases) {
  const fields = statusFields(normalizeStatus(item.payload, contract.now), contract.now);
  for (const [key, expected] of Object.entries(item.ui)) assert.equal(fields[key], expected, `${item.name}: ${key}`);
  if (item.executionUi) {
    const execution = executionFields(item.payload.execution, contract.now);
    for (const [key, expected] of Object.entries(item.executionUi)) assert.equal(execution[key], expected, `${item.name}: execution ${key}`);
  }
}
console.log('Trading status: shared contract passes Worker and page fields');
