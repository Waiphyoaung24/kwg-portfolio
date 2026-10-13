// Gold M5 candidate boundary: only the runner's canonical state may leave the private origin.
import { JEV_MODEL } from './jev.js';

const SECONDS = 300, DEADLINE = 90;
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

export const QUESTION_SHA256 = sha256Hex(canonical(QUESTION));

const exactKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).sort().join() === [...keys].sort().join();

export async function m5Snapshot(feed, now = Date.now() / 1000) {
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  if (feed?.status !== 'ready' || feed.candidate !== true || !finite(feed.checked_at) ||
      now - feed.checked_at < 0 || now - feed.checked_at > 15 ||
      typeof feed.state_json !== 'string' || feed.state_json.length > 60000 ||
      typeof feed.input_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(feed.input_sha256)) throw Error('Invalid M5 feed');
  // Hash the exact published bytes: re-serialising parsed numbers would turn 4000.0 into 4000.
  if (await sha256Hex(feed.state_json) !== feed.input_sha256) throw Error('Invalid M5 input hash');
  const s = JSON.parse(feed.state_json);
  if (!exactKeys(s, ['symbol','timeframe','bar_time','captured_at','features','bars']) ||
      s.symbol !== 'XAUUSD-VIP' || s.timeframe !== 'M5' || !Array.isArray(s.bars) || s.bars.length !== 50) throw Error('Invalid M5 state');
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
      !finite(s.captured_at) || s.captured_at > now || s.captured_at < s.bar_time + SECONDS ||
      now - s.captured_at > DEADLINE) throw Error('Stale M5 candle');
  return { bar_time: s.bar_time, input_sha256: feed.input_sha256, state: s };
}

export function m5Request(snapshot) {
  return { model: JEV_MODEL, state: snapshot.state, questions: { decision: QUESTION } };
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
