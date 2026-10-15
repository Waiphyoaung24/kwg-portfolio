import { scorecard } from './jev-scorecard.js';
import { LATEST, m5Request, parseM5, QUESTION_SHA256, BTC_QUESTION_SHA256 } from './jev-m5.js';
export const JEV_MODEL = 'jev-1.13.0';
const LIMIT = 5_000_000; // USD microdollars, including the earlier 17-microdollar smoke test.
const RESERVE = 3_000; // Covers 65,536 input tokens at the pinned $0.042/M price; output is free.
const headers = { 'Cache-Control': 'no-store' };
const json = (value, status = 200) => Response.json(value, { status, headers });
const initial = () => ({ status: 'ready', charged: 17, attempts: 0, last_sample: 0, requested_at: 0, result: null });

export function jevSnapshot(report, now = Date.now() / 1000) {
  const h = report.health;
  if (report.symbol !== 'XAUUSD-VIP' || report.status === 'offline' ||
      !Number.isInteger(report.checked_at) || report.checked_at > now || now - report.checked_at > 30 ||
      h?.terminal !== 'connected' || h.quote !== 'fresh' ||
      !Number.isFinite(h.quote_age_seconds) || h.quote_age_seconds < 0 || h.quote_age_seconds > 30 ||
      ![h.bid, h.ask].every(x => typeof x === 'number' && Number.isFinite(x) && x > 0 && x <= 1e6) || h.ask < h.bid) {
    throw new Error('Fresh Gold market data is unavailable.');
  }
  const timeframe = report.pilot ? (report.pilot.strategy.includes('-m1-') ? 'M1' : 'M15') : 'M15';
  // Only these fields leave the Worker; no account, position, P/L, free-text reason or credentials.
  return { symbol: 'XAUUSD-VIP', timeframe, checked_at: report.checked_at,
    bid: h.bid, ask: h.ask, signal: report.signal, strategy_status: report.status,
    missing: 'No candle values, indicators, proposed trade or verified costs. This is a snapshot assessment, not a profitability forecast.' };
}

export function jevRequest(snapshot) {
  if (snapshot.bars) return {model:JEV_MODEL,state:snapshot,questions:{observation:{type:'choice',
    instructions:'For this Gold M15 baseline crossover, estimate whether a hypothetical trade closes positive after the supplied modeled costs. Long uses ask, short bid, stop 2 ATR, target 3 ATR; opposite crossover closes it. If eligible is false or signal is none, select insufficient_data. No orders. Costs and fill latency are unverified. Do not infer missing information.',
    criteria:{wait:'Forecast nonpositive net modeled outcome.',insufficient_data:'No eligible setup or insufficient evidence.',review_setup:'Forecast positive net modeled outcome; observation only.'}}}};
  return { model: JEV_MODEL, state: snapshot, questions: { observation: { type: 'choice',
    instructions: 'Assess this snapshot at checked_at, not at request time. Never infer missing candles or indicators. A blocked or baseline strategy requires wait. Otherwise missing candles, indicators, trade levels or costs require insufficient_data. Only select review_setup when all of those inputs are supplied. This is observation only; ordinary code owns all execution guards.',
    criteria: { wait: 'An explicit entry guard or startup baseline requires waiting.',
      insufficient_data: 'Inputs are insufficient to assess a proposed trade.',
      review_setup: 'Inputs support reviewing a setup, not authorizing a trade.' } } } };
}

export function parseJev(value) {
  const a = value?.answers?.observation;
  const keys = ['wait', 'insufficient_data', 'review_setup'];
  if (value?.model !== JEV_MODEL || a?.type !== 'choice' || !keys.includes(a.choice) ||
      typeof a.confidence !== 'number' || !Number.isFinite(a.confidence) || a.confidence < 0 || a.confidence > 1 ||
      !a.probabilities || Object.keys(a.probabilities).sort().join() !== keys.sort().join() ||
      !keys.every(k => typeof a.probabilities[k] === 'number' && Number.isFinite(a.probabilities[k]) && a.probabilities[k] >= 0 && a.probabilities[k] <= 1) ||
      Math.abs(keys.reduce((sum, k) => sum + a.probabilities[k], 0) - 1) > .001 ||
      !Number.isInteger(value.usage?.input_tokens) || value.usage.input_tokens <= 0 || value.usage.input_tokens > 65536) {
    throw new Error('Invalid Jev response');
  }
  return { decision: a.choice, confidence: a.confidence, probabilities: a.probabilities,
    model: value.model, input_tokens: value.usage.input_tokens,
    cost_usd: value.usage.input_tokens * .042 / 1e6 };
}

