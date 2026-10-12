import assert from 'node:assert/strict';
import test from 'node:test';
import { jevNotification, mountJevPanel } from './trading-jev.mjs';

test('one notification per outage and recovery; no repeated failure popups', () => {
  assert.match(jevNotification(null, 'not_configured'), /not connected/);
  assert.equal(jevNotification('not_configured', 'unavailable'), null);
  assert.equal(jevNotification('timeout', 'unavailable'), null);
  assert.match(jevNotification('timeout', 'connected'), /connected again/);
  assert.match(jevNotification('connected', 'timeout'), /timed out/);
  assert.match(jevNotification('connected', 'budget_exhausted'), /budget/);
});

test('Gold panel uses free GET polls, one POST per click and clears results on failure', async () => {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, { hidden: true, textContent: '', disabled: false, events: {}, addEventListener(name, fn) { this.events[name] = fn; } });
    return elements.get(id);
  };
  let poll, state = 'ready'; const calls = [];
  const win = { location: { search: '' }, setInterval(fn) { poll = fn; return 1; }, addEventListener() {}, clearInterval() {} };
  const doc = { getElementById: get, hidden: false };
  const fetcher = async (_, options) => {
    calls.push(options.method);
    if (state === 'throw') throw new DOMException('Timeout', 'TimeoutError');
    return Response.json({ status: state, message: '', feed: { status: 'ready' },
      snapshot: { timeframe: 'M15', captured_at: 900, checked_at: 1000 },
      result: state === 'connected' ? { decision: 'wait', confidence: 1, model: 'jev-1.13.0', latency_ms: 500 } : null });
  };
  const settle = () => new Promise(resolve => setImmediate(resolve));
  mountJevPanel(doc, win, fetcher); await settle();
  assert.deepEqual(calls, ['GET']); assert.equal(get('jev-panel').hidden, false);
  state = 'connected'; get('jev-observe').events.click(); await settle();
  assert.equal(calls.at(-1), 'POST'); assert.equal(get('jev-decision').textContent, 'Nonpositive modeled outlook');
  assert.equal(get('jev-snapshot-time').textContent, '1970-01-01 00:15:00 UTC');
  assert.match(get('jev-message').textContent, /Gold M15 feed connected/);
  state = 'throw'; poll(); await settle();
  assert.equal(calls.at(-1), 'GET'); assert.equal(get('jev-decision').textContent, 'No current assessment');
  assert.equal(get('jev-toast').hidden, false);
  get('jev-dismiss').events.click(); assert.equal(get('jev-toast').hidden, true);
  poll(); await settle(); assert.equal(get('jev-toast').hidden, true);
  state = 'connected'; poll(); await settle(); assert.match(get('jev-toast-text').textContent, /connected again/);
  assert.equal(calls.filter(x => x === 'POST').length, 1);
});

test('BTC does not mount or make Jev requests', () => {
  mountJevPanel({ getElementById: () => ({ hidden: true }) }, { location: { search: '?symbol=BTCUSD' } }, () => { throw new Error('No request'); });
});
