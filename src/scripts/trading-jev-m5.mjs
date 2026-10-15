// M5 Jev shadow scorecard view. Pure mapping plus a GET-only poller; no paid calls.
import { selectedInstrument } from './trading-instruments.mjs';
const STRATEGIES = ['gold-ema-v1-m5-trend-jev', 'btc-ema-v1-m5-trend-jev'];
const QUALIFICATION = 'demo fills; unqualified; not a profitability claim';
const RECEIPTS = [['ok', 'OK'], ['timeout', 'Timeout'], ['unavailable', 'Unavailable'], ['budget_exhausted', 'Budget exhausted'],
  ['invalid', 'Invalid'], ['missing', 'Missing'], ['late', 'Late']];
// Each gate check owns the fixed reason prefixes written by ops/trading/jev_m5_scorecard.py; others become 'Other' rows.
const CHECKS = [['closed', 'Closed trades', ['Need ']], ['receipts', 'Receipt health', ['No due shadow', 'Bad receipts ']],
  ['kept', 'Jev-kept beats all', ['Jev-kept ']]];
const count = x => Number.isInteger(x) && x >= 0;
const time = seconds => new Date(seconds * 1000).toISOString().replace('T', ' ').replace(/\.\d{3}Z$/, ' UTC');
const trades = n => `${n} trade${n === 1 ? '' : 's'}`;
const blank = { text: '—', tone: 'none' };

function signed(value) {
  const cents = Math.round(value * 100);
  const amount = `$${(Math.abs(cents) / 100).toFixed(2)}`;
  return cents > 0 ? { text: `↑ +${amount}`, tone: 'up' } : cents < 0 ? { text: `↓ −${amount}`, tone: 'down' } : { text: `→ ${amount}`, tone: 'flat' };
}

function group(value) {
  if (!value || !count(value.trades) || (value.trades ? !Number.isFinite(value.avg_net_usd) : value.avg_net_usd !== null)) throw Error('Invalid scorecard group');
  const money = value.trades ? signed(value.avg_net_usd) : blank;
  return { text: `${money.text} · ${trades(value.trades)}`, tone: money.tone, money: money.text };
}

export function m5ScorecardView(data) {
  if (data?.status === 'unavailable') return { available: false, summary: 'Scorecard unavailable or older than 2 minutes; results are not zero.', updated: '',
    kept: blank, all: blank, vetoed: blank, receipts: '—', counts: '—', verdict: 'Gate unavailable', checks: [] };
  const gate = data?.gate, r = data?.receipts;
  if (data?.status !== 'ready' || data.qualification !== QUALIFICATION || !Number.isFinite(data.generated_at) ||
      !['candidates', 'pending', 'no_state', 'closed', 'unresolved'].every(k => count(data[k])) ||
      !r || !RECEIPTS.every(([k]) => count(r[k])) || !gate || !count(gate.min_closed) || !Number.isFinite(gate.bad_receipt_max) || !Array.isArray(gate.reasons) ||
      !gate.reasons.every(reason => typeof reason === 'string') || gate.passes !== (gate.reasons.length === 0)) throw Error('Invalid scorecard');
  const kept = group(data.jev_kept), all = group(data.all), vetoed = group(data.jev_vetoed);
  if (RECEIPTS.reduce((sum, [k]) => sum + r[k], 0) + data.no_state !== data.candidates ||
      data.jev_kept.trades + data.jev_vetoed.trades !== data.all.trades || data.closed - data.unresolved !== data.all.trades) throw Error('Inconsistent scorecard');
  const reasons = [...gate.reasons];
  const bad = data.candidates - r.ok;
  const details = {
    closed: `${data.all.trades} / ${gate.min_closed} closed shadow trades`,
    receipts: data.candidates ? `${bad} / ${data.candidates} bad (${Math.round(bad / data.candidates * 100)}%), limit under ${Math.round(gate.bad_receipt_max * 100)}%` : 'No due candidates yet',
    kept: `Kept ${kept.money} vs all ${all.money} per trade`,
  };
  const checks = CHECKS.map(([key, label, prefixes]) => {
    const index = reasons.findIndex(reason => prefixes.some(prefix => reason.startsWith(prefix)));
    const reason = index < 0 ? null : reasons.splice(index, 1)[0];
    return { label, detail: details[key], met: reason === null, reason };
  });
  // A reason added to the scorecard later stays visible rather than blanking the panel.
  checks.push(...reasons.map(reason => ({ label: 'Other', detail: 'Reported by the scorecard', met: false, reason })));
  const summary = data.candidates ? `${data.candidates} due shadow candidates · ${data.closed} closed trades.` : 'No due shadow candidates yet.';
  return { available: true, summary: data.synthetic ? `Synthetic local preview — not trading results. ${summary}` : summary,
    updated: `Report updated ${time(data.generated_at)}.`,
    kept, all, vetoed, receipts: RECEIPTS.map(([k, label]) => `${label} ${r[k]}`).join(' · '),
    counts: `Pending ${data.pending} · No Jev state ${data.no_state} · Closed without P/L ${data.unresolved}`,
    verdict: gate.passes ? 'Gate met · owner review required before veto' : 'Gate not met', checks };
}

