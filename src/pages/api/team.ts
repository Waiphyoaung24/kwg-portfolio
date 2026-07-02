import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';
import { guard } from '../../server/guard';

export const prerender = false;

export async function GET({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  return Response.json(await sql`SELECT * FROM team_members ORDER BY name`);
}

export async function POST({ request }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  const b = await request.json();
  if (!b.name) return new Response('name required', { status: 400 });
  const [row] = await sql`
    INSERT INTO team_members (name, role, contact) VALUES (${b.name}, ${b.role ?? ''}, ${b.contact ?? ''}) RETURNING id`;
  return Response.json({ id: row.id }, { status: 201 });
}