export function jevEnabled(env) {
  return Boolean(env.TYPESAFE_API_KEY && env.JEV_DATA_SHARING_APPROVED === 'true');
}

export class JevObserver {
  constructor(ctx, env) { this.storage = ctx.storage; this.env = env; }

  async fetch(request) {
    if (new URL(request.url).pathname === '/scorecard' && request.method === 'POST') {
      const report = await request.json(); // Internal binding, after owner authentication.
      const result = await scorecard(report, stamp => this.storage.get(`m15:${stamp}`));
      const record = await this.storage.get('record') ?? initial();
      return json({ ...result, accounted_usd: record.charged / 1e6, budget_usd: 5 });
    }
    if (!jevEnabled(this.env)) return json({ status: 'not_configured', message: 'Jev observation is not enabled.', budget_usd: 5 });
    if (new URL(request.url).pathname === '/m5' && request.method === 'POST') return this.m5(await request.json());
    if (request.method === 'GET') {
      const record = await this.storage.get('record') ?? initial();
      if (record.status === 'running' && Date.now() - record.requested_at > 30000) {
        record.status = 'unavailable'; record.message = 'Jev request was interrupted. No automatic retry.';
      }
      return json(this.view(record));
    }
    if (request.method !== 'POST') return json({ status: 'unavailable' }, 405);
    const snapshot = await request.json(); // Internal binding only; the Worker constructs this allowlisted snapshot.
    const body = JSON.stringify(jevRequest(snapshot));
    if (body.length > 64000) return json({ status: 'unavailable', message: 'Snapshot too large.' }, 400);
    const now = Date.now();
    const reserved = await this.storage.transaction(async tx => {
      const record = await tx.get('record') ?? initial();
      if (snapshot.bars && await tx.get(`m15:${snapshot.bar_time}`)) return {denied:'cooldown',record};
      if (record.last_sample >= snapshot.checked_at || now - record.requested_at < 60000) return { denied: 'cooldown', record };
      if (record.charged + RESERVE > LIMIT) return { denied: 'budget_exhausted', record };
      Object.assign(record, { status: 'running', message: '', result: null, snapshot,
        last_sample: snapshot.checked_at, requested_at: now, charged: record.charged + RESERVE, attempts: record.attempts + 1 });
      await tx.put('record', record);
      if (snapshot.bars) await tx.put(`m15:${snapshot.bar_time}`, {status:'running',snapshot,questions:jevRequest(snapshot).questions,model:JEV_MODEL,requested_at:now});
      return { record };
    });
    if (reserved.denied) return json({ ...this.view(reserved.record), status: reserved.denied,
      message: reserved.denied === 'cooldown' ? 'Wait one minute and use a new snapshot. No request sent.' : 'The $5 Jev budget is exhausted. No request sent.' }, 429);
    let result = null, status = 'unavailable', message = 'Jev is unavailable. No automatic retry.';
    try {
      const response = await fetch('https://api.typesafe.ai/v1/systemone', {
        method: 'POST', headers: { Authorization: `Bearer ${this.env.TYPESAFE_API_KEY}`, 'Content-Type': 'application/json' },
        body, redirect: 'manual', signal: AbortSignal.timeout(15000),
      });
      if (!response.ok) throw new Error('Provider unavailable');
      result = { ...parseJev(await response.json()), latency_ms: Date.now() - now, completed_at: Date.now() };
      status = 'connected'; message = 'Snapshot assessed. No orders sent.';
    } catch (error) {
      if (['TimeoutError', 'AbortError'].includes(error.name)) { status = 'timeout'; message = 'Jev timed out. No automatic retry.'; }
    }
    const record = await this.storage.transaction(async tx => {
      const value = await tx.get('record');
      if (value.requested_at === now) {
        Object.assign(value, { status, message, result });
        // Unknown outcomes retain the entire reservation, so timeouts cannot overspend the cap.
        if (result) value.charged -= RESERVE - Math.ceil(result.input_tokens * .042);
        await tx.put('record', value);
        if (snapshot.bars) await tx.put(`m15:${snapshot.bar_time}`, {status,message,snapshot,questions:jevRequest(snapshot).questions,model:JEV_MODEL,result,requested_at:now});
      }
      return value;
    });
    return json(this.view(record), result ? 200 : 503);
  }

