import type { APIRoute } from 'astro';
export const prerender = false;
const enabled = import.meta.env.DEV && import.meta.env.PUBLIC_TRADING_FIXTURE === '1';
export const GET: APIRoute = () => enabled ? Response.json({
  status: 'ready', synthetic: true, generated_at: Math.floor(Date.now() / 1000),
  candidates: 12, pending: 1, no_state: 1, closed: 10, unresolved: 1, mode_counts: { shadow: 13 },
  receipts: { ok: 9, timeout: 1, unavailable: 0, budget_exhausted: 0, invalid: 0, missing: 1, late: 0 },
  all: { trades: 9, avg_net_usd: -1.5 }, jev_kept: { trades: 6, avg_net_usd: 2.25 }, jev_vetoed: { trades: 3, avg_net_usd: -9 },
  gate: { min_closed: 50, bad_receipt_max: 0.2, bad_receipt_rate: 0.25, passes: false,
    reasons: ['Need 50 closed shadow trades with resolved P/L; have 9', 'Bad receipts 3/12 reach the 20% limit'] },
  veto: {
    candidates: 3, submitted: 2, blocked: 1, pending: 0, no_state: 0, unresolved: 0,
    receipts: { ok: 2, timeout: 1, unavailable: 0, budget_exhausted: 0, invalid: 0, missing: 0, late: 0 },
    results: { trades: 2, avg_net_usd: 2.9, net_usd: 5.8 },
    recent: [
      { bar_time: 1791964800, side: 'short', receipt: 'timeout', choice: null, confidence: null, submitted: false, state: null, net_usd: null, reason: 'Jev timeout' },
      { bar_time: 1791964500, side: 'long', receipt: 'ok', choice: 'buy', confidence: .6, submitted: true, state: 'closed', net_usd: -2.5, reason: null },
      { bar_time: 1791964200, side: 'short', receipt: 'ok', choice: 'sell', confidence: .7, submitted: true, state: 'closed', net_usd: 8.3, reason: null },
    ],
  },
  qualification: 'demo fills; unqualified; not a profitability claim',
}, { headers: { 'Cache-Control': 'no-store' } }) : new Response(null, { status: 404 });
