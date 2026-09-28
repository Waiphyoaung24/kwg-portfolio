import { McpServer } from '@modelcontextprotocol/server';
import { createMcpHandler } from 'agents/mcp/server';
import { normalizeStatus } from '../../worker/src/index.js';

const baseline = {
  symbol: 'XAUUSD-VIP',
  mode: 'provisional-offline',
  qualification: 'unqualified',
  cost_profile: 'hypothetical',
  dataset_sha256: 'ba4f246746d861c9f61d82c7a09d17931cd74e9dea604ea2897853369dcf8614',
  manifest_sha256: '01f7c2c698e28474af9fd4398004e2a50331934a6df32b4b03e63ec8c3708291',
  baseline_sha256: '50de8aa4c4fbeaa4a5c4e825faaf78aeb0b13c7996e261d61eecc7d9f08c31ef',
  validation: {
    lower: { trades: 30, net_pnl_usd: -305.195, return_pct: -0.305195, profit_factor: 0.811364 },
    middle: { trades: 31, net_pnl_usd: -445.94, return_pct: -0.44594, profit_factor: 0.745684 },
    stress: { trades: 30, net_pnl_usd: -186.87, return_pct: -0.18687, profit_factor: 0.88238 },
  },
  research_connection: 'blocked',
  candidate_compared: false,
  promotion: 'blocked',
  limitations: ['historical costs unverified', 'validation previously inspected', 'fewer than 100 validation trades', 'live qualification incomplete'],
};

export async function goldStatus(env, fetcher = fetch) {
  if (!env.STATUS_ORIGIN_URL || !env.STATUS_ACCESS_CLIENT_ID || !env.STATUS_ACCESS_CLIENT_SECRET) {
    throw new Error('Status origin is not configured');
  }
  const origin = new URL(env.STATUS_ORIGIN_URL);
  if (origin.protocol !== 'https:') throw new Error('Status origin must use HTTPS');
  origin.pathname = '/status';
  origin.search = '';
  const response = await fetcher(origin, {
    headers: {
      'CF-Access-Client-ID': env.STATUS_ACCESS_CLIENT_ID,
      'CF-Access-Client-Secret': env.STATUS_ACCESS_CLIENT_SECRET,
    },
    redirect: 'manual', cache: 'no-store', signal: AbortSignal.timeout(5000),
  });
  if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Status origin is unavailable');
  }
  return normalizeStatus(await response.json());
}

export function baselineSummary() {
  return structuredClone(baseline);
}

function server(env) {
  const mcp = new McpServer({ name: 'KWG Gold Research', version: '1.0.0' });
  mcp.registerTool('get_gold_status', {
    description: 'Read the current VT Markets demo gold observer status. Observation only; no order controls.',
  }, async () => {
    try {
      return { content: [{ type: 'text', text: JSON.stringify(await goldStatus(env)) }] };
    } catch {
      return { isError: true, content: [{ type: 'text', text: 'Gold observer status is unavailable.' }] };
    }
  });
  mcp.registerTool('get_baseline_summary', {
    description: 'Read the frozen offline gold baseline summary and its evidence limits. No raw data or order controls.',
  }, async () => ({ content: [{ type: 'text', text: JSON.stringify(baselineSummary()) }] }));
  return mcp;
}

function tokenMatches(request, token) {
  const supplied = request.headers.get('authorization');
  if (!supplied?.startsWith('Bearer ') || supplied.length !== token.length + 7) return false;
  let mismatch = 0;
  for (let i = 0; i < token.length; i++) mismatch |= supplied.charCodeAt(i + 7) ^ token.charCodeAt(i);
  return mismatch === 0;
}

export default {
  fetch(request, env, ctx) {
    if (new URL(request.url).pathname !== '/mcp') return new Response('Not found', { status: 404 });
    if (typeof env.MCP_BEARER_TOKEN !== 'string' || !/^[a-f0-9]{64}$/i.test(env.MCP_BEARER_TOKEN)) {
      return new Response('MCP not configured', { status: 503, headers: { 'Cache-Control': 'no-store' } });
    }
    if (!tokenMatches(request, env.MCP_BEARER_TOKEN)) {
      return new Response('Unauthorized', { status: 401, headers: { 'Cache-Control': 'no-store' } });
    }
    return createMcpHandler(() => server(env))(request, env, ctx);
  },
};
