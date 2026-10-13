// Gold M5 Jev shadow scorecard view. Pure mapping plus a GET-only poller; no paid calls.
const STRATEGY = 'gold-ema-v1-m5-trend-jev';
const QUALIFICATION = 'demo fills; unqualified; not a profitability claim';
const RECEIPTS = [['ok', 'OK'], ['timeout', 'Timeout'], ['unavailable', 'Unavailable'], ['budget_exhausted', 'Budget exhausted'],
  ['invalid', 'Invalid'], ['missing', 'Missing'], ['late', 'Late']];
// Each gate check owns the fixed reason prefixes written by ops/trading/jev_m5_scorecard.py.
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
  if (data?.status === 'unavailable') return { available: false, summary: 'Scorecard unavailable. Check your sign-in and the runner journal; results are not zero.',
    kept: blank, all: blank, vetoed: blank, receipts: '—', counts: '—', verdict: 'Gate unavailable', checks: [] };
  const gate = data?.gate, r = data?.receipts;
  if (data?.status !== 'ready' || data.qualification !== QUALIFICATION || !Number.isFinite(data.generated_at) ||
      !['candidates', 'pending', 'no_state', 'closed', 'unresolved'].every(k => count(data[k])) ||
      !r || !RECEIPTS.every(([k]) => count(r[k])) || !gate || !count(gate.min_closed) || !Array.isArray(gate.reasons) ||
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
  if (reasons.length) throw Error('Unknown gate reason');
  const summary = (data.candidates ? `${data.candidates} due shadow candidates · ${data.closed} closed trades.` : 'No due shadow candidates yet.') +
    ` Report updated ${time(data.generated_at)}.`;
  return { available: true, summary: data.synthetic ? `Synthetic local preview — not trading results. ${summary}` : summary,
    kept, all, vetoed, receipts: RECEIPTS.map(([k, label]) => `${label} ${r[k]}`).join(' · '),
    counts: `Pending ${data.pending} · No Jev state ${data.no_state} · Closed without P/L ${data.unresolved}`,
    verdict: gate.passes ? 'Gate met · owner review required before veto' : 'Gate not met', checks };
}

export function m5Mode(pilotState, pilot) {
  if (pilotState === 'Unknown') return 'Mode unavailable';
  if (pilot?.strategy !== STRATEGY) return 'Not running';
  return ({ shadow: 'Shadow', veto: 'Veto' })[pilot.jev_mode] ?? 'Mode unknown';
}

export function budgetText(data) {
  return `${Number.isFinite(data?.remaining_usd) ? `$${data.remaining_usd.toFixed(2)}` : '—'} of $5.00 left`;
}

export function mountJevM5(doc, win, fetcher = fetch) {
  const panel = doc.getElementById('jev-m5-panel');
  if (!panel || new URLSearchParams(win.location.search).get('symbol') === 'BTCUSD') return;
  panel.hidden = false;
  const field = key => doc.getElementById(`jev-m5-${key}`);
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
      const [scorecard, budget] = await Promise.allSettled([get('/api/trading/jev-m5-scorecard'), get('/api/trading/jev')]);
      let view;
      try { view = m5ScorecardView(scorecard.status === 'fulfilled' ? scorecard.value : null); } catch { view = m5ScorecardView({ status: 'unavailable' }); }
      field('summary').textContent = view.summary;
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
      field('budget').textContent = budgetText(budget.status === 'fulfilled' ? budget.value : null);
    } finally { busy = false; }
  };
  void refresh();
  const interval = win.setInterval(() => { if (!doc.hidden) void refresh(); }, 60000);
  win.addEventListener('pagehide', () => win.clearInterval(interval), { once: true });
}
