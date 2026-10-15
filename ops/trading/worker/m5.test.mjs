import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {m5Snapshot, m5Request, parseM5, canonical, sha256Hex, QUESTION, QUESTION_SHA256, timing} from './src/jev-m5.js';
import {JEV_MODEL, JevObserver} from './src/jev.js';
import worker from './src/index.js';

// Printed by: cd ops/trading && python3 -B -c "import jev_m5; print(jev_m5.QUESTION_SHA256)"
const PY_QUESTION_SHA256 = 'e0a4c467d735e43a74fd7bd15b7bad168ad3b7c8af785929af7aa54bfe943e42';
// Printed by: python3 -c "import hashlib;print(hashlib.sha256('{\"bid\":4000.0,\"x\":[1.5,2]}'.encode()).hexdigest())"
const PY_FIXTURE_SHA256 = 'd01a2a1c1e81c341d047d228566dd06212ffa6aed4f0d287aa83722241ba6709';
const now = Math.floor(Date.now()/1000/300)*300+20;
const bar = now-20-300;
const state = () => ({symbol:'XAUUSD-VIP',timeframe:'M5',bar_time:bar,captured_at:now-5,
  features:{trend:'up',slope_3:'rising',price_vs_ema20:'above',volatility:'normal',spread:'tight',session:'london',
    gap_in_window:false,last_5:['up','up','down','up','up']},
  bars:Array.from({length:50},(_,i)=>({time:bar-(49-i)*300,open:4000.5,high:4001,low:3999,close:4000.25}))});
// Python sorts keys and writes integral floats as 4000.0; emulate that byte form.
const pyJson = value => canonical(value).replace(/"(open|high|low|close)":(\d+)(?=[,}])/g, '"$1":$2.0');
const hex = text => createHash('sha256').update(text, 'utf8').digest('hex');
const feed = (value = state()) => {
  const state_json = pyJson(value);
  return {status:'ready',checked_at:now,candidate:true,state_json,input_sha256:hex(state_json),bid:4000,ask:4000.1};
};

test('question hash matches Python and the question is ASCII', async () => {
  assert.equal(await QUESTION_SHA256, PY_QUESTION_SHA256);
  assert.match(canonical(QUESTION), /^[\x20-\x7e]*$/);
});

test('hash is over the exact UTF-8 string, so Python float formatting is accepted', async () => {
  assert.equal(await sha256Hex('{"bid":4000.0,"x":[1.5,2]}'), PY_FIXTURE_SHA256);
  const value = state(); value.bars[0].open = 4000; value.bars[0].close = 4000;
  const f = feed(value);
  assert.match(f.state_json, /"open":4000\.0,/);
  const s = await m5Snapshot(f, now);
  assert.equal(s.bar_time, bar); assert.equal(s.input_sha256, f.input_sha256);
  assert.equal(s.state.bars[0].open, 4000);
  assert.deepEqual(Object.keys(s).sort(), ['bar_time','input_sha256','state']);
});