  // One paid call per symbol per M5 candle. Shares only the spend ledger with M15, never its cooldown fields.
  async m5(snapshot) {
    const symbol = snapshot.state?.symbol;
    if (!['XAUUSD-VIP', 'BTCUSD'].includes(symbol)) return json({ status: 'invalid' }, 400);
    // Preserve historical Gold reservations so a deployment cannot replay a paid candle.
    const key = symbol === 'BTCUSD' ? `m5:BTCUSD:${snapshot.bar_time}` : `m5:${snapshot.bar_time}`;
    const body = JSON.stringify(m5Request(snapshot));
    if (body.length > 64000) return json({ status: 'unavailable', message: 'Snapshot too large.' }, 400);
    const question_sha256 = await (symbol === 'BTCUSD' ? BTC_QUESTION_SHA256 : QUESTION_SHA256), now = Date.now();
    if (now / 1000 > snapshot.bar_time + LATEST) return json({ status: 'too_late', message: 'Too close to the Jev deadline. No request sent.' }, 400);
    const receipt = (status, result = null) => ({ ...(symbol === 'BTCUSD' ? {symbol} : {}), bar_time: snapshot.bar_time, input_sha256: snapshot.input_sha256,
      model: JEV_MODEL, question_sha256, status, choice: result?.choice ?? null, confidence: result?.confidence ?? null,
      probabilities: result?.probabilities ?? null, completed_at: Date.now() / 1000 });
    const reserved = await this.storage.transaction(async tx => {
      if (await tx.get(key)) return { duplicate: true };
      const record = await tx.get('record') ?? initial();
      if (record.charged + RESERVE > LIMIT) {
        const final = receipt('budget_exhausted');
        await tx.put(key, { status: final.status, receipt: final, requested_at: now });
        return { final };
      }
      record.charged += RESERVE;
      await tx.put('record', record);
      await tx.put(key, { status: 'running', input_sha256: snapshot.input_sha256, requested_at: now });
      return {};
    });
    if (reserved.duplicate) return json({ status: 'duplicate', message: 'This candle was already assessed. No request sent.' }, 409);
    if (reserved.final) return json(reserved.final);
    let result = null, status = 'unavailable';
    try {
      const response = await fetch('https://api.typesafe.ai/v1/systemone', {
        method: 'POST', headers: { Authorization: `Bearer ${this.env.TYPESAFE_API_KEY}`, 'Content-Type': 'application/json' },
        body, redirect: 'manual', signal: AbortSignal.timeout(15000),
      });
      if (!response.ok) throw new Error('Provider unavailable');
      try { result = parseM5(await response.json()); status = 'ok'; } catch { status = 'invalid'; }
    } catch (error) {
      if (['TimeoutError', 'AbortError'].includes(error.name)) status = 'timeout';
    }
    const final = receipt(status, result);
    await this.storage.transaction(async tx => {
      const record = await tx.get('record');
      // As for M15: only a parsed usage figure refunds; unknown outcomes keep the whole reservation.
      if (result) { record.charged -= RESERVE - Math.ceil(result.input_tokens * .042); await tx.put('record', record); }
      await tx.put(key, { status, receipt: final, input_tokens: result?.input_tokens ?? null, requested_at: now });
    });
    return json(final);
  }

  view(record) {
    const exhausted = record.status !== 'running' && record.charged + RESERVE > LIMIT;
    return { ...record, ...(exhausted ? { status: 'budget_exhausted', message: 'The $5 Jev budget cannot cover another request. No request sent.' } : {}),
      budget_usd: 5, accounted_usd: record.charged / 1e6,
      remaining_usd: (LIMIT - record.charged) / 1e6 };
  }
}
