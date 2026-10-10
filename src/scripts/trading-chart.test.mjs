import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { appendQuote, chartSnapshot, quotePlot } from './trading-chart.mjs';
import { pilotFields } from './trading-pilot.mjs';
const fixture = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/pilot-status.json', import.meta.url)));

test('chart clears on stale or unavailable reports and never uses replay prices', () => {
  const now = fixture.checked_at;
  const current = chartSnapshot(fixture, now);
  assert.equal(current.quote.bid, fixture.health.bid);
  assert.equal(current.trades.length, 1);
  assert.deepEqual(chartSnapshot(null, now), { quote: null, trades: null, levels: null });
  assert.equal(chartSnapshot(fixture, now + 31).quote, null);
  assert.equal(current.levels.entry, fixture.execution.entry_price);
  assert.equal(chartSnapshot({ ...fixture, health: { ...fixture.health, bid: NaN } }, now).quote, null);
});

test('quote session deduplicates timestamps, bounds memory and breaks across gaps', () => {
  const q = at => ({ at, bid: 4000, ask: 4000.3 });
  let samples = [];
  for (let at = 1; at <= 200; at++) samples = appendQuote(samples, q(at));
  assert.equal(samples.length, 180);
  assert.equal(appendQuote(samples, q(200)), samples);
  assert.equal(appendQuote(samples, q(190)), samples);
  assert.deepEqual(appendQuote(samples, q(240)), [q(240)]);
  assert.deepEqual(appendQuote(samples, null), []);
  const plot = quotePlot(samples);
  assert.ok(plot.low < 4000 && plot.high > 4000.3);
  assert.ok(!plot.bid.includes('NaN'));
  assert.equal(quotePlot([]), null);
});

test('pilot countdown uses bounded readable durations', () => {
  const now = fixture.checked_at;
  assert.equal(pilotFields({ ...fixture.pilot, ends_at: now + 90061 }, now).remaining, '1d 1h 2m');
  assert.equal(pilotFields({ ...fixture.pilot, ends_at: now }, now).remaining, 'Ended');
});
