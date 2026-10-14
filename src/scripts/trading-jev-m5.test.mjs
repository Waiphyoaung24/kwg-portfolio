import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { vetoActivityView, budgetText, m5Mode, m5ScorecardView, mountJevM5 } from './trading-jev-m5.mjs';

const receipts = (ok = 0, rest = {}) => ({ ok, timeout: 0, unavailable: 0, budget_exhausted: 0, invalid: 0, missing: 0, late: 0, ...rest });
const empty = () => ({
  status: 'ready', generated_at: 1791832500, candidates: 0, pending: 1, no_state: 0, closed: 0, unresolved: 0,
  mode_counts: { shadow: 1 }, receipts: receipts(),
  all: { trades: 0, avg_net_usd: null }, jev_kept: { trades: 0, avg_net_usd: null }, jev_vetoed: { trades: 0, avg_net_usd: null },
  gate: { min_closed: 50, bad_receipt_max: 0.2, bad_receipt_rate: null, passes: false,
    reasons: ['Need 50 closed shadow trades with resolved P/L; have 0', 'No due shadow candidates to measure receipts',
      'Jev-kept average net P/L does not beat all trades'] },
  qualification: 'demo fills; unqualified; not a profitability claim',
});
const populated = () => ({
  ...empty(), candidates: 12, pending: 0, no_state: 1, closed: 10, unresolved: 1,
  receipts: receipts(9, { timeout: 1, missing: 1 }),
  all: { trades: 9, avg_net_usd: -1.5 }, jev_kept: { trades: 6, avg_net_usd: 2.25 }, jev_vetoed: { trades: 3, avg_net_usd: -9 },
  gate: { min_closed: 50, bad_receipt_max: 0.2, bad_receipt_rate: 0.25, passes: false,
    reasons: ['Need 50 closed shadow trades with resolved P/L; have 9', 'Bad receipts 3/12 reach the 20% limit'] },
});
const passing = () => ({
  ...populated(), candidates: 60, closed: 55, unresolved: 0, no_state: 0, receipts: receipts(57, { late: 3 }),
  all: { trades: 55, avg_net_usd: 0 }, jev_kept: { trades: 40, avg_net_usd: 1 }, jev_vetoed: { trades: 15, avg_net_usd: -2.67 },
  gate: { min_closed: 50, bad_receipt_max: 0.2, bad_receipt_rate: 0.05, passes: true, reasons: [] },
});

test('empty scorecard shows missing averages, not zero, and every unmet gate', () => {
  const view = m5ScorecardView(empty());
  assert.equal(view.kept.text, '— · 0 trades'); assert.equal(view.kept.tone, 'none');
  assert.equal(view.all.text, '— · 0 trades');
  assert.match(view.summary, /No due shadow candidates yet/);
  assert.equal(view.counts, 'Pending 1 · No Jev state 0 · Closed without P/L 0');
  assert.equal(view.verdict, 'Gate not met');
  assert.deepEqual(view.checks.map(c => c.met), [false, false, false]);
  assert.equal(view.checks[1].detail, 'No due candidates yet');
  assert.deepEqual(view.checks.map(c => c.reason), empty().gate.reasons);
});

test('populated scorecard pairs every average with a sign and an arrow and counts receipt health', () => {
  const view = m5ScorecardView(populated());
  assert.equal(view.kept.text, '↑ +$2.25 · 6 trades'); assert.equal(view.kept.tone, 'up');
  assert.equal(view.all.text, '↓ −$1.50 · 9 trades'); assert.equal(view.all.tone, 'down');
  assert.equal(view.vetoed.text, '↓ −$9.00 · 3 trades');
  assert.equal(view.receipts, 'OK 9 · Timeout 1 · Unavailable 0 · Budget exhausted 0 · Invalid 0 · Missing 1 · Late 0');
  assert.equal(view.checks[0].detail, '9 / 50 closed shadow trades');
  assert.equal(view.checks[1].detail, '3 / 12 bad (25%), limit under 20%');
  assert.equal(view.checks[1].reason, 'Bad receipts 3/12 reach the 20% limit');
  assert.equal(view.checks[2].met, true); assert.equal(view.checks[2].reason, null);
});

