import assert from 'node:assert/strict';
import test from 'node:test';
import worker, { normalizeStatus } from './src/index.js';

const url = 'https://waiphyoaung.com/api/trading/status';
const env = { ALLOWED_VIEWER_EMAIL: 'owner@example.com', STATUS_ORIGIN_URL: 'https://origin.example/status', STATUS_ACCESS_CLIENT_ID: 'id', STATUS_ACCESS_CLIENT_SECRET: 'secret' };
const access = { getIdentity: async () => ({ email: 'owner@example.com' }) };

test('operations page requires exact Access identity and supports only fixed GET paths', async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  let calls = 0;
  globalThis.fetch = async (origin) => {
    calls++;
    assert.equal(new URL(origin).pathname, '/vault/trading-bot');
    return new Response('<h1>Gold operations</h1>', { headers: { 'Content-Type': 'text/html' } });
  };
  for (const path of ['/vault/trading-bot', '/vault/trading-bot/']) {
    const page = new Request(`https://waiphyoaung.com${path}`);
    assert.equal((await worker.fetch(page, env, {})).status, 403);
    assert.equal((await worker.fetch(page, env, { access: { getIdentity: async () => ({ email: 'other@example.com' }) } })).status, 403);
    assert.equal(calls, path.endsWith('/') ? 1 : 0);
    const response = await worker.fetch(page, env, { access });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('Cache-Control'), 'no-store');
    assert.equal(response.headers.get('X-Robots-Tag'), 'noindex');
    assert.equal(await response.text(), '<h1>Gold operations</h1>');
  }
  assert.equal((await worker.fetch(new Request('https://waiphyoaung.com/vault/trading-bot', { method: 'POST' }), env, { access })).status, 404);
  assert.equal((await worker.fetch(new Request('https://waiphyoaung.com/vault/trading-bot/unknown'), env, { access })).status, 404);
  assert.equal(calls, 2);
});

test('health evidence is sanitized and expires at 30 seconds', () => {
  const report = { mode: 'signal-only', symbol: 'XAUUSD-VIP', status: 'blocked', signal: 'none',
    checked_at: 100, bar_time: null, health: { terminal: 'connected', quote: 'future',
      sampled_at: 100, tick_time: 110, quote_age_seconds: -10, login: 123, password: 'secret' } };
  const result = normalizeStatus(report, 105);
  assert.equal(result.health.quote_age_seconds, -10);
  assert.equal(result.health.login, undefined);
  assert.equal(result.health.password, undefined);
  assert.equal(normalizeStatus(report, 131).status, 'offline');
  for (const quote_age_seconds of [NaN, Infinity, '10', true]) {
    assert.throws(() => normalizeStatus({ ...report, health: { ...report.health, quote_age_seconds } }, 105));
  }
});

test('execution state is allowlisted and stale open state expires', () => {
  const report = { mode: 'signal-only', symbol: 'XAUUSD-VIP', status: 'blocked', signal: 'none',
    reason: 'Algo Trading enabled', checked_at: 100, bar_time: null,
    execution: { mode: 'one-shot-demo', status: 'open', updated_at: 100, side: 'buy',
      volume: .01, opened_at: 99, closed_at: null, close_reason: null,
      realized_net_usd: null, login: 123, ticket: 456, password: 'secret' } };
  const current = normalizeStatus(report, 105).execution;
  assert.equal(current.status, 'open');
  assert.equal(normalizeStatus({ ...report, execution: { ...report.execution, status: 'pending' } }, 105).execution.status, 'pending');
  for (const field of ['login', 'ticket', 'password']) assert.equal(current[field], undefined);
  assert.equal(normalizeStatus(report, 131).execution, null);
  const closed = normalizeStatus({ ...report, execution: { ...report.execution,
    status: 'closed', closed_at: 101, realized_net_usd: .8 } }, 500).execution;
  assert.equal(closed.closed_at, 101);
  assert.equal(closed.realized_net_usd, .8);
  assert.throws(() => normalizeStatus({ ...report, execution: { ...report.execution,
    status: 'filled' } }, 105));
  assert.throws(() => normalizeStatus({ ...report, execution: { ...report.execution,
    volume: Infinity } }, 105));
  assert.equal(normalizeStatus({ ...report, execution: undefined }, 105).execution, undefined);
});

test('origin failure remains unavailable rather than a healthy connection', async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async () => new Response('unavailable', { status: 503 });
  const response = await worker.fetch(new Request(url), env, { access });
  assert.equal(response.status, 503);
  assert.equal((await response.json()).status, 'offline');
});

