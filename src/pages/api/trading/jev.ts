import type { APIRoute } from 'astro';
export const prerender = false;

// Production requests belong to the Access-gated Worker. Local fixtures never call TypeSafe.
const enabled = import.meta.env.DEV && import.meta.env.PUBLIC_TRADING_FIXTURE === '1';
let observed = 0;
const response = () => Response.json({ status: observed ? 'connected' : 'ready',
  message: 'Local synthetic Jev preview. No provider request or broker order.',
  accounted_usd: observed ? .000017 : 0, budget_usd: 5,
  snapshot: observed ? { symbol: 'XAUUSD-VIP', timeframe: 'M15', checked_at: observed,
    bid: 4100.25, ask: 4100.5, signal: 'none', strategy_status: 'blocked' } : null,
  result: observed ? { model: 'jev-1.13.0 (synthetic)', decision: 'insufficient_data', confidence: .97, latency_ms: 500 } : null,
}, { headers: { 'Cache-Control': 'no-store' } });
export const GET: APIRoute = () => enabled ? response() : new Response(null, { status: 404 });
export const POST: APIRoute = ({ request, url }) => {
  if (!enabled) return new Response(null, { status: 404 });
  if (request.headers.get('Origin') !== url.origin) return new Response(null, { status: 403 });
  observed = Math.floor(Date.now() / 1000);
  return response();
};
