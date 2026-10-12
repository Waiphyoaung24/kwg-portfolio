import type { APIRoute } from 'astro';
export const prerender = false;
const enabled = import.meta.env.DEV && import.meta.env.PUBLIC_TRADING_FIXTURE === '1';
export const GET: APIRoute = () => enabled ? Response.json({
  status: 'ready', synthetic: true, qualification: 'unqualified_diagnostic', eligible: 3,
  generated_at: 1791832500, last_bar: 1791831600, samples: 30, gaps: 0,
  journal_config_sha256: 'synthetic fixture — no provider or broker calls', accounted_usd: 0,
  arms: {
    baseline: { selected: 3, resolved: 2, expectancy_usd: 7.5 },
    slope: { selected: 2, resolved: 1, expectancy_usd: -5 },
    jev: { selected: 1, resolved: 1, expectancy_usd: 20 },
  },
  checkpoint: { resolved: 2, target: 50, reached: false },
  responses: { timely: 2, missing: 1, late: 0, mismatch: 0, timeout: 0, unavailable: 0, interrupted: 0 }, abstained: 1,
  outcomes: [
    { bar_time: 1791804600, signal: 'long', slope_pass: false, outcome: 'resolved', net_usd: 20, response: 'timely', decision: 'review_setup', evidence: 'Synthetic UI example' },
    { bar_time: 1791813600, signal: 'short', slope_pass: true, outcome: 'resolved', net_usd: -5, response: 'timely', decision: 'insufficient_data', evidence: 'Synthetic UI example' },
    { bar_time: 1791831600, signal: 'long', slope_pass: true, outcome: 'pending', net_usd: null, response: 'missing', decision: null, evidence: 'Synthetic UI example' },
  ],
}, { headers: { 'Cache-Control': 'no-store' } }) : new Response(null, { status: 404 });
