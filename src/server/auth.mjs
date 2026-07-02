import crypto from 'node:crypto';

const SECRET = process.env.APP_SECRET || 'dev-insecure-secret';
const COOKIE = 'kwg_pw';
const PAYLOAD = 'ok';

const hmac = (v) => crypto.createHmac('sha256', SECRET).update(v).digest('hex');

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
  return `${COOKIE}=${sign(PAYLOAD)}; HttpOnly; SameSite=Lax; Path=/; Max-Age=2592000`;
}
export function clearCookie() {
  return `${COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0`;
}
export function isAuthed(request) {
  const cookie = request.headers.get('cookie') || '';
  const match = cookie.split(';').map((c) => c.trim()).find((c) => c.startsWith(COOKIE + '='));
  if (!match) return false;
  return verify(match.slice(COOKIE.length + 1)) === PAYLOAD;
}
