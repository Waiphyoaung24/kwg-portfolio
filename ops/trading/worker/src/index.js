const noStore = { 'Cache-Control': 'no-store', 'Content-Type': 'application/json; charset=utf-8' };

function unavailable(reason = 'Trading status is unavailable') {
  return Response.json(
    { mode: 'signal-only', symbol: 'XAUUSD-VIP', status: 'offline', signal: 'none', reason, checked_at: null, bar_time: null },
    { status: 503, headers: noStore },
  );
}

function normalizeExecution(value, now) {
  if (value === null) return null;
  if (!value || value.mode !== 'one-shot-demo' ||
      !['disarmed', 'armed', 'submitting', 'pending', 'open', 'closing', 'closed', 'needs_attention'].includes(value.status) ||
      !Number.isFinite(value.updated_at) || value.updated_at <= 0 || value.updated_at > now ||
      (value.side !== null && !['buy', 'sell'].includes(value.side))) throw new Error('Invalid execution');
  const execution = { mode: 'one-shot-demo', status: value.status,
    updated_at: value.updated_at, side: value.side };
  for (const key of ['volume', 'opened_at', 'closed_at', 'realized_net_usd', 'entry_price', 'sl', 'tp']) {
    const number = value[key] ?? null;
    if (number !== null && (typeof number !== 'number' || !Number.isFinite(number) || Math.abs(number) > 1e12 ||
        (key !== 'realized_net_usd' && number <= 0))) throw new Error('Invalid execution number');
    execution[key] = number;
  }
  if (value.close_reason != null && (typeof value.close_reason !== 'string' || value.close_reason.length > 160)) throw new Error('Invalid execution reason');
  execution.close_reason = value.close_reason ?? null;
  if (value.status === 'closed' && (execution.closed_at === null || execution.realized_net_usd === null)) throw new Error('Invalid closed result');
  if (!['disarmed', 'closed'].includes(value.status) && now - value.updated_at > 30) return null;
  return execution;
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
  const result = {
    mode: 'signal-only', symbol: 'XAUUSD-VIP', status,
    signal: status === 'offline' || status === 'blocked' ? 'none' : value.signal,
    reason: stale ? 'Observer heartbeat missing' : String(value.reason || '').slice(0, 200),
    checked_at: value.checked_at, bar_time: value.bar_time, health,
  };
  if (value.execution !== undefined) result.execution = normalizeExecution(value.execution, now);
  return result;
}