test('passing gate still requires owner review and a flat average reads as zero with its own arrow', () => {
  const view = m5ScorecardView(passing());
  assert.equal(view.verdict, 'Gate met · owner review required before veto');
  assert.deepEqual(view.checks.map(c => c.met), [true, true, true]);
  assert.equal(view.all.text, '→ $0.00 · 55 trades'); assert.equal(view.all.tone, 'flat');
});

test('unavailable or malformed reports never show numbers', () => {
  const view = m5ScorecardView({ status: 'unavailable', generated_at: 1, error: 'OSError' });
  assert.equal(view.available, false);
  assert.equal(view.kept.text, '—');
  assert.equal(view.summary, 'Scorecard unavailable or older than 2 minutes; results are not zero.');
  assert.equal(view.updated, '');
  for (const change of [{ candidates: -1 }, { qualification: 'qualified' }, { receipts: receipts(1) },
    { all: { trades: 0, avg_net_usd: 0 } }, { gate: { ...empty().gate, passes: true } }, { gate: { ...empty().gate, reasons: 'x' } },
    { closed: 1 }, { gate: { ...empty().gate, bad_receipt_max: null } }, { gate: { ...empty().gate, bad_receipt_max: Infinity } }]) {
    assert.throws(() => m5ScorecardView({ ...empty(), ...change }));
  }
});

test('mode badge reads only the current M5 pilot report', () => {
  const pilot = { strategy: 'gold-ema-v1-m5-trend-jev', jev_mode: 'shadow' };
  assert.equal(m5Mode('Active', pilot), 'Shadow');
  assert.equal(m5Mode('Paused', { ...pilot, jev_mode: 'veto' }), 'Veto');
  assert.equal(m5Mode('Active', { strategy: pilot.strategy }), 'Mode unknown');
  assert.equal(m5Mode('Active', { strategy: 'gold-ema-v1-m1-trend-3' }), 'Not running');
  assert.equal(m5Mode('Unknown', pilot), 'Mode unavailable');
});

test('budget shows the remaining shared Jev budget or a dash', () => {
  assert.equal(budgetText({ remaining_usd: 4.987654, budget_usd: 5 }), '$4.99 of $5.00 left');
  assert.equal(budgetText({ status: 'not_configured', budget_usd: 5 }), '— of $5.00 left');
  assert.equal(budgetText(null), '— of $5.00 left');
});

test('panel polls with GET only, skips Bitcoin and clears numbers after a failure', async () => {
  mountJevM5({ getElementById: () => ({}) }, { location: { search: '?symbol=BTCUSD' } }, () => assert.fail());
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, { textContent: '', dataset: {}, hidden: false, replaceChildren(...items) { this.items = items; } });
    return elements.get(id);
  };
  const doc = { getElementById: get, hidden: false, createElement: () => ({ textContent: '', dataset: {}, append() {} }) };
  let poll, failed = false; const calls = [];
  const win = { location: { search: '' }, setInterval(fn) { poll = fn; return 1; }, clearInterval() {}, addEventListener() {} };
  mountJevM5(doc, win, async (url, options) => {
    calls.push(`${options.method ?? 'GET'} ${url}`);
    if (failed) throw Error('Disconnected');
    return Response.json(url.endsWith('jev') ? { remaining_usd: 4.5, budget_usd: 5 } : populated());
  });
  const settle = () => new Promise(resolve => setImmediate(resolve));
  await settle();
  assert.equal(get('jev-m5-kept').textContent, '↑ +$2.25 · 6 trades');
  assert.equal(get('jev-m5-kept').dataset.tone, 'up');
  assert.equal(get('jev-m5-budget').textContent, '$4.50 of $5.00 left');
  failed = true; await poll(); await settle();
  assert.equal(get('jev-m5-kept').textContent, '—');
  assert.equal(get('jev-m5-budget').textContent, '— of $5.00 left');
  assert.match(get('jev-m5-summary').textContent, /unavailable/);
  assert.ok(calls.every(call => call.startsWith('GET ')));
  assert.deepEqual([...new Set(calls)].sort(), ['GET /api/trading/jev', 'GET /api/trading/jev-m5-scorecard']);
});

