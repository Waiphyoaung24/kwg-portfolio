const date = (value) => typeof value === 'number' && Number.isFinite(value) && value > 0 && value < 8.64e12
  ? `${new Date(value * 1000).toISOString().replace('T', ' ').slice(0, 19)} UTC` : '—';
const recent = (value, now) => typeof value === 'number' && now - value >= 0 && now - value <= 30;

// A successful fetch is not proof that an old observer or terminal is healthy.
export function statusFields(data, now = Date.now() / 1000) {
  const alive = data.status !== 'offline' && recent(data.checked_at, now);
  const health = data.health;
  const current = alive && health && recent(health.sampled_at, now);
  const quoteLabels = { fresh: 'Fresh at last check', stale: 'Stale — over 30 seconds',
    future: 'Future timestamp — clock check required', missing: 'No quote received',
    invalid: 'Invalid quote', unknown: 'Not checked' };
  const terminalLabels = { connected: 'Demo connected; account checks passed',
    disconnected: 'Disconnected', guard_failed: 'Demo safety checks failed', unknown: 'Not checked' };
  return {
    state: alive ? 'System reporting' : 'Observer offline',
    delivery: 'Worker → Tunnel → status service responded',
    heartbeat: alive ? `Reporting · ${Math.floor(now - data.checked_at)}s ago` : 'Missing or expired',
    connection: current ? terminalLabels[health.terminal] ?? 'Unknown' : 'Unknown — no current check',
    freshness: current ? quoteLabels[health.quote] ?? 'Unknown' : 'Unknown — no current check',
    tick: date(health?.tick_time_msc ? health.tick_time_msc / 1000 : health?.tick_time),
    age: typeof health?.quote_age_seconds === 'number' && Number.isFinite(health.quote_age_seconds)
      ? `${health.quote_age_seconds.toFixed(3)}s at ${date(health.sampled_at)}${current ? '' : ' (expired check)'}` : '—',
    history: current && Number.isInteger(health.history_count) ? `${health.history_count} bars fetched` : 'Unknown — no current check',
    candle: date(health?.history_bar_time),
    strategy: !alive ? 'Paused — no current observer report' : data.status === 'blocked' ? 'Blocked — see reason below' : 'Observing · orders off',
    signal: alive && data.status !== 'blocked' ? ({ long: 'Long', short: 'Short', none: 'None' }[data.signal] ?? '—') : 'None',
    checked: date(data.checked_at),
    reason: alive ? data.reason || 'Waiting for the next completed candle.' : 'Observer report expired. Waiting for a current report.',
  };
}
