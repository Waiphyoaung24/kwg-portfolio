import test from 'node:test';
import assert from 'node:assert/strict';
import { scorecard } from './src/jev-scorecard.js';
import { m15Snapshot } from './src/jev-m15.js';
import { JevObserver, jevRequest, JEV_MODEL } from './src/jev.js';
import worker from './src/index.js';

const now = 900000;
function row(stamp = now - 1800, net = 20) {
  return { bar_time: stamp, outcome: net === null ? 'pending' : 'resolved',
    trade: net === null ? null : { net_pnl: net, exit_bar: stamp + 900, exit_reason: 'target' },
    sample: { symbol: 'XAUUSD-VIP', timeframe: 'M15', captured_at: stamp + 901,
      bars: Array.from({ length: 250 }, (_, i) => ({ time: stamp - (249 - i) * 900, open: 4000, high: 4001, low: 3999, close: 4000 })),
      bid: 4000, ask: 4000.1, signal: 'long', eligible: true, slope_pass: false,
      indicators: { ema20: 4000, ema50: 3999, atr14: 2 },
      costs: { commission: 7, slippage: .1, overnight: 15, spread_multiplier: 1.5 },
      specification: { point: .01, trade_contract_size: 100, trade_tick_size: .01, volume_min: .01, volume_max: 100, volume_step: .01 },
      input_sha256: 'a'.repeat(64) } };
}
const report = outcomes => ({ version: 1, status: 'ready', qualification: 'unqualified_diagnostic',
  generated_at: now, last_bar: now - 900, samples: 10, gaps: 0, journal_config_sha256: 'b'.repeat(64), outcomes });
function receipt(row, decision = 'review_setup') {
  const s = row.sample, snapshot = m15Snapshot({ status: 'ready', checked_at: s.captured_at, sample: s }, s.captured_at);
  return { status: 'connected', model: JEV_MODEL, snapshot, questions: jevRequest(snapshot).questions,
    requested_at: s.captured_at * 1000, result: { model: JEV_MODEL, decision, confidence: 1,
      probabilities: { review_setup: +(decision === 'review_setup'), wait: +(decision === 'wait'), insufficient_data: +(decision === 'insufficient_data') },
      input_tokens: 100, completed_at: (s.captured_at + 1) * 1000 } };
}

test('paired outcomes retain rejects, abstentions and pending denominator; no-setup receipts are not queried', async () => {
  const rows = [row(now - 4500, 20), row(now - 3600, -5), row(now - 1800, null)];
  rows[1].sample.slope_pass = true; rows[2].sample.slope_pass = true;
  const receipts = new Map([[rows[0].bar_time, receipt(rows[0])], [rows[1].bar_time, receipt(rows[1], 'insufficient_data')]]);
  const r = await scorecard(report(rows), async stamp => receipts.get(stamp), now);
  assert.deepEqual(r.arms.baseline, { selected: 3, resolved: 2, coverage: 1, expectancy_usd: 7.5 });
  assert.equal(r.arms.slope.expectancy_usd, -5); assert.equal(r.arms.jev.expectancy_usd, 20);
  assert.equal(r.arms.jev.coverage, 1 / 3); assert.equal(r.response_coverage, 2 / 3);
  assert.equal(r.responses.missing, 1); assert.equal(r.abstained, 1); assert.equal(r.checkpoint.resolved, 2);
  assert.match(r.outcomes[0].prompt_sha256, /^[a-f0-9]{64}$/);
});

test('late, failed and changed-input/prompt receipts cannot enter Jev selection', async () => {
  const r = row();
  for (const [expected, change] of [
    ['late', x => x.result.completed_at = (r.sample.captured_at + 16) * 1000],
    ['late', x => x.requested_at = (r.sample.captured_at - 1) * 1000],
    ['mismatch', x => x.snapshot.ask += .1],
    ['mismatch', x => x.questions.observation.instructions += 'changed'],
    ['timeout', x => { x.status = 'timeout'; x.result = null; }],
    ['interrupted', x => { x.status = 'running'; x.result = null; }],
  ]) {
    const rec = receipt(r); change(rec);
    const result = await scorecard(report([r]), async () => rec, now);
    assert.equal(result.outcomes[0].response, expected); assert.equal(result.arms.jev.selected, 0);
    assert.equal(result.arms.baseline.resolved, 1);
  }
});

test('duplicate setup, stale export and fabricated resolution fail closed', async () => {
  const r = row();
  for (const input of [report([r, r]), { ...report([r]), generated_at: now - 121 },
    report([{ ...r, trade: { ...r.trade, net_pnl: null } }]),
    report([{ ...r, trade: { ...r.trade, exit_reason: 'window_end' } }])]) {
    await assert.rejects(scorecard(input, async () => receipt(r), now));
  }
  const empty = await scorecard(report([]), async () => { throw Error('No receipts'); }, now);
  assert.equal(empty.arms.baseline.expectancy_usd, null); assert.equal(empty.response_coverage, null);
});

test('scorecard read leaves provider budget and receipts untouched, and route requires owner', async t => {
  t.mock.method(Date, 'now', () => now * 1000);
  t.mock.method(globalThis, 'fetch', () => { throw Error('No provider requests'); });
  const r = row(), values = new Map([['record', { charged: 1441 }], [`m15:${r.bar_time}`, receipt(r)]]);
  const before = structuredClone(values);
  const observer = new JevObserver({ storage: { get: async key => values.get(key), put: () => assert.fail('Read only') } }, {});
  const result = await (await observer.fetch(new Request('https://internal/scorecard', { method: 'POST', body: JSON.stringify(report([r])) }))).json();
  assert.equal(result.accounted_usd, .001441); assert.deepEqual(values, before);
  assert.equal((await worker.fetch(new Request('https://site/api/trading/jev-scorecard'), {}, {})).status, 403);
  assert.equal((await worker.fetch(new Request('https://site/api/trading/jev-scorecard', { method: 'POST' }), {}, {})).status, 404);
});
