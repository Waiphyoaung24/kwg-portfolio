import { m15Snapshot } from './jev-m15.js';
import { jevRequest, JEV_MODEL, parseJev } from './jev.js';

const canonical = value => JSON.stringify(value, function (_key, item) {
  return item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(k => [k, item[k]])) : item;
});
const hash = async value => [...new Uint8Array(await crypto.subtle.digest('SHA-256',
  new TextEncoder().encode(canonical(value))))].map(x => x.toString(16).padStart(2, '0')).join('');
const market = ({ checked_at, ...snapshot }) => snapshot;
const finite = x => typeof x === 'number' && Number.isFinite(x);
const count = x => Number.isInteger(x) && x >= 0;

export async function scorecard(report, receiptFor, now = Date.now() / 1000) {
  if (report?.version !== 1 || report.status !== 'ready' || report.qualification !== 'unqualified_diagnostic' ||
      !finite(report.generated_at) || now - report.generated_at < 0 || now - report.generated_at > 120 ||
      !count(report.samples) || !count(report.gaps) || !/^[a-f0-9]{64}$/.test(report.journal_config_sha256) ||
      (report.last_bar !== null && (!count(report.last_bar) || report.last_bar + 900 > now)) ||
      !Array.isArray(report.outcomes) || report.outcomes.length > 200) throw Error('Invalid outcome report');
  const seen = new Set(), outcomes = [];
  for (const row of report.outcomes) {
    const s = row.sample;
    if (!s?.eligible || !['long', 'short'].includes(s.signal) || !count(row.bar_time) ||
        seen.has(row.bar_time) || row.bar_time > report.last_bar || !/^[a-f0-9]{64}$/.test(s.input_sha256) ||
        !['resolved', 'pending', 'no_fill', 'censored_gap', 'censored_missing_predecessor'].includes(row.outcome)) throw Error('Invalid outcome');
    seen.add(row.bar_time);
    const snapshot = m15Snapshot({ status: 'ready', checked_at: s.captured_at, sample: s }, s.captured_at);
    if (snapshot.bar_time !== row.bar_time || s.captured_at > row.bar_time + 930) throw Error('Invalid capture');
    const net = row.outcome === 'resolved' ? row.trade?.net_pnl : null;
    if (row.outcome === 'resolved' && (!finite(net) || Math.abs(net) > 1e9 ||
        !count(row.trade.exit_bar) || row.trade.exit_bar < row.bar_time || row.trade.exit_bar > report.last_bar ||
        row.trade.exit_reason === 'window_end')) throw Error('Invalid resolved outcome');
    const receipt = await receiptFor(row.bar_time);
    const questions = jevRequest(snapshot).questions;
    let response = 'missing', decision = null, probabilities = null, completed_at = null;
    if (receipt) {
      response = 'mismatch';
      if (receipt.model === JEV_MODEL && receipt.snapshot &&
          canonical(market(receipt.snapshot)) === canonical(market(snapshot)) &&
          canonical(receipt.questions) === canonical(questions)) {
        response = ['timeout', 'unavailable'].includes(receipt.status) ? receipt.status : 'interrupted';
        if (receipt.status === 'connected') {
          const r = receipt.result;
          const valid = parseJev({ model: r?.model, usage: { input_tokens: r?.input_tokens }, answers: { observation: {
            type: 'choice', choice: r?.decision, confidence: r?.confidence, probabilities: r?.probabilities } } });
          decision = valid.decision; probabilities = valid.probabilities;
          completed_at = r.completed_at / 1000;
          const requested = receipt.requested_at / 1000;
          response = finite(requested) && finite(completed_at) && requested >= s.captured_at &&
            completed_at >= requested && completed_at <= s.captured_at + 15 ? 'timely' : 'late';
        }
      }
    }
    outcomes.push({ bar_time: row.bar_time, captured_at: s.captured_at, signal: s.signal,
      slope_pass: s.slope_pass, outcome: row.outcome, net_usd: net,
      exit_reason: row.outcome === 'resolved' ? row.trade.exit_reason : null,
      response, decision, probabilities, completed_at,
      input: { candles: snapshot.bars.length, bid: s.bid, ask: s.ask, indicators: s.indicators,
        costs: s.costs, risk: snapshot.risk },
      input_sha256: await hash(market(snapshot)), journal_input_sha256: s.input_sha256,
      prompt_sha256: await hash(questions), model: JEV_MODEL });
  }
  const total = outcomes.length, arms = {};
  for (const name of ['baseline', 'slope', 'jev']) {
    const selected = outcomes.filter(o => name === 'baseline' || (name === 'slope' ? o.slope_pass :
      o.response === 'timely' && o.decision === 'review_setup'));
    const resolved = selected.filter(o => o.outcome === 'resolved');
    arms[name] = { selected: selected.length, resolved: resolved.length,
      coverage: total ? selected.length / total : null,
      expectancy_usd: resolved.length ? resolved.reduce((sum, o) => sum + o.net_usd, 0) / resolved.length : null };
  }
  const responses = Object.fromEntries(['timely', 'missing', 'late', 'mismatch', 'timeout', 'unavailable', 'interrupted']
    .map(status => [status, outcomes.filter(o => o.response === status).length]));
  return { status: 'ready', qualification: 'unqualified_diagnostic', promotion: 'blocked',
    generated_at: report.generated_at, last_bar: report.last_bar, samples: report.samples, gaps: report.gaps,
    journal_config_sha256: report.journal_config_sha256, eligible: total, arms, responses,
    response_coverage: total ? responses.timely / total : null,
    abstained: outcomes.filter(o => o.response === 'timely' && o.decision === 'insufficient_data').length,
    checkpoint: { target: 50, resolved: arms.baseline.resolved, reached: arms.baseline.resolved >= 50 }, outcomes };
}

export async function readOutcomeReport(env) {
  const url = new URL(env.STATUS_ORIGIN_URL);
  if (url.protocol !== 'https:') throw Error('Invalid origin');
  url.pathname = '/jev-scorecard'; url.search = '';
  const response = await fetch(url, { headers: { 'CF-Access-Client-ID': env.STATUS_ACCESS_CLIENT_ID,
    'CF-Access-Client-Secret': env.STATUS_ACCESS_CLIENT_SECRET }, redirect: 'manual', signal: AbortSignal.timeout(10000) });
  if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw Error('Outcome report unavailable');
  const text = await response.text();
  if (text.length > 8_000_000) throw Error('Oversized outcome report');
  return JSON.parse(text);
}
