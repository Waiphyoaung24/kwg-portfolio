import type { APIRoute } from 'astro';
import { selectedInstrument } from '../../../scripts/trading-instruments.mjs';
import contract from '../../../../ops/trading/fixtures/status-contract.json';
import pilot from '../../../../ops/trading/fixtures/pilot-status.json';

export const prerender = false;

// Explicit dev-test opt-in only; production status belongs to the Access-gated Worker.
export const GET: APIRoute = ({ url }) => {
  if (!import.meta.env.DEV || import.meta.env.PUBLIC_TRADING_FIXTURE !== '1') {
    return new Response(null, { status: 404 });
  }
  let selected;
  try { selected = selectedInstrument(url.search); }
  catch { return new Response(null, { status: 400 }); }
  if (selected.symbol === 'BTCUSD') {
    const now = Math.floor(Date.now() / 1000);
    const payload = structuredClone(pilot);
    payload.symbol = 'BTCUSD';
    payload.checked_at = now;
    payload.bar_time = Math.floor(now / 900) * 900 - 900;
    Object.assign(payload.health, { bid: 82790.5, ask: 82807.49, sampled_at: now,
      tick_time: now, tick_time_msc: now * 1000, quote_age_seconds: 0, history_bar_time: payload.bar_time });
    Object.assign(payload.pilot, { strategy: 'btc-ema-v1-m15-trend-3', status: 'standby',
      updated_at: now, started_at: null, ends_at: null, realized_net_usd: 0, floating_usd: 0,
      completed_trades: 0, recent_trades: [], reason: 'Owner activation required' });
    Object.assign(payload.execution, { status: 'disarmed', updated_at: now, side: null, volume: null,
      opened_at: null, closed_at: null, realized_net_usd: null, entry_price: null, sl: null, tp: null });
    payload.reason = 'Owner activation required';
    return Response.json(payload, { headers: { 'Cache-Control': 'no-store' } });
  }
  if (import.meta.env.PUBLIC_TRADING_PILOT_FIXTURE === '1') {
    const payload = structuredClone(pilot);
    // Sample history belongs only to the opted-in local design preview.
    payload.pilot.recent_trades = [12.8, -4.5, 8.2, -6.1, 15.4, 3.6].map((net, index) => ({
      side: index % 2 === 0 ? 'buy' : 'sell',
      opened_at: payload.checked_at - 9000 + index * 1500,
      closed_at: payload.checked_at - 8400 + index * 1500,
      realized_net_usd: net,
    }));
    payload.pilot.completed_trades = payload.pilot.recent_trades.length;
    payload.pilot.realized_net_usd = 29.4;
    payload.reason = payload.pilot.reason = 'Managing one protected demo position';
    const shift = Math.floor(Date.now() / 1000) - payload.checked_at;
    payload.checked_at += shift;
    // A bounded synthetic path makes the preview move without inventing broker ticks.
    const phase = payload.checked_at;
    payload.health.bid = Math.round((4100.25 + Math.sin(phase / 11) * 0.8 + Math.sin(phase / 3) * 0.15) * 100) / 100;
    payload.health.ask = Math.round((payload.health.bid + 0.25) * 100) / 100;
    payload.pilot.floating_usd = Math.round((payload.health.bid - payload.execution.entry_price) * 100) / 100;
    payload.bar_time += shift;
    payload.health.sampled_at += shift;
    payload.health.tick_time += shift;
    payload.health.tick_time_msc += shift * 1000;
    payload.health.history_bar_time += shift;
    payload.execution.updated_at += shift;
    payload.execution.opened_at += shift;
    payload.pilot.updated_at += shift;
    payload.pilot.started_at += shift;
    payload.pilot.ends_at += shift;
    for (const trade of payload.pilot.recent_trades) {
      trade.opened_at += shift;
      trade.closed_at += shift;
    }
    return Response.json(payload, { headers: { 'Cache-Control': 'no-store' } });
  }
  const shift = Math.floor(Date.now() / 1000) - contract.now;
  const payload = structuredClone(contract.cases[0].payload);
  payload.checked_at += shift;
  payload.bar_time += shift;
  payload.health.sampled_at += shift;
  payload.health.tick_time += shift;
  payload.health.tick_time_msc += shift * 1000;
  payload.health.history_bar_time += shift;
  return Response.json(payload, { headers: { 'Cache-Control': 'no-store' } });
};
