import { executionFields, statusFields } from './trading-status.mjs';

export function entryReadiness(data, now = Date.now() / 1000, symbol = 'XAUUSD-VIP') {
  const pilot = pilotFields(data?.pilot, now, symbol);
  if (!data || pilot.state === 'Unknown' || !Number.isFinite(data.checked_at) || data.status === 'offline' || now - data.checked_at > 30 || now < data.checked_at) return 'Status unavailable';
  if (pilot.state !== 'Active') return pilot.state === 'Paused' ? 'Paused — no new orders' : pilot.state;
  const fields = statusFields(data, now);
  const execution = executionFields(data.execution, now);
  if (fields.connection !== 'Connected to demo' || execution.state === 'Unknown') return 'Waiting for broker checks';
  if (['Open', 'Pending', 'Armed', 'Submitting', 'Closing'].includes(execution.state)) return 'Waiting for current trade to finish';
  if (execution.state === 'Needs attention') return 'Needs attention';
  if (fields.price === '—') return 'Waiting for fresh quotes';
  if (data.status === 'blocked') return 'Waiting for entry checks';
  return 'Enabled — awaiting an eligible setup';
}

export function normalizePilot(value, now = Date.now() / 1000, symbol = 'XAUUSD-VIP') {
  if (value === null) return null;
  if (!value || !(symbol === 'BTCUSD' ? ['btc-ema-v1-m15-trend-3', 'btc-ema-v1-m1-scalp-60', 'btc-ema-v1-m5-trend-jev'] : symbol === 'XAUUSD-VIP' ? ['gold-ema-v1-slope-3', 'gold-ema-v1-m1-slope-3', 'gold-ema-v1-m1-trend-3', 'gold-ema-v1-m5-trend-jev'] : []).includes(value.strategy) || value.qualification !== 'unqualified' ||
      !['standby', 'active', 'paused', 'needs_attention', 'expired'].includes(value.status)) throw new Error('Invalid pilot');
  const result = { strategy: value.strategy, qualification: value.qualification, status: value.status };
  if (['gold-ema-v1-m5-trend-jev', 'btc-ema-v1-m5-trend-jev'].includes(value.strategy) && ['shadow', 'veto'].includes(value.jev_mode)) result.jev_mode = value.jev_mode;
  for (const key of ['updated_at', 'started_at', 'ends_at', 'realized_net_usd', 'floating_usd', 'completed_trades']) {
    const number = value[key] ?? null;
    if (number !== null && (typeof number !== 'number' || !Number.isFinite(number) || Math.abs(number) > 1e12)) throw new Error('Invalid pilot number');
    result[key] = number;
  }
  if (result.updated_at === null || now < result.updated_at || now - result.updated_at > 30) return null;
  const continuous = value.run_policy === 'continuous';
  if (value.run_policy !== undefined && !continuous) throw new Error('Invalid run policy');
  if (continuous) result.run_policy = 'continuous';
  const start = result.started_at, end = result.ends_at;
  if ((value.status === 'standby' && (start !== null || end !== null || continuous)) ||
      (value.status !== 'standby' && (start === null || !(start > 0 && start <= now) || (continuous ? end !== null || value.status === 'expired' : end === null || !(end > start && end - start <= 604800))))) throw new Error('Invalid pilot window');
  if (value.reporting_start !== undefined || value.reporting_end !== undefined) {
    const start = value.reporting_start, end = value.reporting_end;
    if (!Number.isFinite(start) || !Number.isFinite(end) || start <= 0 || start > now || end - start !== 172800) throw new Error('Invalid reporting window');
    result.reporting_start = start;
    result.reporting_end = end;
  }
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

export function pilotFields(value, now = Date.now() / 1000, symbol = 'XAUUSD-VIP') {
  let p;
  try { p = normalizePilot(value ?? null, now, symbol); } catch { p = null; }
  if (!p) return { state: 'Unknown', reason: 'No current pilot report.', realized: '—', floating: '—',
    reporting: '—', remaining: '—', count: '—', canPause: false, trades: [] };
  const money = number => typeof number === 'number' ? `${number.toFixed(2)} USD` : 'Unknown';
  const minutes = p.ends_at === null ? null : Math.max(0, Math.ceil((p.ends_at - now) / 60));
  return { state: ({ standby: 'Not activated', active: 'Active', paused: 'Paused', needs_attention: 'Needs attention', expired: 'Expired' })[p.status],
    reporting: p.reporting_start === undefined ? 'No reporting window set' : `${Math.floor(Math.min(172800, Math.max(0, now - p.reporting_start)) / 3600)}h ${Math.floor(Math.min(172800, Math.max(0, now - p.reporting_start)) % 3600 / 60)}m / 48h elapsed · Ends ${new Date(p.reporting_end * 1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC')}`,
    reason: p.reason, realized: money(p.realized_net_usd), floating: money(p.floating_usd),
    remaining: p.run_policy === 'continuous' ? 'Until you pause' : minutes === null ? 'Not started' : minutes === 0 ? 'Ended'
      : [minutes >= 1440 ? `${Math.floor(minutes / 1440)}d` : '', minutes >= 60 ? `${Math.floor(minutes % 1440 / 60)}h` : '', `${minutes % 60}m`].filter(Boolean).join(' '),
    count: String(p.completed_trades), canPause: p.status === 'active',
    trades: p.recent_trades.map(t => `${t.side === 'buy' ? 'Buy' : 'Sell'} · ${money(t.realized_net_usd)} net · ${new Date(t.closed_at * 1000).toISOString()}`) };
}
