// Guards Vault Finance. Every other route passes straight through.
import { defineMiddleware } from 'astro:middleware';
import { COOKIE, COOKIE_PATH, sessionValid } from './lib/finance/auth.ts';
import { db } from './lib/finance/db.ts';

const LOGIN = `${COOKIE_PATH}/login`;
const SAFE = new Set(['GET', 'HEAD', 'OPTIONS']);

function isFinance(path: string): boolean {
  return path === COOKIE_PATH || path.startsWith(`${COOKIE_PATH}/`);
}

// Astro's checkOrigin covers form posts; this also covers any other body
// type, and refuses a request a browser marks as coming from another site.
function crossSite(request: Request, url: URL): boolean {
  const site = request.headers.get('sec-fetch-site');
  if (site) return site !== 'same-origin';
  const origin = request.headers.get('origin');
  if (origin) {
    try {
      return new URL(origin).host !== url.host;
    } catch {
      return true;
    }
  }
  return false;
}

function secure(res: Response): Response {
  // Redirect responses can carry immutable headers; copy when needed.
  let out = res;
  try {
    out.headers.set('Cache-Control', 'no-store');
  } catch {
    out = new Response(res.body, res);
    out.headers.set('Cache-Control', 'no-store');
  }
  out.headers.set('X-Robots-Tag', 'noindex, nofollow');
  // Not no-referrer: that makes browsers send "Origin: null" on form posts,
  // which checkOrigin then refuses. same-origin still hides finance URLs
  // from every other site.
  out.headers.set('Referrer-Policy', 'same-origin');
  out.headers.set('X-Content-Type-Options', 'nosniff');
  out.headers.set('X-Frame-Options', 'DENY');
  return out;
}

const CONNECTION_CODES = new Set([
  'ECONNREFUSED',
  'ECONNRESET',
  'ENOTFOUND',
  'EAI_AGAIN',
  'ETIMEDOUT',
  'CONNECT_TIMEOUT',
  'CONNECTION_CLOSED',
  'CONNECTION_ENDED',
  'CONNECTION_DESTROYED',
  '57P03',
]);

function isConnectionError(err: unknown): boolean {
  const code = (err as { code?: unknown })?.code;
  return (
    (typeof code === 'string' && CONNECTION_CODES.has(code)) ||
    (err instanceof Error && err.message === 'DATABASE_URL is not set')
  );
}

// Plain inline page: it must render when nothing else can. Colours mirror
// --c-canvas, --c-body and --c-ink from src/styles/_vars.scss.
function unavailable(): Response {
  return new Response(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">' +
      '<title>Finance unavailable</title>' +
      '<body style="background:#0a0a0a;color:#dadbdf;font:16px/1.5 system-ui;padding:48px 24px">' +
      '<h1 style="font-weight:400;color:#fff">Finance is unavailable right now</h1>' +
      '<p>The database could not be reached. Nothing you entered earlier is lost. Try again in a minute.</p>',
    {
      status: 503,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Retry-After': '60',
      },
    },
  );
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { url, request } = context;
  if (!isFinance(url.pathname)) return next();

  if (!SAFE.has(request.method) && crossSite(request, url)) {
    return secure(new Response('Cross-site request refused', { status: 403 }));
  }

  try {
    if (url.pathname !== LOGIN) {
      const sql = await db();
      if (!(await sessionValid(sql, context.cookies.get(COOKIE)?.value))) {
        const back = SAFE.has(request.method)
          ? url.pathname + url.search
          : url.pathname;
        return secure(
          context.redirect(`${LOGIN}?next=${encodeURIComponent(back)}`, 303),
        );
      }
    }
    return secure(await next());
  } catch (err) {
    if (!isConnectionError(err)) throw err;
    console.error('[finance] database unreachable', err);
    return secure(unavailable());
  }
});
