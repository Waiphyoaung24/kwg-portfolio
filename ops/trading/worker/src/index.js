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
  const stale = value.checked_at > now || now - value.checked_at > 30;
  let health = null;
  if (value.health != null) {
    const input = value.health;
    if (!['unknown', 'connected', 'disconnected', 'guard_failed'].includes(input.terminal) ||
        !['unknown', 'fresh', 'stale', 'future', 'missing', 'invalid'].includes(input.quote)) throw new Error('Invalid health');
    health = { terminal: input.terminal, quote: input.quote };
    for (const key of ['sampled_at', 'tick_time', 'tick_time_msc', 'quote_age_seconds', 'history_bar_time', 'history_count']) {
      const number = input[key] ?? null;
      if (number !== null && (typeof number !== 'number' || !Number.isFinite(number) || Math.abs(number) > 1e15)) throw new Error('Invalid health number');
      if (['history_bar_time', 'history_count'].includes(key) && number !== null && (!Number.isInteger(number) || number < 0)) throw new Error('Invalid history');
      health[key] = number;
    }
  }
  const status = stale ? 'offline' : value.status;
  return {
    mode: 'signal-only', symbol: 'XAUUSD-VIP', status,
    signal: status === 'offline' || status === 'blocked' ? 'none' : value.signal,
    reason: stale ? 'Observer heartbeat missing' : String(value.reason || '').slice(0, 200),
    checked_at: value.checked_at, bar_time: value.bar_time, health,
  };
}

export default {
  async fetch(request, env, ctx) {
    const pathname = new URL(request.url).pathname;
    const isPage = pathname === '/vault/trading' || pathname === '/vault/trading/';
    if (request.method !== 'GET' || (!isPage && pathname !== '/api/trading/status')) {
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
      const origin = new URL(env.STATUS_ORIGIN_URL);
      if (isPage) origin.pathname = '/vault/trading';
      const response = await fetch(origin, {
        headers: {
          'CF-Access-Client-ID': env.STATUS_ACCESS_CLIENT_ID,
          'CF-Access-Client-Secret': env.STATUS_ACCESS_CLIENT_SECRET,
        },
        redirect: 'manual', cache: 'no-store', signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) return unavailable();
      if (isPage) {
        if (!response.headers.get('content-type')?.includes('text/html')) return unavailable();
        return new Response(response.body, { headers: {
          'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
          'X-Robots-Tag': 'noindex', 'X-Content-Type-Options': 'nosniff',
        } });
      }
      if (!response.headers.get('content-type')?.includes('application/json')) return unavailable();
      return Response.json(normalizeStatus(await response.json()), { headers: noStore });
    } catch {
      return unavailable();
    }
  },
};
