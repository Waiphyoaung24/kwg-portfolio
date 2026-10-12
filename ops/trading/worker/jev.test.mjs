import assert from 'node:assert/strict';
import test from 'node:test';
import worker from './src/index.js';
import { JevObserver, jevSnapshot, parseJev, JEV_MODEL } from './src/jev.js';

function storage(seed) {
  let value = seed, lock = Promise.resolve();
  const db = { get: async () => structuredClone(value), put: async (_, next) => { value = structuredClone(next); } };
  db.transaction = fn => { const next = lock.then(() => fn(db)); lock = next.catch(() => {}); return next; };
  return db;
}
const env = { TYPESAFE_API_KEY: 'fake-test-key', JEV_DATA_SHARING_APPROVED: 'true' };
const snapshot = () => ({ symbol: 'XAUUSD-VIP', timeframe: 'M1', checked_at: Math.floor(Date.now() / 1000), bid: 4000, ask: 4000.3, signal: 'none', strategy_status: 'blocked' });
const request = () => new Request('https://internal/', { method: 'POST', body: JSON.stringify(snapshot()) });
const answer = () => ({ model: JEV_MODEL, answers: { observation: { type: 'choice', choice: 'wait', confidence: 1,
  probabilities: { wait: 1, review_setup: 0, insufficient_data: 0 } } }, usage: { input_tokens: 392 } });
function mockFetch(t, fn) { const original = globalThis.fetch; globalThis.fetch = fn; t.after(() => { globalThis.fetch = original; }); }

test('market payload strips all account, position, free text and secret fields', () => {
  const now = Math.floor(Date.now()/1000);
  const report = { symbol: 'XAUUSD-VIP', checked_at: now, status: 'blocked', signal: 'none', reason: 'private text', login: 123,
    pilot: { strategy: 'gold-ema-v1-m1-trend-3', realized_net_usd: 999 }, execution: { side: 'buy' },
    health: { terminal: 'connected', quote: 'fresh', quote_age_seconds: .1, bid: 4000, ask: 4000.3, password: 'secret' } };
  const result = jevSnapshot(report, now);
  assert.equal(result.timeframe, 'M1');
  assert.deepEqual(Object.keys(result).sort(), ['ask','bid','checked_at','missing','signal','strategy_status','symbol','timeframe'].sort());
  for (const change of [{ symbol: 'BTCUSD' }, { checked_at: now-31 }, { checked_at: now+1 }, { status: 'offline' }, { health: { ...report.health, bid: NaN } }, { health: { ...report.health, quote: 'stale' } }]) {
    assert.throws(() => jevSnapshot({ ...report, ...change }, now));
  }
});

test('response validation rejects version drift, invalid probabilities and missing usage', () => {
  assert.equal(parseJev(answer()).decision, 'wait');
  for (const mutate of [a => a.model = 'jev-next', a => delete a.usage, a => a.usage.input_tokens = 70000,
    a => a.answers.observation.confidence = NaN, a => a.answers.observation.probabilities.wait = .1,
    a => a.answers.observation.choice = 'buy', a => a.answers.observation.probabilities.unexpected = 0]) {
    const a = answer(); mutate(a); assert.throws(() => parseJev(a));
  }
});

test('configuration gate prevents any provider request', async t => {
  mockFetch(t, () => { throw new Error('No provider request allowed'); });
  const observer = new JevObserver({ storage: storage() }, { TYPESAFE_API_KEY: 'fake' });
  assert.equal((await (await observer.fetch(request())).json()).status, 'not_configured');
});

test('one paid request survives duplicate concurrent clicks and object recreation', async t => {
  let calls = 0;
  mockFetch(t, async (url, options) => {
    calls++; assert.equal(url, 'https://api.typesafe.ai/v1/systemone');
    assert.equal(options.redirect, 'manual'); assert.equal(JSON.parse(options.body).model, JEV_MODEL);
    return Response.json(answer());
  });
  const db = storage(), observer = new JevObserver({ storage: db }, env);
  const responses = await Promise.all([observer.fetch(request()), observer.fetch(request())]);
  assert.deepEqual(responses.map(r => r.status).sort(), [200, 429]);
  assert.equal(calls, 1);
  const recreated = new JevObserver({ storage: db }, env);
  const result = await (await recreated.fetch(new Request('https://internal/'))).json();
  assert.equal(result.charged, 34); assert.equal(result.attempts, 1);
  assert.equal(result.result.decision, 'wait');
  assert.equal((await recreated.fetch(request())).status, 429);
  assert.equal(calls, 1);
});