test('snapshot rejects stale, malformed, mismatched or extended feeds', async () => {
  const bad = [
    f=>f.checked_at=now-16, f=>f.checked_at=now+3, f=>f.candidate=false, f=>f.status='blocked',
    f=>f.input_sha256='0'.repeat(64), f=>f.input_sha256=f.input_sha256.toUpperCase(),
    f=>f.state_json=f.state_json.replace('"tight"','"wide"'), // hash mismatch
    f=>{f.state_json=f.state_json+' '.repeat(60001); f.input_sha256=hex(f.state_json);},
    f=>{delete f.state_json;}, f=>{f.state=JSON.parse(f.state_json); delete f.state_json;},
  ];
  for (const mutate of bad) { const f=feed(); mutate(f); await assert.rejects(m5Snapshot(f, now)); }
  const badState = [
    s=>s.timeframe='M15', s=>s.symbol='BTCUSD', s=>s.features.trend='sideways', s=>s.features.session='tokyo',
    s=>s.features.last_5=['up','up','up','up'], s=>s.features.last_5[0]='rising', s=>s.features.gap_in_window='no',
    s=>s.features.extra='x', s=>delete s.features.spread, s=>s.account='omit', s=>s.bars[0].secret='omit',
    s=>s.bars.at(-1).time+=300, s=>{s.bars=s.bars.map(b=>({...b,time:b.time-300})); s.bar_time-=300;}, // stale candle
    s=>s.bars.pop(), s=>s.bars[3].time+=1, s=>s.bars[3].time=s.bars[2].time, s=>s.bars[5].high=3998,
    s=>s.bars[5].low=4000.6, s=>s.bars[5].close=NaN, s=>s.bar_time+=300, s=>s.captured_at=bar+299,
    s=>s.captured_at=now+3,
  ];
  for (const mutate of badState) { const s=state(); mutate(s); await assert.rejects(m5Snapshot(feed(s), now)); }
  // Same candle interval, but within 20 s of the 90-second decision deadline: no paid call.
  const old = state(); old.captured_at = bar+300; const late = feed(old); late.checked_at = bar+300+71;
  await assert.rejects(m5Snapshot(late, bar+300+71));
  late.checked_at = bar+300+70; assert.equal((await m5Snapshot(late, bar+300+70)).bar_time, bar);
  // Up to 2 s of clock skew between the VPS and the Worker is tolerated.
  const skew = state(); skew.captured_at = now+2; const ahead = feed(skew); ahead.checked_at = now+2;
  assert.equal((await m5Snapshot(ahead, now)).bar_time, bar);
  // Gaps are allowed when the feature says so; the grid is still required.
  const gapped = state(); gapped.bars = gapped.bars.map((b,i)=>i<10?{...b,time:b.time-600}:b); gapped.features.gap_in_window = true;
  assert.equal((await m5Snapshot(feed(gapped), now)).bar_time, bar);
});

test('request carries only the validated state and the frozen question', async () => {
  const s = await m5Snapshot(feed(), now);
  assert.deepEqual(m5Request(s), {model:JEV_MODEL,state:s.state,questions:{decision:QUESTION}});
});

test('parser enforces model, choices, probability sum, argmax and usage', () => {
  const ok = () => ({model:JEV_MODEL,usage:{input_tokens:900},answers:{decision:{type:'choice',choice:'buy',confidence:.7,
    probabilities:{buy:.7,hold:.2,sell:.1}}}});
  const parsed = parseM5(ok());
  assert.deepEqual(parsed, {choice:'buy',confidence:.7,probabilities:{buy:.7,hold:.2,sell:.1},model:JEV_MODEL,input_tokens:900});
  for (const mutate of [a=>a.model='jev-latest', a=>a.answers.decision.probabilities.buy=.9, a=>a.answers.decision.choice='hold',
      a=>a.answers.decision.choice='wait', a=>a.answers.decision.probabilities.extra=0, a=>delete a.usage,
      a=>a.usage.input_tokens=70000, a=>a.answers.decision.confidence=1.2, a=>{a.answers.observation=a.answers.decision; delete a.answers.decision;}]) {
    const a = ok(); mutate(a); assert.throws(() => parseM5(a));
  }
});

test('a candle past the 90-second decision deadline is never sent', async () => {
  const s = state(); s.captured_at = bar+300+60; const f = feed(s); f.checked_at = bar+300+91;
  await assert.rejects(m5Snapshot(f, bar+300+91));
});

