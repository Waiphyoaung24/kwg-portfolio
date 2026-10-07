import type { APIRoute } from 'astro';
import contract from '../../../../ops/trading/fixtures/status-contract.json';

export const prerender = false;

// Explicit dev-test opt-in only; production status belongs to the Access-gated Worker.
export const GET: APIRoute = () => {
  if (!import.meta.env.DEV || import.meta.env.PUBLIC_TRADING_FIXTURE !== '1') {
    return new Response(null, { status: 404 });
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
