import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';
import { guard } from '../../server/guard';

export const prerender = false;

export async function GET({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  return Response.json(await sql`SELECT id, name FROM project_types ORDER BY name`);
}