const RECEIPT_KEYS = ['bar_time','completed_at','confidence','choice','input_sha256','model','probabilities','question_sha256','status'];
function memory(seed) {
  const values = new Map(seed ? [['record', seed]] : []);
  const db = {values, get: async k => structuredClone(values.get(k)), put: async (k, v) => { values.set(k, structuredClone(v)); }};
  let lock = Promise.resolve();
  db.transaction = fn => { const next = lock.then(() => fn(db)); lock = next.catch(() => {}); return next; };
  return db;
}
function harness(t, {record, provider, control, dual = false, input = feed()} = {}) {
  const clock = {t: now};
  t.mock.method(Date, 'now', () => clock.t*1000);
  t.mock.method(timing, 'sleep', async ms => { clock.t += ms/1000; });
  const db = memory(record), calls = {feed: 0, provider: 0, forwards: []};
  const env = {TYPESAFE_API_KEY:'fake-test-key', JEV_DATA_SHARING_APPROVED:'true', JEV_M5_LIVE:'true',
    STATUS_ORIGIN_URL:'https://status.example/status', STATUS_ACCESS_CLIENT_ID:'id', STATUS_ACCESS_CLIENT_SECRET:'secret',
    TRADING_CONTROL_SECRET:'control-secret'};
  env.JEV_OBSERVER = {idFromName: name => { assert.equal(name, 'gold-preview-v1'); return 'one'; }, get: () => new JevObserver({storage: db}, env)};
  const answer = {model:JEV_MODEL,usage:{input_tokens:1000},answers:{decision:{type:'choice',choice:'buy',confidence:.7,
    probabilities:{buy:.7,hold:.2,sell:.1}}}};
  t.mock.method(globalThis, 'fetch', async (target, options = {}) => {
    const url = new URL(target instanceof Request ? target.url : target);
    if (url.hostname === 'api.typesafe.ai') { calls.provider++; return provider ? provider() : Response.json(answer); }
    if (url.pathname === '/jev-m5') { if (url.search && !dual) return Response.json({status:'ready', candidate:false, bar_time:bar, checked_at:clock.t}); if (!url.search) calls.feed++; return Response.json(typeof input === 'function' ? input(url) : input); }
    if (url.pathname === '/control/jev-receipt') {
      calls.forwards.push({url, options});
      return control ? control(calls.forwards.length) : Response.json({status:'stored'}, {status:202});
    }
    throw new Error(`Unexpected fetch ${url}`);
  });
  const run = async () => { let pending = []; await worker.scheduled({}, env, {waitUntil: p => pending.push(p)}); await Promise.all(pending); };
  return {db, env, calls, run, clock};
}

test('no candidate spends nothing and forwards nothing', async t => {
  const {db, calls, run, clock} = harness(t, {input: {status:'ready', checked_at: bar+300, candidate: false, bar_time: bar}});
  clock.t = bar+300; await run();                      // current candle, no candidate: no polling retries
  assert.equal(calls.feed, 1); assert.equal(calls.provider, 0); assert.equal(calls.forwards.length, 0);
  assert.equal(db.values.get('record'), undefined);
});

test('a candidate is assessed once per candle and the receipt is forwarded exactly', async t => {
  const {db, calls, run} = harness(t, {record: {status:'ready', charged:100, attempts:3, last_sample:now, requested_at:now*1000, result:null}});
  await run(); await run();
  assert.equal(calls.provider, 1); assert.equal(calls.forwards.length, 1);
  const record = db.values.get('record');
  assert.equal(record.charged, 100 + 42);
  // M15 bookkeeping is untouched, so its one-minute cooldown neither blocks nor is blocked by M5.
  assert.deepEqual([record.attempts, record.last_sample, record.requested_at], [3, now, now*1000]);
  const {url, options} = calls.forwards[0];
  assert.equal(url.pathname, '/control/jev-receipt'); assert.equal(options.method, 'POST');
  assert.equal(options.redirect, 'manual'); assert.ok(options.signal);
  assert.equal(options.headers['X-KWG-Control-Secret'], 'control-secret');
  assert.equal(options.headers['CF-Access-Client-ID'], 'id'); assert.equal(options.headers['Content-Type'], 'application/json');
  assert.ok(options.body.length <= 1024); assert.ok(!options.body.includes('fake-test-key'));
  const body = JSON.parse(options.body);
  assert.deepEqual(Object.keys(body).sort(), [...RECEIPT_KEYS].sort());
  assert.deepEqual(body, {bar_time:bar, input_sha256:feed().input_sha256, model:JEV_MODEL, question_sha256:PY_QUESTION_SHA256,
    status:'ok', choice:'buy', confidence:.7, probabilities:{buy:.7,hold:.2,sell:.1}, completed_at:now});
  assert.equal(db.values.get(`m5:${bar}`).receipt.status, 'ok');
});

