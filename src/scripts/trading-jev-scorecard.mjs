const names = ['baseline', 'slope', 'jev'];
const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });
const time = seconds => Number.isFinite(seconds) ? new Date(seconds * 1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC') : 'none';

export function scorecardText(data) {
  if (data?.status !== 'ready' || data.qualification !== 'unqualified_diagnostic' || !Number.isInteger(data.eligible) ||
      data.eligible < 0 || !data.checkpoint || !data.responses || !Array.isArray(data.outcomes)) throw Error('Invalid scorecard');
  const cells = {};
  for (const name of names) {
    const arm = data.arms?.[name];
    if (!arm || !Number.isInteger(arm.selected) || !Number.isInteger(arm.resolved) ||
        arm.resolved < 0 || arm.selected < arm.resolved || arm.selected > data.eligible ||
        (arm.resolved ? !Number.isFinite(arm.expectancy_usd) : arm.expectancy_usd !== null)) throw Error('Invalid scorecard arm');
    cells[`${name}-net`] = arm.resolved ? money.format(arm.expectancy_usd) : '—';
    cells[`${name}-coverage`] = `${arm.selected} / ${data.eligible}${data.eligible ? ` (${(arm.selected / data.eligible * 100).toFixed(0)}%)` : ''}`;
    cells[`${name}-resolved`] = `${arm.resolved} / ${arm.selected}`;
  }
  return cells;
}

export function mountScorecard(doc, win, fetcher = fetch, onReady = () => {}) {
  const panel = doc.getElementById('jev-scorecard');
  if (!panel || new URLSearchParams(win.location.search).get('symbol') === 'BTCUSD') return;
  const field = key => doc.getElementById(`scorecard-${key}`);
  let busy = false, entered = false, lastOutcomes = '';
  const refresh = async () => {
    if (busy) return;
    busy = true;
    try {
      const response = await fetcher('/api/trading/jev-scorecard', { credentials: 'same-origin', cache: 'no-store', redirect: 'manual', signal: AbortSignal.timeout(15000) });
      if (!response.ok || !response.headers.get('Content-Type')?.includes('application/json')) throw Error('Unavailable');
      const data = await response.json(), cells = scorecardText(data);
      for (const [key, value] of Object.entries(cells)) field(key).textContent = value;
      field('status').textContent = data.synthetic ? 'Synthetic local preview — these are not trading results.' : `${data.eligible ? 'Diagnostic outcomes.' : 'No eligible baseline setups recorded yet.'} Candles through ${time(data.last_bar)}. Report updated ${time(data.generated_at)}.`;
      field('checkpoint').textContent = `${data.checkpoint.resolved} / 50 resolved baseline setups · ${data.checkpoint.reached ? 'Diagnostic review checkpoint reached. No automatic promotion.' : 'Collecting toward the first diagnostic review.'}`;
      field('responses').textContent = `Timely matched responses: ${data.responses.timely} / ${data.eligible}. Abstained: ${data.abstained}. Missing: ${data.responses.missing}. Late: ${data.responses.late}. Mismatched: ${data.responses.mismatch}. Failed / interrupted: ${data.responses.timeout + data.responses.unavailable + data.responses.interrupted}.`;
      field('quality').textContent = `${data.samples} captured candles · ${data.gaps} gaps. Frozen journal: ${data.journal_config_sha256}. Manual no-setup checks are excluded. API used / reserved: ${Number.isFinite(data.accounted_usd) ? `$${data.accounted_usd.toFixed(6)} / $5` : 'unavailable'}.`;
      const serialized = JSON.stringify(data.outcomes);
      if (serialized !== lastOutcomes) {
        const host = field('outcomes');
        const open = new Set([...host.querySelectorAll('details[open]')].map(node => node.dataset.bar));
        host.replaceChildren();
        for (const row of [...data.outcomes].reverse()) {
          const details = doc.createElement('details'), summary = doc.createElement('summary'), content = doc.createElement('pre');
          details.dataset.bar = String(row.bar_time); details.open = open.has(details.dataset.bar);
          summary.textContent = `${time(row.bar_time)} · ${row.signal} · ${row.outcome} · Jev ${row.response}`;
          content.textContent = JSON.stringify(row, null, 2);
          details.append(summary, content); host.append(details);
        }
        lastOutcomes = serialized;
      }
      if (!entered) { entered = true; onReady(); }
    } catch {
      for (const name of names) for (const key of ['net', 'coverage', 'resolved']) field(`${name}-${key}`).textContent = '—';
      field('status').textContent = 'Evaluation unavailable. Check your sign-in and journal connection; results are not zero.';
      field('checkpoint').textContent = 'First review: 50 resolved baseline setups. Progress unavailable.';
      field('responses').textContent = 'Response coverage unavailable.';
      field('quality').textContent = 'Journal details unavailable.';
      field('outcomes').replaceChildren(); lastOutcomes = '';
    } finally { busy = false; }
  };
  void refresh();
  const interval = win.setInterval(() => { if (!doc.hidden) void refresh(); }, 60000);
  win.addEventListener('pagehide', () => win.clearInterval(interval), { once: true });
}
