import crypto from 'node:crypto';

const COOKIE = 'kwg_pw';
const PAYLOAD = 'ok';

// ponytail: fail closed — no fallback secret. If APP_SECRET is unset, auth refuses
// rather than signing with a guessable key that would let anyone forge a session.
// Read at call time (not module load) so the guard reflects the live environment.
const hmac = (v) => crypto.createHmac('sha256', process.env.APP_SECRET).update(v).digest('hex');

function sign(v) {
  return `${v}.${hmac(v)}`;
}
function verify(signed) {
  if (!signed) return null;
  const i = signed.lastIndexOf('.');
  if (i < 0) return null;
  const v = signed.slice(0, i);
  const want = Buffer.from(sign(v));
  const got = Buffer.from(signed);
  if (want.length !== got.length) return null;
  return crypto.timingSafeEqual(want, got) ? v : null;
}

export function checkPassword(input) {
  const a = Buffer.from(String(input));
  const b = Buffer.from(process.env.APP_PASSWORD || '');
  return a.length === b.length && a.length > 0 && crypto.timingSafeEqual(a, b);
}

export function sessionCookie() {
  if (!process.env.APP_SECRET) throw new Error('APP_SECRET is not set');
  return `${COOKIE}=${sign(PAYLOAD)}; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000`;
}
export function clearCookie() {
  return `${COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0`;
}
export function isAuthed(request) {
  if (!process.env.APP_SECRET) return false;
  const cookie = request.headers.get('cookie') || '';
  const match = cookie.split(';').map((c) => c.trim()).find((c) => c.startsWith(COOKIE + '='));
  if (!match) return false;
  return verify(match.slice(COOKIE.length + 1)) === PAYLOAD;
}