test('budget near the limit forwards budget_exhausted without a provider call', async t => {
  const {db, calls, run} = harness(t, {record: {status:'ready', charged:4_998_000, attempts:1, last_sample:0, requested_at:0, result:null}});
  await run();
  assert.equal(calls.provider, 0); assert.equal(db.values.get('record').charged, 4_998_000);
  const body = JSON.parse(calls.forwards[0].options.body);
  assert.equal(body.status, 'budget_exhausted');
  assert.deepEqual([body.choice, body.confidence, body.probabilities], [null, null, null]);
});

test('timeout keeps the reservation and forwards a timeout receipt', async t => {
  const {db, calls, run} = harness(t, {provider: () => { throw new DOMException('fake', 'TimeoutError'); }});
  await run(); await run();
  assert.equal(calls.provider, 1); assert.equal(db.values.get('record').charged, 17 + 3000);
  assert.equal(JSON.parse(calls.forwards[0].options.body).status, 'timeout');
});

test('an unparseable provider answer forwards invalid', async t => {
  const {calls, run} = harness(t, {provider: () => new Response('not json', {status: 200})});
  await run();
  assert.equal(JSON.parse(calls.forwards[0].options.body).status, 'invalid');
});

test('provider HTTP failure is unavailable', async t => {
  const {calls, run} = harness(t, {provider: () => new Response('down', {status: 502})});
  await run();
  const body = JSON.parse(calls.forwards[0].options.body);
  assert.equal(body.status, 'unavailable'); assert.equal(body.choice, null);
});

test('a busy runner (409) is retried twice; other failures are not retried', async t => {
  const busy = harness(t, {control: n => new Response('{}', {status: n < 3 ? 409 : 202})});
  await busy.run();
  assert.equal(busy.calls.forwards.length, 3);
  t.mock.restoreAll();
  const failing = harness(t, {control: () => new Response('{}', {status: 400})});
  await failing.run();
  assert.equal(failing.calls.forwards.length, 1);
});

test('missing control secret skips the forward but keeps the receipt', async t => {
  const {db, env, calls, run} = harness(t);
  delete env.TRADING_CONTROL_SECRET;
  await run();
  assert.equal(calls.provider, 1); assert.equal(calls.forwards.length, 0);
  assert.equal(db.values.get(`m5:${bar}`).receipt.status, 'ok');
});

test('JEV_M5_LIVE unset leaves the M5 branch inert', async t => {
  const {env, calls, run} = harness(t);
  delete env.JEV_M5_LIVE;
  await run();
  assert.equal(calls.feed + calls.provider + calls.forwards.length, 0);
});

test('the Durable Object refuses a candle inside the deadline margin before reserving', async t => {
  const {db, calls, clock} = harness(t);
  const snapshot = await m5Snapshot(feed(), now);
  clock.t = bar+300+71;
  const observer = new JevObserver({storage: db}, {TYPESAFE_API_KEY:'fake-test-key', JEV_DATA_SHARING_APPROVED:'true'});
  const response = await observer.fetch(new Request('https://jev.internal/m5', {method:'POST', body: JSON.stringify(snapshot)}));
  assert.ok(!response.ok); assert.equal(calls.provider, 0);
  assert.equal(db.values.get('record'), undefined); assert.equal(db.values.get(`m5:${bar}`), undefined);
});