export function vetoActivityView(data) {
  const unavailable = { summary: 'Veto activity unavailable; the publisher may need updating. Results are not zero.', results: '—', receipts: '—', rows: [] };
  if (!data || !['candidates', 'submitted', 'blocked', 'pending', 'no_state', 'unresolved'].every(k => count(data[k])) ||
      data.submitted + data.blocked !== data.candidates || !data.receipts || !RECEIPTS.every(([k]) => count(data.receipts[k])) ||
      RECEIPTS.reduce((sum, [k]) => sum + data.receipts[k], 0) + data.no_state !== data.candidates ||
      !data.results || !count(data.results.trades) || (data.results.trades ? !Number.isFinite(data.results.net_usd) : data.results.net_usd !== null) ||
      !Array.isArray(data.recent) || data.recent.length > 20) return unavailable;
  if ((data.reporting_start !== undefined || data.reporting_end !== undefined) &&
      (!Number.isFinite(data.reporting_start) || !Number.isFinite(data.reporting_end) || data.reporting_start <= 0 || data.reporting_end - data.reporting_start !== 172800)) return unavailable;
  const rows = [];
  for (const row of data.recent) {
    if (!Number.isFinite(row.bar_time) || !['long', 'short'].includes(row.side) ||
        ![...RECEIPTS.map(([k]) => k), 'no_state'].includes(row.receipt) || typeof row.submitted !== 'boolean' ||
        (row.reason !== null && typeof row.reason !== 'string') ||
        (row.state !== null && typeof row.state !== 'string') ||
        (row.net_usd !== null && !Number.isFinite(row.net_usd)) ||
        (row.choice !== null && !['buy', 'sell', 'hold'].includes(row.choice)) ||
        (row.confidence !== null && (!Number.isFinite(row.confidence) || row.confidence < 0 || row.confidence > 1))) return unavailable;
    rows.push(`${time(row.bar_time)} · ${row.side === 'long' ? 'Buy' : 'Sell'} setup · Receipt: ${row.receipt}` +
      (row.choice ? ` · Jev ${row.choice}${row.confidence === null ? '' : ` (${Math.round(row.confidence * 100)}%)`}` : '') +
      ` · ${row.submitted ? `Submitted · ${row.state ?? 'outcome unknown'}` : 'Blocked before submission'}` +
      (row.net_usd === null ? '' : ` · ${signed(row.net_usd).text} net`) + (row.reason ? ` · ${row.reason}` : ''));
  }
  const window = data.reporting_start === undefined ? '' : `Reporting window ${time(data.reporting_start)} to ${time(data.reporting_end)}. `;
  return { summary: `${window}${data.candidates} completed decisions · ${data.submitted} submitted · ${data.blocked} blocked · ${data.pending} awaiting Jev.`,
    results: `${data.results.trades ? signed(data.results.net_usd).text : '—'} net · ${trades(data.results.trades)} closed with P/L · ${data.unresolved} closed without P/L`,
    receipts: RECEIPTS.map(([k, label]) => `${label} ${data.receipts[k]}`).join(' · ') + ` · No Jev state ${data.no_state}`,
    rows };
}

