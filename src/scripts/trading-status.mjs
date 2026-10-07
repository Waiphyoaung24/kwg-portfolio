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
  const ready = current && health.terminal === 'connected' && health.quote === 'fresh' && data.status !== 'blocked';
  const waiting = current && health.terminal === 'connected' && health.quote === 'stale';
  const priced = current && health.terminal === 'connected' && health.quote === 'fresh'
    && typeof health.quote_age_seconds === 'number' && health.quote_age_seconds >= 0
    && health.quote_age_seconds + now - health.sampled_at <= 30
    && Number.isFinite(health.bid) && Number.isFinite(health.ask)
    && health.bid > 0 && health.ask >= health.bid && health.ask <= 1e6;
  return {
    price: priced ? `${health.bid.toFixed(2)} / ${health.ask.toFixed(2)}` : '—',
    state: !alive ? 'Observer offline' : waiting ? 'Waiting for price' : ready ? 'Observing' : 'Needs attention',
    guidance: !alive ? 'The observer has stopped reporting. Check the VPS observer before using any signals.'
      : waiting ? 'MT5 is connected, but the last gold price is too old to evaluate. Leave the observer running; it will check again automatically. If prices stay old during an open trading session, check the MT5 feed.'
      : ready ? 'The observer is checking completed 15-minute candles. Use these observations to validate the data and test the strategy; a signal does not place an order.'
      : 'Signal checks are paused. Open technical details for the reason before continuing.',
    delivery: 'Worker → Tunnel → status service responded',
    heartbeat: alive ? `Reporting · ${Math.floor(now - data.checked_at)}s ago` : 'Missing or expired',
    connection: current ? health.terminal === 'connected' ? 'Connected to demo' : terminalLabels[health.terminal] ?? 'Unknown' : 'Unknown — no current check',
    freshness: current ? health.quote === 'stale' ? 'Waiting for a fresh price' : quoteLabels[health.quote] ?? 'Unknown' : 'Unknown — no current check',
    tick: date(health?.tick_time_msc ? health.tick_time_msc / 1000 : health?.tick_time),
    age: typeof health?.quote_age_seconds === 'number' && Number.isFinite(health.quote_age_seconds)
      ? `${health.quote_age_seconds.toFixed(3)}s at ${date(health.sampled_at)}${current ? '' : ' (expired check)'}` : '—',
    history: current && Number.isInteger(health.history_count) ? `${health.history_count} bars fetched` : 'Unknown — no current check',
    candle: date(health?.history_bar_time),
    strategy: !alive ? 'Paused — no current observer report' : data.status === 'blocked' ? 'Blocked — see reason below' : 'Observing · orders off',
    signal: ready ? ({ long: 'Long setup', short: 'Short setup', none: 'No setup yet' }[data.signal] ?? '—') : 'Paused',
    checked: date(data.checked_at),
    reason: alive ? data.reason || 'Waiting for the next completed candle.' : 'Observer report expired. Waiting for a current report.',
  };
}

export function executionFields(execution, now = Date.now() / 1000) {
  if (!execution || execution.mode !== 'one-shot-demo' ||
      (!['closed', 'disarmed'].includes(execution.status) && !recent(execution.updated_at, now))) {
    return { state: 'Unknown', side: '—', volume: '—', opened: '—', closed: '—',
      result: '—', updated: '—', entry: '—', sl: '—', tp: '—',
      guidance: 'No current one-shot execution report.' };
  }
  const labels = { disarmed: 'Disarmed', armed: 'Armed', submitting: 'Submitting', pending: 'Pending',
    open: 'Open', closing: 'Closing', closed: 'Closed', needs_attention: 'Needs attention' };
  const state = labels[execution.status] ?? 'Unknown';
  const result = execution.status === 'closed' && typeof execution.realized_net_usd === 'number'
    ? `${execution.realized_net_usd.toFixed(2)} USD net` : '—';
  const guidance = execution.status === 'needs_attention'
    ? 'Review the private journal and broker position. No new entry will be sent.'
    : execution.status === 'closed' ? (execution.close_reason === 'manual desktop'
      ? 'Closed from MT5 desktop. This is a historical result.'
      : 'The broker close was reconciled. This is a historical result.')
    : execution.status === 'open' ? 'Position protected by broker-held stop and target. It stays open until one is hit.'
    : execution.status === 'pending' ? 'Entry is waiting at the broker. Cancel it manually in MT5 if you no longer want it.'
    : execution.status === 'disarmed' ? execution.close_reason || 'No new demo attempt is armed.'
    : 'A supervised demo attempt is in progress. Review the private journal for details.';
  return { state, side: execution.side ? execution.side.toUpperCase() : '—',
    volume: typeof execution.volume === 'number' ? `${execution.volume} lot` : '—',
    opened: date(execution.opened_at), closed: date(execution.closed_at), result,
    updated: date(execution.updated_at), guidance,
    entry: typeof execution.entry_price === 'number' ? execution.entry_price.toFixed(2) : '—',
    sl: typeof execution.sl === 'number' ? execution.sl.toFixed(2) : '—',
    tp: typeof execution.tp === 'number' ? execution.tp.toFixed(2) : '—' };
}