test('requires Access and the exact viewer before calling origin', async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = () => { throw new Error('origin must not be called'); };
  assert.equal((await worker.fetch(new Request(url), env, {})).status, 403);
  assert.equal((await worker.fetch(new Request(url), env, { access: { getIdentity: async () => ({ email: 'other@example.com' }) } })).status, 403);
});

test('returns only validated read-only status', async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.headers['CF-Access-Client-ID'], 'id');
    return Response.json({ mode: 'signal-only', symbol: 'XAUUSD-VIP', status: 'blocked', signal: 'none', reason: 'Stale quote', checked_at: Math.floor(Date.now() / 1000), bar_time: null, login: 123 });
  };
  const response = await worker.fetch(new Request(url), env, { access });
  assert.equal(response.status, 200);
  const status = await response.json();
  assert.equal(status.status, 'blocked');
  assert.equal(status.login, undefined);
  assert.equal(normalizeStatus({ ...status, checked_at: 1 }).status, 'offline');
});

test('serves the trading page only to the approved Access viewer', async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  let calls = 0;
  globalThis.fetch = async (origin) => {
    calls++;
    assert.equal(new URL(origin).pathname, '/vault/trading');
    return new Response('<h1>Trading</h1>', { headers: { 'Content-Type': 'text/html' } });
  };
  const page = new Request('https://waiphyoaung.com/vault/trading');
  assert.equal((await worker.fetch(page, env, {})).status, 403);
  assert.equal(calls, 0);
  const response = await worker.fetch(page, env, { access });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(await response.text(), '<h1>Trading</h1>');
  assert.equal(calls, 1);
});

test('demo control requires exact Access viewer and same-origin POST', async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  globalThis.fetch = () => { throw new Error('origin must not be called'); };
  const request = (origin) => new Request('https://waiphyoaung.com/api/trading/preview', {
    method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json' }, body: '{"side":"buy"}',
  });
  const enabled = { ...env, TRADING_CONTROL_SECRET: 'private-control-secret' };
  assert.equal((await worker.fetch(request('https://waiphyoaung.com'), enabled, {})).status, 403);
  assert.equal((await worker.fetch(request('https://evil.example'), enabled, { access })).status, 400);
  assert.equal((await worker.fetch(request('https://waiphyoaung.com'), env, { access })).status, 503);
  assert.equal((await worker.fetch(new Request('https://waiphyoaung.com/api/trading/arm'), enabled, { access })).status, 404);
});

test('reviewed preview and one arm reach only the private control route', async (t) => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  const enabled = { ...env, TRADING_CONTROL_SECRET: 'private-control-secret' };
  let calls = 0;
  globalThis.fetch = async (origin, options) => {
    calls++;
    assert.equal(options.method, 'POST');
    assert.equal(options.headers['X-KWG-Control-Secret'], enabled.TRADING_CONTROL_SECRET);
    if (new URL(origin).pathname === '/control/arm') {
      assert.deepEqual(JSON.parse(options.body), { token: 'a'.repeat(32) });
      return Response.json({ status: 'starting', account: 123 }, { status: 202 });
    }
    assert.equal(new URL(origin).pathname, '/control/preview');
    assert.deepEqual(JSON.parse(options.body), { side: 'buy', entry: 4142.51, sl: 4129.57, tp: 4161.92 });
    return Response.json({ token: 'a'.repeat(32), preview: {
      mode: 'private-demo-preview', symbol: 'XAUUSD-VIP', side: 'buy', volume: .01,
      quote_reference: 4142.51, sl: 4129.57, tp: 4161.92, modeled_stop_usd: 12.94,
      modeled_stop_pct_of_equity: .01294, previewed_at: 1790672644,
      order_kind: 'Buy limit', pending_until_cancelled: true,
      order_sent: false, order_check_passed: false, account: 123,
    } });
  };
  const post = (route, body) => new Request(`https://waiphyoaung.com/api/trading/${route}`, {
    method: 'POST', headers: { Origin: 'https://waiphyoaung.com', 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const preview = await worker.fetch(post('preview', { side: 'buy', entry: 4142.51,
    sl: 4129.57, tp: 4161.92 }), enabled, { access });
  assert.equal(preview.status, 200);
  const result = await preview.json();
  assert.equal(result.preview.account, undefined);
  assert.equal(result.token, 'a'.repeat(32));
  const armed = await worker.fetch(post('arm', { token: result.token }), enabled, { access });
  assert.equal(armed.status, 202);
  assert.deepEqual(await armed.json(), { status: 'starting' });
  assert.equal(calls, 2);
});
