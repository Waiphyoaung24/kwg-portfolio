export function normalizePilot(value, now = Date.now() / 1000) {
  if (value === null) return null;
  if (!value || !['gold-ema-v1-slope-3', 'gold-ema-v1-m1-slope-3'].includes(value.strategy) || value.qualification !== 'unqualified' ||
      !['standby', 'active', 'paused', 'needs_attention', 'expired'].includes(value.status)) throw new Error('Invalid pilot');
  const result = { strategy: value.strategy, qualification: value.qualification, status: value.status };
  for (const key of ['updated_at', 'started_at', 'ends_at', 'realized_net_usd', 'floating_usd', 'completed_trades']) {
    const number = value[key] ?? null;
    if (number !== null && (typeof number !== 'number' || !Number.isFinite(number) || Math.abs(number) > 1e12)) throw new Error('Invalid pilot number');
    result[key] = number;
  }
  if (result.updated_at === null || now < result.updated_at || now - result.updated_at > 30) return null;
  const start = result.started_at, end = result.ends_at;
  if ((value.status === 'standby' && (start !== null || end !== null)) ||
      (value.status !== 'standby' && (start === null || end === null || !(start > 0 && start <= now && end > start && end - start <= 604800)))) throw new Error('Invalid pilot window');
  if (!Number.isInteger(result.completed_trades) || result.completed_trades < 0 ||
      typeof value.reason !== 'string' || value.reason.length > 160 ||
      !Array.isArray(value.recent_trades) || value.recent_trades.length > 10) throw new Error('Invalid pilot results');
  result.reason = value.reason;
  result.recent_trades = value.recent_trades.map(trade => {
    if (!trade || !['buy', 'sell'].includes(trade.side)) throw new Error('Invalid pilot trade');
    const clean = { side: trade.side };
    for (const key of ['opened_at', 'closed_at', 'realized_net_usd']) {
      if (typeof trade[key] !== 'number' || !Number.isFinite(trade[key]) || Math.abs(trade[key]) > 1e12) throw new Error('Invalid pilot trade number');
      clean[key] = trade[key];
    }
    if (!(clean.opened_at > 0 && clean.opened_at <= clean.closed_at && clean.closed_at <= now)) throw new Error('Invalid pilot trade times');
    return clean;
  });
  return result;
}

export function pilotFields(value, now = Date.now() / 1000) {
  let p;
  try { p = normalizePilot(value ?? null, now); } catch { p = null; }
  if (!p) return { state: 'Unknown', reason: 'No current pilot report.', realized: '—', floating: '—',
    remaining: '—', count: '—', canPause: false, trades: [] };
  const money = number => typeof number === 'number' ? `${number.toFixed(2)} USD` : 'Unknown';
  const minutes = p.ends_at === null ? null : Math.max(0, Math.ceil((p.ends_at - now) / 60));
  return { state: ({ standby: 'Not activated', active: 'Active', paused: 'Paused', needs_attention: 'Needs attention', expired: 'Expired' })[p.status],
    reason: p.reason, realized: money(p.realized_net_usd), floating: money(p.floating_usd),
    remaining: minutes === null ? 'Not started' : minutes === 0 ? 'Ended'
      : [minutes >= 1440 ? `${Math.floor(minutes / 1440)}d` : '', minutes >= 60 ? `${Math.floor(minutes % 1440 / 60)}h` : '', `${minutes % 60}m`].filter(Boolean).join(' '),
    count: String(p.completed_trades), canPause: p.status === 'active',
    trades: p.recent_trades.map(t => `${t.side === 'buy' ? 'Buy' : 'Sell'} · ${money(t.realized_net_usd)} net · ${new Date(t.closed_at * 1000).toISOString()}`) };
}
