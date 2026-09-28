import assert from 'node:assert/strict';
import test from 'node:test';
import worker, { baselineSummary, goldStatus } from './src/index.js';

const token = 'a'.repeat(64);
const endpoint = 'https://example.workers.dev/mcp';
const context = { waitUntil() {} };

function message(method, params = {}, id = 1) {
  return new Request(endpoint, {
    method: 'POST',
    headers: {
      Host: 'example.workers.dev',
      Authorization: `Bearer ${token}`,
      Accept: 'application/json, text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ jsonrpc: '2.0', id, method, params }),
  });
}

async function result(response) {
  const body = await response.text();
  assert.equal(response.status, 200, body);
  const json = response.headers.get('content-type')?.includes('text/event-stream')
    ? body.match(/^data: (.+)$/m)?.[1] : body;
  assert.ok(json, body);
  return JSON.parse(json);
}

test('MCP denies unauthenticated and unconfigured requests', async () => {
  const request = new Request(endpoint, { method: 'POST' });
  assert.equal((await worker.fetch(request, {}, context)).status, 503);
  assert.equal((await worker.fetch(request, { MCP_BEARER_TOKEN: token }, context)).status, 401);
  assert.equal((await worker.fetch(request, { MCP_BEARER_TOKEN: 'short' }, context)).status, 503);
  assert.equal((await worker.fetch(new Request('https://example.workers.dev/other'), { MCP_BEARER_TOKEN: token }, context)).status, 404);
});

test('MCP lists only two read-only tools and returns the baseline', async () => {
  const env = { MCP_BEARER_TOKEN: token };
  const listed = await result(await worker.fetch(message('tools/list'), env, context));
  assert.deepEqual(listed.result.tools.map(tool => tool.name).sort(), ['get_baseline_summary', 'get_gold_status']);
  const called = await result(await worker.fetch(message('tools/call', { name: 'get_baseline_summary', arguments: {} }), env, context));
  const summary = JSON.parse(called.result.content[0].text);
  assert.deepEqual(summary, baselineSummary());
  assert.equal(summary.promotion, 'blocked');
  assert.equal(summary.candidate_compared, false);
  const status = await result(await worker.fetch(message('tools/call', { name: 'get_gold_status', arguments: {} }), env, context));
  assert.equal(status.result.isError, true);
  assert.equal(status.result.content[0].text, 'Gold observer status is unavailable.');
});

test('gold status allowlists fresh data and expires an old observer report', async () => {
  const now = Math.floor(Date.now() / 1000);
  const env = {
    STATUS_ORIGIN_URL: 'https://status.example.com/anything',
    STATUS_ACCESS_CLIENT_ID: 'id',
    STATUS_ACCESS_CLIENT_SECRET: 'secret',
  };
  const snapshot = {
    mode: 'signal-only', symbol: 'XAUUSD-VIP', status: 'observed', signal: 'long',
    reason: 'evaluated', checked_at: now, bar_time: now - 900,
    account: 1344907, balance: 100000,
  };
  let calls = 0;
  const fetcher = async (url, options) => {
    calls++;
    assert.equal(url.toString(), 'https://status.example.com/status');
    assert.equal(options.headers['CF-Access-Client-ID'], 'id');
    assert.equal(options.headers['CF-Access-Client-Secret'], 'secret');
    return Response.json(snapshot);
  };
  const fresh = await goldStatus(env, fetcher);
  assert.equal(fresh.status, 'observed');
  assert.equal(fresh.signal, 'long');
  assert.equal('account' in fresh, false);
  assert.equal('balance' in fresh, false);
  snapshot.checked_at = now - 60;
  const stale = await goldStatus(env, fetcher);
  assert.equal(stale.status, 'offline');
  assert.equal(stale.signal, 'none');
  assert.equal(calls, 2);
});

test('gold status fails closed on missing origin credentials or invalid response', async () => {
  await assert.rejects(goldStatus({}), /not configured/);
  await assert.rejects(goldStatus({
    STATUS_ORIGIN_URL: 'http://status.example.com', STATUS_ACCESS_CLIENT_ID: 'id', STATUS_ACCESS_CLIENT_SECRET: 'secret',
  }), /HTTPS/);
  await assert.rejects(goldStatus({
    STATUS_ORIGIN_URL: 'https://status.example.com', STATUS_ACCESS_CLIENT_ID: 'id', STATUS_ACCESS_CLIENT_SECRET: 'secret',
  }, async () => new Response('bad', { status: 502 })), /unavailable/);
});
