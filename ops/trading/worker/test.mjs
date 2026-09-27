import assert from 'node:assert/strict';
import test from 'node:test';
import worker, { normalizeStatus } from './src/index.js';

const url = 'https://waiphyoaung.com/api/trading/status';
const env = { ALLOWED_VIEWER_EMAIL: 'owner@example.com', STATUS_ORIGIN_URL: 'https://origin.example/status', STATUS_ACCESS_CLIENT_ID: 'id', STATUS_ACCESS_CLIENT_SECRET: 'secret' };
const access = { getIdentity: async () => ({ email: 'owner@example.com' }) };

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