test('behind feeds are retried briefly; a feed for the current candle without a candidate is not', async t => {
  const close = bar+300;
  const behind = {status:'ready', checked_at: close-5, candidate:false, bar_time: bar-300};
  const h = harness(t, {input: () => behind});
  h.clock.t = close; await h.run();                    // polls once a second for the first 20 s
  assert.equal(h.calls.feed, 20);
  h.clock.t = close+25; await h.run();                 // too late in the candle to keep polling
  assert.equal(h.calls.feed, 21);
});

test('a candidate published 12 s after close is captured by the first cron', async t => {
  const close = bar+300, value = state(); value.captured_at = close+12;
  const published = feed(value);
  let h;
  h = harness(t, {input: () => h.clock.t < close+12
    ? {status:'ready', checked_at: close-50, candidate:false, bar_time: bar-300}
    : {...published, checked_at: Math.floor(h.clock.t)}});
  h.clock.t = close; await h.run();
  assert.equal(h.calls.feed, 13); assert.equal(h.calls.provider, 1); assert.equal(h.calls.forwards.length, 1);
});

test('a candidate published after the polling window is assessed by a later cron exactly once', async t => {
  const close = bar+300, value = state(); value.captured_at = close+25;
  const published = feed(value);
  let h;
  h = harness(t, {input: () => h.clock.t < close+25
    ? {status:'ready', checked_at: close-50, candidate:false, bar_time: bar-300}
    : {...published, checked_at: Math.floor(h.clock.t)}});             // the runner refreshes checked_at each poll
  h.clock.t = close; await h.run();                                     // reads at close+0..19 all miss
  assert.equal(h.calls.feed, 20); assert.equal(h.calls.provider, 0); assert.equal(h.db.values.get('record'), undefined);
  h.clock.t = close+60; await h.run();
  assert.equal(h.calls.provider, 1); assert.equal(h.calls.forwards.length, 1);
  assert.equal(h.db.values.get('record').charged, 17+42);
  h.clock.t = close+65; await h.run();
  assert.equal(h.calls.provider, 1); assert.equal(h.calls.forwards.length, 1);
  assert.equal(h.db.values.get('record').charged, 17+42);
});

test('M5 scorecard route requires the owner and passes the origin report through uncached', async t => {
  const original = globalThis.fetch;
  t.after(() => { globalThis.fetch = original; });
  const env = { ALLOWED_VIEWER_EMAIL: 'owner@example.com', STATUS_ORIGIN_URL: 'https://origin.example/status',
    STATUS_ACCESS_CLIENT_ID: 'id', STATUS_ACCESS_CLIENT_SECRET: 'secret' };
  const as = email => ({ access: { getIdentity: async () => ({ email }) } });
  const url = 'https://site/api/trading/jev-m5-scorecard';
  const body = JSON.stringify({ status: 'ready', generated_at: 1, candidates: 0 });
  let origin = () => new Response(body, { headers: { 'Content-Type': 'application/json' } }), calls = [];
  globalThis.fetch = async (target, options) => { calls.push([String(target), options]); return origin(); };
  assert.equal((await worker.fetch(new Request(url), env, {})).status, 403);
  assert.equal((await worker.fetch(new Request(url), env, as('other@example.com'))).status, 403);
  assert.equal((await worker.fetch(new Request(url, { method: 'POST' }), env, as('owner@example.com'))).status, 404);
  assert.equal((await worker.fetch(new Request(url + '?symbol=ETHUSD'), env, as('owner@example.com'))).status, 400);
  assert.equal(calls.length, 0);
  const response = await worker.fetch(new Request(url), env, as('owner@example.com'));
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(await response.text(), body);
  assert.equal(calls[0][0], 'https://origin.example/jev-m5-scorecard');
  assert.equal(calls[0][1].headers['CF-Access-Client-Secret'], 'secret');
  assert.equal(calls[0][1].redirect, 'manual');
  origin = () => Response.json({status:'ready', symbol:'BTCUSD', candidates:3});
  const btcResponse = await worker.fetch(new Request(url + '?symbol=BTCUSD'), env, as('owner@example.com'));
  assert.equal(btcResponse.status, 200);
  assert.deepEqual(await btcResponse.json(), {status:'ready', symbol:'BTCUSD', candidates:3});
  assert.equal(calls[1][0], 'https://origin.example/jev-m5-scorecard?symbol=BTCUSD');
  for (const failure of [() => new Response('', { status: 503 }), () => new Response('<html>', { headers: { 'Content-Type': 'text/html' } }),
    () => new Response('x'.repeat(65537), { headers: { 'Content-Type': 'application/json' } }),
    () => new Response('not json', { headers: { 'Content-Type': 'application/json' } })]) {
    origin = failure;
    const failed = await worker.fetch(new Request(url), env, as('owner@example.com'));
    assert.equal(failed.status, 503);
    assert.equal(failed.headers.get('Cache-Control'), 'no-store');
    assert.equal((await failed.json()).status, 'unavailable');
  }
});