export default {
  async fetch(request, env, ctx) {
    const pathname = new URL(request.url).pathname;
    const pagePath = ['/vault/trading', '/vault/trading/', '/vault/trading-bot', '/vault/trading-bot/'].includes(pathname)
      ? pathname.replace(/\/$/, '') : null;
    const isPage = pagePath !== null;
    const action = pathname === '/api/trading/preview' ? 'preview' : pathname === '/api/trading/arm' ? 'arm' : null;
    if (!(request.method === 'GET' && (isPage || pathname === '/api/trading/status')) &&
        !(request.method === 'POST' && action)) {
      return new Response('Not found', { status: 404 });
    }
    if (!ctx.access || !env.ALLOWED_VIEWER_EMAIL) return new Response('Access required', { status: 403 });
    const identity = await ctx.access.getIdentity();
    if (identity?.email?.toLowerCase() !== env.ALLOWED_VIEWER_EMAIL.toLowerCase()) {
      return new Response('Access required', { status: 403 });
    }
    if (isPage) {
      try {
        // A route Worker fetches the existing Dokploy origin, not itself.
        const response = await fetch(request, {
          headers: { Accept: 'text/html' }, redirect: 'manual', cache: 'no-store',
          signal: AbortSignal.timeout(5000),
        });
        if (!response.ok || !response.headers.get('content-type')?.includes('text/html')) return unavailable();
        return new Response(response.body, { headers: {
          'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
          'X-Robots-Tag': 'noindex', 'X-Content-Type-Options': 'nosniff',
        } });
      } catch {
        return unavailable();
      }
    }
    if (!env.STATUS_ORIGIN_URL || !env.STATUS_ACCESS_CLIENT_ID || !env.STATUS_ACCESS_CLIENT_SECRET) {
      return unavailable();
    }
    if (action) {
      if (!env.TRADING_CONTROL_SECRET) return Response.json({ error: 'Demo control is unavailable.' }, { status: 503, headers: noStore });
      if (request.headers.get('Origin') !== new URL(request.url).origin ||
          (request.headers.get('Sec-Fetch-Site') && request.headers.get('Sec-Fetch-Site') !== 'same-origin') ||
          request.headers.get('Content-Type') !== 'application/json' ||
          Number(request.headers.get('Content-Length') || 0) > 256) {
        return Response.json({ error: 'Invalid demo request.' }, { status: 400, headers: noStore });
      }
      let body;
      try {
        const raw = await request.text();
        if (raw.length > 256) throw new Error('Oversized request');
        body = JSON.parse(raw);
        if (!body || typeof body !== 'object' || Array.isArray(body) ||
            (action === 'preview' && (Object.keys(body).sort().join() !== 'entry,side,sl,tp' ||
              !['buy', 'sell'].includes(body.side) ||
              ![body.entry, body.sl, body.tp].every(x => typeof x === 'number' && Number.isFinite(x) && x > 0 && x <= 1e6))) ||
            (action === 'arm' && (Object.keys(body).join() !== 'token' || !/^[A-Za-z0-9_-]{32}$/.test(body.token)))) {
          throw new Error('Invalid request');
        }
      } catch {
        return Response.json({ error: 'Invalid demo request.' }, { status: 400, headers: noStore });
      }
      try {
        const origin = new URL(env.STATUS_ORIGIN_URL);
        origin.pathname = `/control/${action}`;
        const response = await fetch(origin, {
          method: 'POST',
          headers: { 'CF-Access-Client-ID': env.STATUS_ACCESS_CLIENT_ID,
            'CF-Access-Client-Secret': env.STATUS_ACCESS_CLIENT_SECRET,
            'X-KWG-Control-Secret': env.TRADING_CONTROL_SECRET,
            'Content-Type': 'application/json' },
          body: JSON.stringify(body), redirect: 'manual', cache: 'no-store', signal: AbortSignal.timeout(55000),
        });
        if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Invalid response');
        const result = await response.json();
        if (!response.ok) {
          return Response.json({ error: typeof result.error === 'string' && result.error.length < 160
            ? result.error : 'Demo control is unavailable.' }, { status: response.status === 409 ? 409 : 503, headers: noStore });
        }
        if (action === 'arm') {
          if (response.status !== 202 || result.status !== 'starting') throw new Error('Invalid arm response');
          return Response.json({ status: 'starting' }, { status: 202, headers: noStore });
        }
        const p = result.preview;
        if (p?.mode !== 'private-demo-preview' || p.symbol !== 'XAUUSD-VIP' || p.side !== body.side ||
            p.order_sent !== false || p.order_check_passed !== false ||
            !/^[A-Za-z0-9_-]{32}$/.test(result.token) ||
            ![p.volume, p.quote_reference, p.sl, p.tp, p.modeled_stop_usd,
              p.modeled_stop_pct_of_equity, p.previewed_at].every(x => typeof x === 'number' && Number.isFinite(x) && x > 0) ||
            p.volume !== .01 || p.modeled_stop_pct_of_equity > .1 ||
            p.quote_reference !== body.entry || p.sl !== body.sl || p.tp !== body.tp ||
            p.pending_until_cancelled !== true ||
            !['Buy limit', 'Buy stop', 'Sell limit', 'Sell stop'].includes(p.order_kind) ||
            !p.order_kind.toLowerCase().startsWith(body.side)) throw new Error('Invalid preview');
        return Response.json({ preview: { side: p.side, symbol: p.symbol, volume: p.volume,
          quote_reference: p.quote_reference, sl: p.sl, tp: p.tp,
          modeled_stop_usd: p.modeled_stop_usd,
          modeled_stop_pct_of_equity: p.modeled_stop_pct_of_equity,
          order_kind: p.order_kind, pending_until_cancelled: true,
          previewed_at: p.previewed_at }, token: result.token }, { headers: noStore });
      } catch {
        return Response.json({ error: 'Demo control is unavailable.' }, { status: 503, headers: noStore });
      }
    }
    try {
      const origin = new URL(env.STATUS_ORIGIN_URL);
      const response = await fetch(origin, {
        headers: {
          'CF-Access-Client-ID': env.STATUS_ACCESS_CLIENT_ID,
          'CF-Access-Client-Secret': env.STATUS_ACCESS_CLIENT_SECRET,
        },
        redirect: 'manual', cache: 'no-store', signal: AbortSignal.timeout(5000),
      });
      if (!response.ok) return unavailable();
      if (!response.headers.get('content-type')?.includes('application/json')) return unavailable();
      return Response.json(normalizeStatus(await response.json()), { headers: noStore });
    } catch {
      return unavailable();
    }
  },
};