export function m5Mode(pilotState, pilot) {
  if (pilotState === 'Unknown') return 'Mode unavailable';
  if (!STRATEGIES.includes(pilot?.strategy)) return 'Not running';
  return ({ shadow: 'Shadow', veto: 'Veto' })[pilot.jev_mode] ?? 'Mode unknown';
}

export function budgetText(data) {
  return `${Number.isFinite(data?.remaining_usd) ? `$${data.remaining_usd.toFixed(2)}` : '—'} of $5.00 left`;
}

export function mountJevM5(doc, win, fetcher = fetch) {
  const panel = doc.getElementById('jev-m5-panel');
  if (!panel) return;
  const selected = selectedInstrument(win.location.search);
  panel.hidden = false;
  const field = key => doc.getElementById(`jev-m5-${key}`);
  field('instrument').textContent = `${selected.name} M5 · Jev decision layer`;
  const get = async url => {
    const response = await fetcher(url, { credentials: 'same-origin', cache: 'no-store', redirect: 'manual', signal: AbortSignal.timeout(15000) });
    if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw Error('Unavailable');
    return response.json();
  };
  let busy = false;
  const refresh = async () => {
    if (busy) return;
    busy = true;
    try {
      const [scorecard, budget] = await Promise.allSettled([get(`/api/trading/jev-m5-scorecard${selected.query}`), get('/api/trading/jev')]);
      let view;
      try {
        if (scorecard.status === 'fulfilled' && (scorecard.value.symbol ?? 'XAUUSD-VIP') !== selected.symbol) throw Error('Wrong symbol');
        view = m5ScorecardView(scorecard.status === 'fulfilled' ? scorecard.value : null); } catch { view = m5ScorecardView({ status: 'unavailable' }); }
      // Only the live region's changes are announced; the report time updates silently beside it.
      if (field('summary').textContent !== view.summary) field('summary').textContent = view.summary;
      field('updated').textContent = view.updated;
      for (const key of ['kept', 'all', 'vetoed']) { field(key).textContent = view[key].text; field(key).dataset.tone = view[key].tone; }
      field('verdict').textContent = view.verdict;
      field('receipts').textContent = view.receipts;
      field('counts').textContent = view.counts;
      field('checks').replaceChildren(...view.checks.map(check => {
        const item = doc.createElement('li');
        item.dataset.met = String(check.met);
        item.textContent = `${check.met ? 'Met' : 'Not met'} · ${check.label}: ${check.detail}${check.reason ? `. ${check.reason}` : ''}`;
        return item;
      }));
      const veto = vetoActivityView(view.available && scorecard.status === 'fulfilled' ? scorecard.value.veto : null);
      if (scorecard.status === 'fulfilled' && scorecard.value.synthetic) veto.summary = `Synthetic local preview — not trading results. ${veto.summary}`;
      for (const key of ['summary', 'results', 'receipts']) field(`veto-${key}`).textContent = veto[key];
      field('veto-recent').replaceChildren(...veto.rows.map(text => {
        const item = doc.createElement('li'); item.textContent = text; return item;
      }));
      field('budget').textContent = budgetText(budget.status === 'fulfilled' ? budget.value : null);
    } finally { busy = false; }
  };
  void refresh();
  const interval = win.setInterval(() => { if (!doc.hidden) void refresh(); }, 60000);
  win.addEventListener('pagehide', () => win.clearInterval(interval), { once: true });
}
