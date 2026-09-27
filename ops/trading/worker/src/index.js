const noStore = { 'Cache-Control': 'no-store', 'Content-Type': 'application/json; charset=utf-8' };

function unavailable(reason = 'Trading status is unavailable') {
  return Response.json(
    { mode: 'signal-only', symbol: 'XAUUSD-VIP', status: 'offline', signal: 'none', reason, checked_at: null, bar_time: null },
    { status: 503, headers: noStore },
  );
}

export function normalizeStatus(value, now = Date.now() / 1000) {
  if (!value || value.mode !== 'signal-only' || value.symbol !== 'XAUUSD-VIP') throw new Error('Invalid status');
  if (!['baseline', 'observed', 'duplicate', 'blocked', 'offline'].includes(value.status)) throw new Error('Invalid status');
  if (!['long', 'short', 'none'].includes(value.signal)) throw new Error('Invalid signal');
  if (!Number.isInteger(value.checked_at) || (value.bar_time !== null && !Number.isInteger(value.bar_time))) throw new Error('Invalid time');
  const stale = value.checked_at > now || now - value.checked_at > 45;
  const status = stale ? 'offline' : value.status;
  return {
    mode: 'signal-only', symbol: 'XAUUSD-VIP', status,
    signal: status === 'offline' || status === 'blocked' ? 'none' : value.signal,
    reason: stale ? 'Observer heartbeat missing' : String(value.reason || '').slice(0, 200),
    checked_at: value.checked_at, bar_time: value.bar_time,
  };
}

export default {
  async fetch(request, env, ctx) {
    if (request.method !== 'GET' || new URL(request.url).pathname !== '/api/trading/status') {
      return new Response('Not found', { status: 404 });
    }
    if (!ctx.access || !env.ALLOWED_VIEWER_EMAIL) return new Response('Access required', { status: 403 });
    const identity = await ctx.access.getIdentity();
    if (identity?.email?.toLowerCase() !== env.ALLOWED_VIEWER_EMAIL.toLowerCase()) {
      return new Response('Access required', { status: 403 });
    }
    if (!env.STATUS_ORIGIN_URL || !env.STATUS_ACCESS_CLIENT_ID || !env.STATUS_ACCESS_CLIENT_SECRET) {
      return unavailable();
    }
    try {
      const response = await fetch(env.STATUS_ORIGIN_URL, {
        headers: {
          'CF-Access-Client-ID': env.STATUS_ACCESS_CLIENT_ID,
          'CF-Access-Client-Secret': env.STATUS_ACCESS_CLIENT_SECRET,
        },
        redirect: 'manual', cache: 'no-store', signal: AbortSignal.timeout(5000),
      });
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) return unavailable();
      return Response.json(normalizeStatus(await response.json()), { headers: noStore });
    } catch {
      return unavailable();
    }
  },
};
