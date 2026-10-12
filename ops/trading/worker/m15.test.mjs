import test from 'node:test';
import assert from 'node:assert/strict';
import {m15Snapshot} from './src/jev-m15.js';
import {JevObserver,JEV_MODEL} from './src/jev.js';
import worker from './src/index.js';
const now = Math.floor(Date.now()/900)*900+2;
const feed = () => ({status:'ready',checked_at:now,sample:{symbol:'XAUUSD-VIP',timeframe:'M15',captured_at:now,
  bars:Array.from({length:250},(_,i)=>({time:now-2-(250-i)*900,open:4000,high:4001,low:3999,close:4000,secret:'omit'})),
  bid:4000,ask:4000.1,signal:'long',eligible:true,slope_pass:false,indicators:{ema20:4000,ema50:3999,atr14:2},
  costs:{commission:7,slippage:.1,overnight:15,spread_multiplier:1.5},
  specification:{point:.01,trade_contract_size:100,trade_tick_size:.01,volume_min:.01,volume_max:100,volume_step:.01},account:'omit'}});
test('M15 boundary rejects stale, future, malformed bars and strips unrelated fields',()=>{
  const s=m15Snapshot(feed(),now);
  assert.equal(s.slope_pass,false); assert.equal(s.account,undefined); assert.equal(s.bars[0].secret,undefined);
  for(const mutate of [f=>f.checked_at=now-16,f=>f.sample.timeframe='M1',f=>f.sample.bars[0].high=0,
    f=>f.sample.indicators.atr14=NaN,f=>f.sample.bars.at(-1).time+=900]) {
    const f=feed(); mutate(f); assert.throws(()=>m15Snapshot(f,now));
  }
});
test('M15 uses existing spend ledger, persists receipt and cannot repeat the same candle',async t=>{
  const values=new Map([['record',{charged:4995000,attempts:10,last_sample:0,requested_at:0}]]);
  const storage={get:async k=>structuredClone(values.get(k)),put:async(k,v)=>values.set(k,structuredClone(v))};
  storage.transaction=fn=>fn(storage);
  const old=globalThis.fetch; let calls=0;
  globalThis.fetch=async()=>{calls++;return Response.json({model:JEV_MODEL,usage:{input_tokens:1000},answers:{observation:{
    type:'choice',choice:'review_setup',confidence:.6,probabilities:{review_setup:.6,wait:.3,insufficient_data:.1}}}});};
  t.after(()=>globalThis.fetch=old);
  const observer=new JevObserver({storage},{TYPESAFE_API_KEY:'test',JEV_DATA_SHARING_APPROVED:'true'});
  const s=m15Snapshot(feed(),now);
  const req=()=>new Request('https://internal/',{method:'POST',body:JSON.stringify(s)});
  await observer.fetch(req());
  assert.equal(values.get('record').charged,4995042);
  assert.equal(values.get(`m15:${s.bar_time}`).result.decision,'review_setup');
  assert.equal((await observer.fetch(req())).status,429); assert.equal(calls,1);
});
test('schedule sends fresh baseline setups before slope filtering and skips late or absent setups',async t=>{
  t.mock.method(Date,'now',()=>now*1000);
  let input=feed(), paid=0, pending;
  t.mock.method(globalThis,'fetch',async()=>Response.json(input));
  const observer={fetch:async request=>{
    if(request.method==='POST') { paid++; return Response.json({status:'connected',attempts:2}); }
    return Response.json({status:'connected',attempts:1});
  }};
  const env={TYPESAFE_API_KEY:'test',JEV_DATA_SHARING_APPROVED:'true',JEV_M15_LIVE:'true',
    STATUS_ORIGIN_URL:'https://status.example/status',JEV_OBSERVER:{idFromName:()=>'',get:()=>observer}};
  const run=async()=>{await worker.scheduled({},env,{waitUntil:p=>pending=p});await pending;};
  await run(); assert.equal(paid,1); // slope_pass is false; baseline eligibility controls observation.
  input.sample.eligible=false; await run(); assert.equal(paid,1);
  input.sample.eligible=true; input.sample.captured_at=now-16;
  // Use an instant later in the same completed-candle interval to test the decision deadline.
  t.mock.method(Date,'now',()=>(now+20)*1000); input.checked_at=now+20; input.sample.captured_at=now;
  await run(); assert.equal(paid,1);
});
