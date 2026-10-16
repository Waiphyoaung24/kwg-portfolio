import type { APIRoute } from 'astro';
import {
  COOKIE,
  COOKIE_PATH,
  endAllSessions,
  endSession,
} from '../../../lib/finance/auth.ts';
import { db } from '../../../lib/finance/db.ts';
import { field } from '../../../lib/finance/request.ts';

export const prerender = false;

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  const sql = await db();
  const everywhere = field(await request.formData(), 'everywhere') === '1';
  if (everywhere) await endAllSessions(sql);
  else await endSession(sql, cookies.get(COOKIE)?.value);
  cookies.delete(COOKIE, { path: COOKIE_PATH });
  return redirect(`${COOKIE_PATH}/login`, 303);
};
