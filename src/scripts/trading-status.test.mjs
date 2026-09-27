import assert from 'node:assert/strict';
import { statusFields } from './trading-status.mjs';

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

const ready = { ...report, status: 'observing', health: { ...report.health, quote: 'fresh' } };
assert.equal(statusFields(ready, 105).state, 'Observing');
assert.equal(statusFields(ready, 105).signal, 'No setup yet');
assert.equal(statusFields({ ...ready, signal: 'long' }, 105).signal, 'Long setup');
assert.equal(statusFields({ ...ready, signal: 'short' }, 105).signal, 'Short setup');
assert.equal(statusFields({ ...ready, health: { ...ready.health, terminal: 'guard_failed' } }, 105).signal, 'Paused');
assert.match(statusFields(report, 105).guidance, /Leave the observer running/);
assert.match(statusFields(report, 131).guidance, /stopped reporting/);
assert.equal(statusFields({ ...report, health: null }, 105).state, 'Needs attention');
