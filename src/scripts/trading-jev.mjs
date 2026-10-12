const labels = { ready: 'Ready to connect', connected: 'Last request succeeded', running: 'Assessing snapshot',
  not_configured: 'Not connected', unavailable: 'Unavailable', timeout: 'Timed out',
  cooldown: 'Waiting', budget_exhausted: 'Budget reached', access: 'Sign-in required' };
const decisions = { wait: 'Nonpositive modeled outlook', review_setup: 'Positive modeled outlook', insufficient_data: 'Insufficient setup evidence' };
const failures = new Set(['not_configured', 'unavailable', 'timeout', 'access']);

export function jevNotification(previous, current) {
  if (failures.has(current) && !failures.has(previous)) return current === 'timeout' ? 'Jev timed out. The trading runner is unaffected.' : 'Jev is not connected. The trading runner is unaffected.';
  if (failures.has(previous) && current === 'connected') return 'Jev is connected again.';
  if (current === 'budget_exhausted' && previous !== current) return 'Jev reached its $5 budget. No further requests will be sent.';
  return null;
}

export function mountJevPanel(doc, win, fetcher = fetch) {
  const panel = doc.getElementById('jev-panel');
  if (!panel || new URLSearchParams(win.location.search).get('symbol') === 'BTCUSD') return;
  panel.hidden = false;
  const field = name => doc.getElementById(`jev-${name}`);
  const button = field('observe');
  let busy = false, previous = null;
  const render = data => {
    const status = Object.hasOwn(labels, data.status) ? data.status : 'unavailable';
    field('state').textContent = labels[status];
    field('message').textContent = data.message || (data.feed?.status === 'ready' ? 'Gold M15 feed connected. Watching for eligible baseline setups.' : 'Waiting for observer status.');
    // Clear old assessments on every failure, including expired authentication.
    const result = status === 'connected' ? data.result : null;
    field('decision').textContent = result ? decisions[result.decision] ?? 'Invalid assessment' : 'No current assessment';
    field('model').textContent = result?.model ?? '—';
    field('confidence').textContent = Number.isFinite(result?.confidence) ? `${(result.confidence * 100).toFixed(1)}%` : '—';
    field('latency').textContent = Number.isFinite(result?.latency_ms) ? `${result.latency_ms} ms` : '—';
    field('budget').textContent = Number.isFinite(data.accounted_usd) ? `$${data.accounted_usd.toFixed(6)} / $5.00` : '— / $5.00';
    const captured = new Date((data.snapshot?.captured_at ?? data.snapshot?.checked_at) * 1000);
    field('snapshot-time').textContent = Number.isFinite(captured.getTime()) ? captured.toISOString().replace('T', ' ').replace('.000Z', ' UTC') : '—';
    field('timeframe').textContent = data.snapshot?.timeframe ?? '—';
    field('input').textContent = data.snapshot ? JSON.stringify(data.snapshot, null, 2) : 'No snapshot sent.';
    button.disabled = busy || ['not_configured', 'access', 'running', 'budget_exhausted'].includes(status);
    const notification = jevNotification(previous, status);
    previous = status;
    if (notification) { field('toast-text').textContent = notification; field('toast').hidden = false; }
  };
  const refresh = async (method = 'GET') => {
    if (busy) return;
    busy = true; button.disabled = true;
    if (method === 'POST') field('state').textContent = 'Assessing snapshot';
    let data;
    try {
      const response = await fetcher('/api/trading/jev', { method, credentials: 'same-origin', cache: 'no-store', redirect: 'manual',
        signal: AbortSignal.timeout(22000), ...(method === 'POST' ? { headers: { 'Content-Type': 'application/json' }, body: '{}' } : {}) });
      if (response.type === 'opaqueredirect' || [401, 403].includes(response.status)) data = { status: 'access', message: 'Sign in to the trading dashboard again.' };
      else if (!response.headers.get('Content-Type')?.includes('application/json')) throw new Error('Unavailable');
      else { data = await response.json(); if (!Object.hasOwn(labels, data.status)) throw new Error('Invalid status'); }
    } catch (error) {
      data = { status: ['TimeoutError', 'AbortError'].includes(error.name) ? 'timeout' : 'unavailable',
        message: 'Jev could not be reached. No automatic retry; the trading runner is unaffected.' };
    } finally { busy = false; }
    render(data);
  };
  button.addEventListener('click', () => void refresh('POST'));
  field('dismiss').addEventListener('click', () => { field('toast').hidden = true; });
  void refresh();
  const interval = win.setInterval(() => { if (!doc.hidden) void refresh(); }, 15000);
  win.addEventListener('pagehide', () => win.clearInterval(interval), { once: true });
}