test('BTC snapshot and question are isolated from Gold', async () => {
  const btc = feed({...state(), symbol:'BTCUSD'});
  const snapshot = await m5Snapshot(btc, now, 'BTCUSD');
  assert.equal(m5Request(snapshot).questions.decision.instructions, QUESTION.instructions.replace('Gold M5', 'BTC M5'));
  await assert.rejects(m5Snapshot(btc, now));
  await assert.rejects(m5Snapshot(feed(), now, 'BTCUSD'));
  await assert.rejects(m5Snapshot(btc, now, 'ETHUSD'));
});

test('both symbols share the historical ledger but deduplicate independently', async t => {
  const h = harness(t, {dual:true, input: url => feed({...state(), symbol: url.searchParams.get('symbol') ?? 'XAUUSD-VIP'})});
  await h.run(); await h.run();
  assert.equal(h.calls.provider, 2);
  assert.equal(h.db.values.get('record').charged, 17+42+42);
  assert.equal(h.calls.forwards.length, 2);
  const receipts = h.calls.forwards.map(x=>JSON.parse(x.options.body));
  assert.equal(receipts.filter(x=>x.symbol === undefined).length, 1);
  const btc = receipts.find(x=>x.symbol === 'BTCUSD');
  assert.equal(btc.question_sha256, hex(canonical({...QUESTION, instructions:QUESTION.instructions.replace('Gold M5','BTC M5')})));
  assert.equal(h.db.values.get(`m5:${bar}`).receipt.status, 'ok');
  assert.equal(h.db.values.get(`m5:BTCUSD:${bar}`).receipt.status, 'ok');
});

test('concurrent symbols cannot spend past the one shared budget', async t => {
  const h = harness(t, {dual:true, record:{status:'ready',charged:4_995_000,attempts:0,last_sample:0,requested_at:0,result:null},
    input: url=>feed({...state(),symbol:url.searchParams.get('symbol') ?? 'XAUUSD-VIP'}),
    provider:()=>{throw new DOMException('timeout','TimeoutError');}});
  await h.run(); await h.run();
  assert.equal(h.calls.provider, 1);
  assert.equal(h.db.values.get('record').charged, 4_998_000);
  assert.deepEqual(h.calls.forwards.map(x=>JSON.parse(x.options.body).status).sort(), ['budget_exhausted','timeout']);
});

test('historic Gold reservation survives rollout while BTC can assess the same candle', async t => {
  const h = harness(t, {dual:true, input:url=>feed({...state(),symbol:url.searchParams.get('symbol') ?? 'XAUUSD-VIP'})});
  h.db.values.set(`m5:${bar}`, {status:'running',requested_at:now*1000});
  await h.run();
  assert.equal(h.calls.provider, 1);
  assert.equal(h.calls.forwards.length, 1);
  assert.equal(JSON.parse(h.calls.forwards[0].options.body).symbol, 'BTCUSD');
  assert.equal(h.db.values.get(`m5:${bar}`).status, 'running');
});