test('timeout reserves spend, clears prior results and never retries', async t => {
  let calls = 0;
  mockFetch(t, async () => { calls++; throw new DOMException('fake', 'TimeoutError'); });
  const db = storage(), observer = new JevObserver({ storage: db }, env);
  const result = await (await observer.fetch(request())).json();
  assert.equal(result.status, 'timeout'); assert.equal(result.result, null);
  assert.equal(result.charged, 3017); assert.equal(calls, 1);
  assert.equal((await observer.fetch(request())).status, 429); assert.equal(calls, 1);
});

test('budget exhaustion is persistent and blocks before contacting provider', async t => {
  mockFetch(t, () => { throw new Error('No provider call'); });
  const db = storage({ charged: 4_999_000, attempts: 1, last_sample: 0, requested_at: 0, result: null });
  const observer = new JevObserver({ storage: db }, env);
  const result = await (await observer.fetch(request())).json();
  assert.equal(result.status, 'budget_exhausted'); assert.equal(result.charged, 4_999_000);
  const restarted = new JevObserver({ storage: db }, env);
  assert.equal((await (await restarted.fetch(new Request('https://internal/'))).json()).status, 'budget_exhausted');
});

test('an interrupted request is reported unavailable without retrying', async () => {
  const observer = new JevObserver({ storage: storage({ status: 'running', requested_at: Date.now()-31000, charged: 3017 }) }, env);
  const result = await (await observer.fetch(new Request('https://internal/'))).json();
  assert.equal(result.status, 'unavailable'); assert.equal(result.charged, 3017);
});

test('Worker enforces owner Access, same-origin POST and Gold-only requests', async () => {
  const url = 'https://waiphyoaung.com/api/trading/jev';
  const owner = { access: { getIdentity: async () => ({ email: 'owner@example.com' }) } };
  const config = { ...env, ALLOWED_VIEWER_EMAIL: 'owner@example.com', JEV_OBSERVER: {
    idFromName: () => 'one', get: () => ({ fetch: async () => Response.json({ status: 'ready' }) }),
  } };
  assert.equal((await worker.fetch(new Request(url), config, {})).status, 403);
  assert.equal((await worker.fetch(new Request(url), config, { access: { getIdentity: async () => ({ email: 'other@example.com' }) } })).status, 403);
  assert.equal((await worker.fetch(new Request(url+'?symbol=BTCUSD'), config, owner)).status, 400);
  assert.equal((await worker.fetch(new Request(url, { method: 'POST', body: '{}' }), config, owner)).status, 403);
  assert.equal((await worker.fetch(new Request(url), config, owner)).status, 200);
  assert.equal((await worker.fetch(new Request(url, { method: 'POST', headers: { Origin: 'https://waiphyoaung.com', 'Content-Type': 'application/json' }, body: '{"prompt":"override"}' }), config, owner)).status, 400);
});

test('Worker fetches fresh status itself; never forwards browser or account data', async t => {
  let forwarded;
  mockFetch(t, async () => Response.json({ mode: 'signal-only', symbol: 'XAUUSD-VIP', status: 'blocked', signal: 'none', bar_time: null,
    checked_at: Math.floor(Date.now()/1000), login: 123, health: { terminal: 'connected', quote: 'fresh', quote_age_seconds: 0, bid: 4000, ask: 4001 } }));
  const config = { ...env, ALLOWED_VIEWER_EMAIL: 'owner@example.com', STATUS_ORIGIN_URL: 'https://status.example/', JEV_OBSERVER: {
    idFromName: () => 'one', get: () => ({ fetch: async req => { forwarded = await req.json(); return Response.json({ status: 'connected' }); } }),
  } };
  const response = await worker.fetch(new Request('https://waiphyoaung.com/api/trading/jev', { method: 'POST',
    headers: { Origin: 'https://waiphyoaung.com', 'Content-Type': 'application/json' }, body: '{}' }), config,
    { access: { getIdentity: async () => ({ email: 'owner@example.com' }) } });
  assert.equal(response.status, 200); assert.equal(forwarded.symbol, 'XAUUSD-VIP'); assert.equal(forwarded.login, undefined);
});

test('Worker reports unavailable when the persistent observer rejects', async () => {
  const response = await worker.fetch(new Request('https://waiphyoaung.com/api/trading/jev'), {
    ...env, ALLOWED_VIEWER_EMAIL: 'owner@example.com', JEV_OBSERVER: {
      idFromName: () => 'one', get: () => ({ fetch: async () => { throw new Error('Internal detail'); } }),
    },
  }, { access: { getIdentity: async () => ({ email: 'owner@example.com' }) } });
  assert.equal(response.status, 503);
  const body = await response.json();
  assert.equal(body.status, 'unavailable'); assert.ok(!body.message.includes('Internal detail'));
});
