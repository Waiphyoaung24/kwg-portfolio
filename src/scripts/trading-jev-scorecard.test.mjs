import test from 'node:test';
import assert from 'node:assert/strict';
import { scorecardText, mountScorecard } from './trading-jev-scorecard.mjs';
const data = () => ({ status: 'ready', qualification: 'unqualified_diagnostic', eligible: 3, checkpoint: {}, responses: {}, outcomes: [],
  arms: { baseline: { selected: 3, resolved: 2, expectancy_usd: 7.5 }, slope: { selected: 1, resolved: 1, expectancy_usd: 0 }, jev: { selected: 0, resolved: 0, expectancy_usd: null } } });
test('missing results differ from zero; coverage and resolution have explicit denominators', () => {
  const cells = scorecardText(data());
  assert.equal(cells['baseline-net'], '$7.50'); assert.equal(cells['slope-net'], '$0.00'); assert.equal(cells['jev-net'], '—');
  assert.equal(cells['slope-coverage'], '1 / 3 (33%)'); assert.equal(cells['baseline-resolved'], '2 / 3');
  const bad = data(); bad.arms.jev.expectancy_usd = 0; assert.throws(() => scorecardText(bad));
});
test('Bitcoin never queries the Gold scorecard', () => {
  mountScorecard({ getElementById: () => ({}) }, { location: { search: '?symbol=BTCUSD' } }, () => assert.fail());
});

test('free polling clears prior numbers after failure and animates only the first success', async () => {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, { textContent: '', querySelectorAll: () => [], replaceChildren() {}, append() {} });
    return elements.get(id);
  };
  let poll, failed = false, animations = 0; const methods = [];
  const win = { location: { search: '' }, setInterval(fn) { poll = fn; return 1; }, clearInterval() {}, addEventListener() {} };
  const doc = { getElementById: get, hidden: false };
  mountScorecard(doc, win, async (_, options) => {
    methods.push(options.method ?? 'GET');
    if (failed) throw Error('Disconnected');
    const value = data(); value.responses = { timely: 0, missing: 3, late: 0, mismatch: 0, timeout: 0, unavailable: 0, interrupted: 0 };
    return Response.json(value);
  }, () => animations++);
  const settle = () => new Promise(resolve => setImmediate(resolve));
  await settle(); assert.equal(get('scorecard-baseline-net').textContent, '$7.50');
  failed = true; await poll(); await settle();
  assert.equal(get('scorecard-baseline-net').textContent, '—'); assert.match(get('scorecard-status').textContent, /unavailable/);
  failed = false; await poll(); await settle(); assert.equal(animations, 1);
  assert.deepEqual(methods, ['GET', 'GET', 'GET']);
});
