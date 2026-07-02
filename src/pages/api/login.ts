import type { APIContext } from 'astro';
import { checkPassword, sessionCookie } from '../../server/auth.mjs';

export const prerender = false;

export async function POST({ request }: APIContext) {
  const { password } = await request.json().catch(() => ({ password: '' }));
  if (!checkPassword(password)) return new Response('nope', { status: 401 });
  return new Response(null, { status: 204, headers: { 'set-cookie': sessionCookie() } });
}