test('an unknown gate reason stays visible as an unmet Other row', () => {
  const data = empty(); data.gate.reasons = [...data.gate.reasons, 'Owner paused veto review'];
  const view = m5ScorecardView(data);
  assert.equal(view.checks.length, 4);
  assert.deepEqual(view.checks[3], { label: 'Other', detail: 'Reported by the scorecard', met: false, reason: 'Owner paused veto review' });
});

test('report time stays outside the live summary', () => {
  const view = m5ScorecardView(populated());
  assert.doesNotMatch(view.summary, /updated/i);
  assert.equal(view.updated, 'Report updated 2026-10-12 19:15:00 UTC.');
});

test('real scorecard exports map through the view', () => {
  const load = name => JSON.parse(readFileSync(new URL(`../../ops/trading/fixtures/jev-m5-scorecard-${name}.json`, import.meta.url)));
  const none = m5ScorecardView(load('empty'));
  assert.equal(none.verdict, 'Gate not met');
  assert.deepEqual(none.checks.map(c => c.met), [false, false, false]);
  const bad = m5ScorecardView(load('bad-receipt'));
  assert.equal(bad.checks[1].detail, '3 / 5 bad (60%), limit under 20%');
  assert.equal(bad.checks[1].reason, 'Bad receipts 3/5 reach the 20% limit');
  assert.equal(bad.kept.text, '↑ +$5.00 · 1 trade');
  assert.equal(bad.counts, 'Pending 0 · No Jev state 1 · Closed without P/L 0');
  const pass = m5ScorecardView(load('passing'));
  assert.equal(pass.verdict, 'Gate met · owner review required before veto');
  assert.deepEqual(pass.checks.map(c => c.met), [true, true, true]);
  assert.equal(pass.all.text, '↑ +$0.87 · 60 trades');
});


test('veto activity renders results and block reasons independently of qualification', () => {
  const data = { candidates: 2, submitted: 1, blocked: 1, pending: 0, no_state: 0,
    unresolved: 0, receipts: receipts(1, { timeout: 1 }),
    results: { trades: 1, avg_net_usd: 8.3, net_usd: 8.3 },
    recent: [{ bar_time: 1791936000, side: 'short', receipt: 'timeout', choice: null,
      confidence: null, submitted: false, state: null, net_usd: null, reason: 'Jev timeout' }] };
  const view = vetoActivityView(data);
  assert.match(view.summary, /1 submitted.*1 blocked/);
  assert.match(view.results, /8.30/);
  assert.match(view.rows[0], /Jev timeout/);
  assert.match(view.rows[0], /Blocked/);
  assert.match(vetoActivityView(null).summary, /unavailable/i);
  assert.equal(vetoActivityView(null).rows.length, 0);
  assert.match(vetoActivityView({ ...data, blocked: -1 }).summary, /unavailable/i);
});

test('real veto export shows receipts, linked P/L, and the recorded block reason', () => {
  const data = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/jev-m5-scorecard-veto.json', import.meta.url)));
  const view = vetoActivityView(data.veto);
  assert.match(view.summary, /3 completed decisions · 2 submitted · 1 blocked/);
  assert.match(view.results, /5.80/);
  assert.match(view.receipts, /OK 2 · Timeout 1/);
  assert.match(view.rows[0], /Jev timeout/);
  assert.match(view.rows[1], /2.50/);
  assert.match(view.rows[2], /8.30/);
  const shadow = JSON.parse(readFileSync(new URL('../../ops/trading/fixtures/jev-m5-scorecard-passing.json', import.meta.url)));
  assert.deepEqual(data.gate, shadow.gate);
  assert.deepEqual(data.all, shadow.all);
});
