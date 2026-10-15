// Gold M5 candidate boundary: only the runner's canonical state may leave the private origin.
import { JEV_MODEL } from './jev.js';

const SECONDS = 300, DEADLINE = 90, SKEW = 2;
// Leave 20 s of the runner's 90-second deadline for the provider call and the receipt forward.
export const LATEST = SECONDS + DEADLINE - 20;
const CHOICES = ['buy', 'hold', 'sell'];
// Byte-identical to ops/trading/jev_m5.py QUESTION; a test pins the Python digest.
export const QUESTION = {type:'choice',
  instructions:'Using only the supplied Gold M5 state at captured_at, choose whether conditions '+
    'favour a long entry, a short entry, or no entry now. Do not infer missing data. '+
    'Ordinary code owns all risk, sizing and execution; this is a demo assessment.',
  criteria:{buy:'Conditions favour a long entry now.',
    hold:'No clear edge, or the evidence conflicts.',
    sell:'Conditions favour a short entry now.'}};
const FEATURES = {trend:['up','down','flat'], slope_3:['rising','falling','mixed'], price_vs_ema20:['below','at','above'],
  volatility:['low','normal','high'], spread:['tight','normal','wide'], session:['asia','london','overlap','new_york']};

// Python json.dumps(sort_keys=True, separators=(',',':')); only safe for ASCII strings and no floats.
export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(k=>`${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}

export async function sha256Hex(text) {
  const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text)));
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
}

export const BTC_QUESTION = {...QUESTION, instructions: QUESTION.instructions.replace('Gold M5', 'BTC M5')};
export const QUESTION_SHA256 = sha256Hex(canonical(QUESTION));
export const BTC_QUESTION_SHA256 = sha256Hex(canonical(BTC_QUESTION));
const validSymbol = symbol => ['XAUUSD-VIP', 'BTCUSD'].includes(symbol);

const exactKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).sort().join() === [...keys].sort().join();

export async function m5Snapshot(feed, now = Date.now() / 1000, symbol = 'XAUUSD-VIP') {
  if (!validSymbol(symbol)) throw Error('Invalid M5 symbol');
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  if (feed?.status !== 'ready' || feed.candidate !== true || !finite(feed.checked_at) ||
      now - feed.checked_at < -SKEW || now - feed.checked_at > 15 ||
      typeof feed.state_json !== 'string' || feed.state_json.length > 60000 ||
      typeof feed.input_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(feed.input_sha256)) throw Error('Invalid M5 feed');
  // Hash the exact published bytes: re-serialising parsed numbers would turn 4000.0 into 4000.
  if (await sha256Hex(feed.state_json) !== feed.input_sha256) throw Error('Invalid M5 input hash');
  const s = JSON.parse(feed.state_json);
  if (!exactKeys(s, ['symbol','timeframe','bar_time','captured_at','features','bars']) ||
      s.symbol !== symbol || s.timeframe !== 'M5' || !Array.isArray(s.bars) || s.bars.length !== 50) throw Error('Invalid M5 state');
  s.bars.forEach((b, i) => {
    if (!exactKeys(b, ['time','open','high','low','close']) || !Number.isInteger(b.time) || b.time <= 0 || b.time % SECONDS ||
        (i && b.time <= s.bars[i-1].time) || !['open','high','low','close'].every(k => finite(b[k]) && b[k] > 0 && b[k] <= 1e6) ||
        b.high < Math.max(b.open, b.close, b.low) || b.low > Math.min(b.open, b.close)) throw Error('Invalid M5 candle');
  });
  const f = s.features;
  if (!exactKeys(f, [...Object.keys(FEATURES), 'last_5', 'gap_in_window']) ||
      !Object.entries(FEATURES).every(([k, names]) => names.includes(f[k])) || typeof f.gap_in_window !== 'boolean' ||
      !Array.isArray(f.last_5) || f.last_5.length !== 5 || !f.last_5.every(x => ['up','down','flat'].includes(x))) throw Error('Invalid M5 features');
  if (s.bar_time !== Math.floor(now / SECONDS) * SECONDS - SECONDS || s.bars.at(-1).time !== s.bar_time ||
      !finite(s.captured_at) || s.captured_at > now + SKEW || s.captured_at < s.bar_time + SECONDS ||
      now - s.captured_at > DEADLINE || now > s.bar_time + LATEST) throw Error('Stale M5 candle');
  return { bar_time: s.bar_time, input_sha256: feed.input_sha256, state: s };
}

export function m5Request(snapshot) {
  if (!validSymbol(snapshot.state?.symbol)) throw Error('Invalid M5 symbol');
  return { model: JEV_MODEL, state: snapshot.state, questions: { decision: snapshot.state.symbol === 'BTCUSD' ? BTC_QUESTION : QUESTION } };
}

export function parseM5(value) {
  const a = value?.answers?.decision, p = a?.probabilities;
  const unit = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1;
  if (value?.model !== JEV_MODEL || a?.type !== 'choice' || !CHOICES.includes(a.choice) || !unit(a.confidence) ||
      !exactKeys(p, CHOICES) || !CHOICES.every(k => unit(p[k])) ||
      Math.abs(CHOICES.reduce((sum, k) => sum + p[k], 0) - 1) > .001 ||
      // The runner rejects a receipt whose choice is not the strict most probable answer.
      !CHOICES.every(k => k === a.choice || p[k] < p[a.choice]) ||
      !Number.isInteger(value.usage?.input_tokens) || value.usage.input_tokens <= 0 || value.usage.input_tokens > 65536) {
    throw new Error('Invalid Jev M5 response');
  }
  return { choice: a.choice, confidence: a.confidence, probabilities: { buy: p.buy, hold: p.hold, sell: p.sell },
    model: value.model, input_tokens: value.usage.input_tokens };
}

export const RECEIPT_KEYS = ['bar_time', 'input_sha256', 'model', 'question_sha256', 'status',
  'choice', 'confidence', 'probabilities', 'completed_at'];
export const timing = { sleep: ms => new Promise(resolve => setTimeout(resolve, ms)) }; // Test seam.
const accessHeaders = env => ({ 'CF-Access-Client-ID': env.STATUS_ACCESS_CLIENT_ID,
  'CF-Access-Client-Secret': env.STATUS_ACCESS_CLIENT_SECRET });

function origin(env, pathname, symbol = 'XAUUSD-VIP') {
  const url = new URL(env.STATUS_ORIGIN_URL);
  if (url.protocol !== 'https:') throw Error('Invalid origin');
  url.pathname = pathname; url.search = '';
  if (symbol === 'BTCUSD') url.searchParams.set('symbol', symbol);
  return url;
}

// error.retry marks a feed that may still catch up: origin failure or a feed behind the current candle.
export async function readM5(env, now = Date.now() / 1000, symbol = 'XAUUSD-VIP') {
  if (!validSymbol(symbol)) throw Error('Invalid M5 symbol');
  let response;
  try {
    response = await fetch(origin(env, '/jev-m5', symbol), { headers: accessHeaders(env), redirect: 'manual',
      signal: AbortSignal.timeout(5000) });
  } catch { throw Object.assign(Error('M5 origin unreachable'), { retry: true }); }
  if (!response.ok) throw Object.assign(Error(`M5 origin HTTP ${response.status}`), { retry: true });
  const feed = await response.json();
  try { return await m5Snapshot(feed, now, symbol); } catch (error) {
    error.retry = !(Number.isInteger(feed?.bar_time) && feed.bar_time >= Math.floor(now / SECONDS) * SECONDS - SECONDS);
    throw error;
  }
}

// The runner fails closed without a receipt, so a lost forward only loses this candle.
export async function forwardReceipt(env, receipt) {
  if (!env.TRADING_CONTROL_SECRET) { console.warn('Jev M5 receipt not forwarded: control secret missing.'); return false; }
  if (receipt.symbol !== undefined && receipt.symbol !== 'BTCUSD') throw Error('Invalid M5 receipt symbol');
  const keys = receipt.symbol === 'BTCUSD' ? [...RECEIPT_KEYS, 'symbol'] : RECEIPT_KEYS;
  const body = JSON.stringify(Object.fromEntries(keys.map(k => [k, receipt[k]])));
  if (body.length > 1024) throw Error('Invalid M5 receipt size');
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await fetch(origin(env, '/control/jev-receipt'), { method: 'POST',
      headers: { ...accessHeaders(env), 'X-KWG-Control-Secret': env.TRADING_CONTROL_SECRET, 'Content-Type': 'application/json' },
      body, redirect: 'manual', signal: AbortSignal.timeout(5000) });
    if ([200, 202].includes(response.status)) return true;
    if (response.status !== 409 || attempt === 2) { console.warn('Jev M5 receipt forward failed', response.status); return false; }
    await timing.sleep(1000); // 409: the control server is busy with another action.
  }
}

export async function runM5(env, symbol = 'XAUUSD-VIP') {
  try {
    let snapshot;
    // Poll once a second through the first 20 s of the candle while the feed is behind (hard cap 20 reads).
    for (let attempt = 0; attempt < 20; attempt++) {
      try { snapshot = await readM5(env, Date.now() / 1000, symbol); break; } catch (error) {
        if (!error.retry || attempt === 19 || (Date.now() / 1000) % SECONDS >= 20) {
          console.info('Jev M5: no fresh candidate; nothing spent.', /^(Invalid|Stale|M5 origin)/.test(error.message) ? error.message : error.name);
          return;
        }
        await timing.sleep(1000); // Read-only polling while the runner publishes the candle.
      }
    }
    const observer = env.JEV_OBSERVER.get(env.JEV_OBSERVER.idFromName('gold-preview-v1'));
    const response = await observer.fetch(new Request('https://jev.internal/m5', { method: 'POST', body: JSON.stringify(snapshot) }));
    if (response.status === 409) return; // This candle already has its one paid call.
    if (!response.ok) { console.warn('Jev M5 observer refused', response.status); return; }
    const receipt = await response.json();
    console.info('Jev M5 receipt', JSON.stringify({ bar_time: receipt.bar_time, status: receipt.status,
      choice: receipt.choice, confidence: receipt.confidence }));
    await forwardReceipt(env, receipt);
  } catch (error) {
    console.warn('Jev M5 run failed; no paid retry.', /^(Invalid|Stale|M5 origin)/.test(error.message) ? error.message : error.name);
  }
}
