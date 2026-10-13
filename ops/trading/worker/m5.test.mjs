import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {m5Snapshot, m5Request, parseM5, canonical, sha256Hex, QUESTION, QUESTION_SHA256} from './src/jev-m5.js';
import {JEV_MODEL} from './src/jev.js';

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
    f=>f.checked_at=now-16, f=>f.checked_at=now+1, f=>f.candidate=false, f=>f.status='blocked',
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
    s=>s.captured_at=now+1,
  ];
  for (const mutate of badState) { const s=state(); mutate(s); await assert.rejects(m5Snapshot(feed(s), now)); }
  // Same candle interval, but the capture is older than the 90-second decision window.
  const old = state(); old.captured_at = bar+300; const late = feed(old); late.checked_at = bar+300+91;
  await assert.rejects(m5Snapshot(late, bar+300+91));
  late.checked_at = bar+300+90; assert.equal((await m5Snapshot(late, bar+300+90)).bar_time, bar);
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
