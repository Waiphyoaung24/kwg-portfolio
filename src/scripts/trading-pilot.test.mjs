import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { normalizePilot, pilotFields } from './trading-pilot.mjs';
import { normalizeStatus } from '../../ops/trading/worker/src/index.js';
import { statusFields } from './trading-status.mjs';

const fixture = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/pilot-status.json', import.meta.url)));
const now = fixture.checked_at;

test('M1 strategy survives Worker and labels completed one-minute candles', () => {
  const m1 = { ...fixture, pilot: { ...fixture.pilot, strategy: 'gold-ema-v1-m1-slope-3' } };
  assert.deepEqual(normalizeStatus(m1, now), m1);
  assert.match(statusFields(m1, now).guidance, /completed 1-minute candles/);
  assert.equal(pilotFields(m1.pilot, now).canPause, true);
  assert.throws(() => normalizePilot({ ...m1.pilot, strategy: 'unknown' }, now));
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
