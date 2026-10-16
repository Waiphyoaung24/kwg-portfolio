// Owner sign-in for finance: one scrypt-hashed password from the server's
// environment, database-backed sessions, and a failed-attempt limit.
import {
  createHash,
  randomBytes,
  scrypt as scryptCb,
  timingSafeEqual,
} from 'node:crypto';
import type { ScryptOptions } from 'node:crypto';
import type { Sql } from './db.ts';

const scrypt = (pw: string, salt: Buffer, len: number, opts: ScryptOptions) =>
  new Promise<Buffer>((resolve, reject) =>
    scryptCb(pw, salt, len, opts, (err, key) =>
      err ? reject(err) : resolve(key),
    ),
  );

export const COOKIE = 'kwg_fin';
export const COOKIE_PATH = '/vault/finance';
export const SESSION_DAYS = 30;
const WINDOW_MINUTES = 15;
const MAX_FAILS_PER_CLIENT = 5;
const MAX_FAILS_TOTAL = 30;

// Stored as scrypt:N:r:p:salt:hash with base64url parts — no "$", so the
// value survives Docker Compose variable interpolation unescaped.
export async function hashPassword(
  password: string,
  N = 2 ** 15,
  r = 8,
  p = 1,
): Promise<string> {
  const salt = randomBytes(16);
  const key = await scrypt(password, salt, 32, {
    N,
    r,
    p,
    maxmem: 256 * N * r,
  });
  return [
    'scrypt',
    N,
    r,
    p,
    salt.toString('base64url'),
    key.toString('base64url'),
  ].join(':');
}

export class AuthConfigError extends Error {}

export async function verifyPassword(
  password: string,
  stored: string,
): Promise<boolean> {
  const parts = stored.trim().split(':');
  const [tag, n, r, p, saltText = '', hashText = ''] = parts;
  const N = Number(n),
    R = Number(r),
    P = Number(p);
  const salt = Buffer.from(saltText, 'base64url');
  const expected = Buffer.from(hashText, 'base64url');
  // A truncated value must never verify: scrypt with a 0-byte key length
  // returns an empty buffer, and two empty buffers compare equal.
  const valid =
    parts.length === 6 &&
    tag === 'scrypt' &&
    Number.isInteger(N) &&
    N >= 2 ** 14 &&
    N <= 2 ** 20 &&
    (N & (N - 1)) === 0 &&
    Number.isInteger(R) &&
    R >= 1 &&
    R <= 32 &&
    Number.isInteger(P) &&
    P >= 1 &&
    P <= 16 &&
    salt.length >= 16 &&
    expected.length === 32;
  if (!valid) {
    throw new AuthConfigError(
      'FINANCE_PASSWORD_HASH is not a scrypt hash from scripts/finance-password-hash.mjs',
    );
  }
  const key = await scrypt(password, salt, expected.length, {
    N,
    r: R,
    p: P,
    maxmem: 256 * N * R,
  });
  return timingSafeEqual(key, expected);
}

function digest(token: string): Buffer {
  return createHash('sha256').update(token).digest();
}

export async function createSession(sql: Sql): Promise<string> {
  const token = randomBytes(32).toString('base64url');
  await sql`insert into fin_sessions (token_hash, expires_at)
    values (${digest(token)}, now() + ${SESSION_DAYS + ' days'}::interval)`;
  await sql`delete from fin_sessions where expires_at < now()`;
  return token;
}

export async function sessionValid(
  sql: Sql,
  token: string | undefined,
): Promise<boolean> {
  if (!token || token.length > 100) return false;
  const rows = await sql`select 1 from fin_sessions
    where token_hash = ${digest(token)} and expires_at > now()`;
  return rows.length === 1;
}

export async function endSession(
  sql: Sql,
  token: string | undefined,
): Promise<void> {
  if (token)
    await sql`delete from fin_sessions where token_hash = ${digest(token)}`;
}

export async function endAllSessions(sql: Sql): Promise<void> {
  await sql`delete from fin_sessions`;
}

// Records the attempt as a failure *before* the slow password check, then
// counts. Parallel guesses therefore see each other, so no more than the
// limit are ever verified. A blocked attempt is removed again so it does not
// extend the lockout. Returns null when blocked.
export async function beginAttempt(
  sql: Sql,
  clientKey: string,
): Promise<bigint | null> {
  await sql`delete from fin_login_attempts where attempted_at < now() - interval '1 day'`;
  const [{ id }] = await sql<{ id: bigint }[]>`
    insert into fin_login_attempts (client_key, succeeded) values (${clientKey}, false) returning id`;
  const [row] = await sql<{ mine: bigint; total: bigint }[]>`
    select count(*) filter (where client_key = ${clientKey}) as mine, count(*) as total
    from fin_login_attempts
    where not succeeded and attempted_at > now() - ${WINDOW_MINUTES + ' minutes'}::interval`;
  if (
    row.mine > BigInt(MAX_FAILS_PER_CLIENT) ||
    row.total > BigInt(MAX_FAILS_TOTAL)
  ) {
    await sql`delete from fin_login_attempts where id = ${id}`;
    return null;
  }
  return id;
}

export async function finishAttempt(
  sql: Sql,
  id: bigint,
  succeeded: boolean | null,
): Promise<void> {
  // null: the check itself could not run (misconfiguration), so it is not a guess.
  if (succeeded === null)
    await sql`delete from fin_login_attempts where id = ${id}`;
  else if (succeeded)
    await sql`update fin_login_attempts set succeeded = true where id = ${id}`;
}

export const LOCKOUT_MINUTES = WINDOW_MINUTES;

// Only same-site relative paths under finance may be a post-sign-in target.
export function safeNext(next: string | null): string {
  if (
    !next ||
    !next.startsWith(COOKIE_PATH) ||
    next.startsWith('//') ||
    /[\\\r\n]/.test(next)
  ) {
    return COOKIE_PATH;
  }
  const rest = next.slice(COOKIE_PATH.length);
  return rest === '' || rest.startsWith('/') || rest.startsWith('?')
    ? next
    : COOKIE_PATH;
}
