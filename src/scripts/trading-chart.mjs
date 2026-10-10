import { executionFields, statusFields } from './trading-status.mjs';
import { normalizePilot } from './trading-pilot.mjs';

export function chartSnapshot(data, now = Date.now() / 1000) {
  if (!data) return { quote: null, trades: null, levels: null };
  let pilot = null;
  try { pilot = normalizePilot(data.pilot ?? null, now, data.symbol); } catch { /* Invalid reports clear the chart. */ }
  const h = data.health;
  const at = h?.tick_time_msc ? h.tick_time_msc / 1000 : h?.tick_time;
  const quote = statusFields(data, now).price !== '—' && Number.isFinite(at) && at > 0 && at <= now
    ? { at, bid: h.bid, ask: h.ask } : null;
  const e = data.execution;
  const levels = executionFields(e, now).state === 'Open' ? { side: e.side, entry: e.entry_price, sl: e.sl, tp: e.tp } : null;
  return { quote, trades: pilot?.recent_trades ?? null, levels };
}

// Keep only this page session; clear on stale/auth failure and break lines across polling gaps.
export function appendQuote(samples, quote) {
  if (!quote) return [];
  const previous = samples.at(-1);
  if (previous && quote.at <= previous.at) return samples;
  return [...(previous && quote.at - previous.at > 30 ? [] : samples), quote].slice(-180);
}

export function quotePlot(samples) {
  if (!samples.length) return null;
  const min = Math.min(...samples.map(s => s.bid)), max = Math.max(...samples.map(s => s.ask));
  const pad = Math.max((max - min) * .2, .05);
  const low = min - pad, high = max + pad;
  const first = samples[0].at, last = samples.at(-1).at;
  // SVG viewBox coordinates; linear time and price axes, not CSS dimensions.
  const x = time => 12 + (time - first) / Math.max(last - first, 1) * 616;
  const y = price => 220 - (price - low) / (high - low) * 200;
  return { low, high, first, last,
    bid: samples.map(s => `${x(s.at)},${y(s.bid)}`).join(' '),
    ask: samples.map(s => `${x(s.at)},${y(s.ask)}`).join(' ') };
}
