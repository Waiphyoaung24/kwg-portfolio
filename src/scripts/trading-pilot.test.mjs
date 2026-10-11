import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { entryReadiness, normalizePilot, pilotFields } from './trading-pilot.mjs';
import { normalizeStatus } from '../../ops/trading/worker/src/index.js';
import { statusFields } from './trading-status.mjs';

const fixture = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/pilot-status.json', import.meta.url)));
const now = fixture.checked_at;

test('entry readiness distinguishes open positions, pauses, filters and lost reports', () => {
  assert.equal(entryReadiness(fixture, now), 'Waiting for current trade to finish');
  const paused = { ...fixture, pilot: { ...fixture.pilot, status: 'paused' } };
  assert.equal(entryReadiness(paused, now), 'Paused — no new orders');
  for (const data of [null, { ...fixture, checked_at: undefined }, { ...fixture, status: 'offline' }]) {
    assert.equal(entryReadiness(data, now), 'Status unavailable');
  }
  assert.equal(entryReadiness(fixture, now + 31), 'Status unavailable');
  assert.equal(entryReadiness({ ...fixture, health: null }, now), 'Waiting for broker checks');
  const flat = { ...fixture, execution: { ...fixture.execution, status: 'closed' } };
  assert.equal(entryReadiness(flat, now), 'Enabled — awaiting an eligible setup');
  assert.equal(entryReadiness({ ...flat, status: 'blocked' }, now), 'Waiting for entry checks');
  const stale = { ...flat, health: { ...flat.health, quote: 'stale' } };
  assert.equal(entryReadiness(stale, now), 'Waiting for fresh quotes');
  assert.equal(statusFields(stale, now).signal, 'Waiting for fresh quotes');
});

test('continuous policy survives Worker without an expiry and rejects inconsistent windows', () => {
  const data = { ...fixture, pilot: { ...fixture.pilot, run_policy: 'continuous', ends_at: null } };
  assert.deepEqual(normalizeStatus(data, now), data);
  assert.equal(pilotFields(data.pilot, now).remaining, 'Until you pause');
  for (const changes of [{ run_policy: undefined }, { run_policy: 'forever' },
    { ends_at: now + 60 }, { status: 'standby' }, { status: 'expired' }]) {
    assert.throws(() => normalizePilot({ ...data.pilot, ...changes }, now));
  }
});

test('M1 strategy survives Worker and labels completed one-minute candles', () => {
  const m1 = { ...fixture, pilot: { ...fixture.pilot, strategy: 'gold-ema-v1-m1-slope-3' } };
  assert.deepEqual(normalizeStatus(m1, now), m1);
  assert.match(statusFields(m1, now).guidance, /completed 1-minute candles/);
  assert.equal(pilotFields(m1.pilot, now).canPause, true);
  assert.throws(() => normalizePilot({ ...m1.pilot, strategy: 'unknown' }, now));
});

test('M1 trend survives Worker and identifies its cooldown', () => {
  const trend = { ...fixture, pilot: { ...fixture.pilot, strategy: 'gold-ema-v1-m1-trend-3' } };
  assert.deepEqual(normalizeStatus(trend, now), trend);
  assert.match(statusFields(trend, now).guidance, /completed 1-minute candles/);
  assert.match(statusFields(trend, now).strategy, /EMA trend.*5-minute cooldown/);
  assert.equal(pilotFields(trend.pilot, now).canPause, true);
});

test('pilot contract survives Worker and produces truthful demo fields', () => {
  assert.deepEqual(normalizeStatus(fixture, now), fixture);
  assert.equal(statusFields(fixture, now).state, 'Demo pilot');
  assert.equal(pilotFields(fixture.pilot, now).realized, '-4.50 USD');
  assert.equal(pilotFields(fixture.pilot, now).canPause, true);
  assert.equal(pilotFields(fixture.pilot, now).trades.length, 1);
});

test('expired or malformed pilot snapshots never enable control or show current P&L', () => {
  for (const value of [null, { ...fixture.pilot, updated_at: now - 31 },
    { ...fixture.pilot, updated_at: now + 1 }, { ...fixture.pilot, completed_trades: -1 },
    { ...fixture.pilot, floating_usd: Infinity }, { ...fixture.pilot, qualification: 'qualified' }]) {
    const fields = pilotFields(value, now);
    assert.equal(fields.canPause, false);
    assert.equal(fields.realized, '—');
  }
  const cleaned = normalizePilot({ ...fixture.pilot, password: 'secret', login: 123 }, now);
  assert.equal(cleaned.password, undefined);
  assert.equal(cleaned.login, undefined);
  for (const status of ['standby', 'paused', 'needs_attention', 'expired']) {
    assert.equal(pilotFields({ ...fixture.pilot, status }, now).canPause, false);
  }
});
