import type { APIContext } from 'astro';
import { sql, initDb } from '../../../../server/db';
import { guard } from '../../../../server/guard';

export const prerender = false;

export async function POST({ request, params }: APIContext) {
  const denied = guard(request);
  if (denied) return denied;
  await initDb();
  const b = await request.json();
  if (!b.team_member_id) return new Response('team_member_id required', { status: 400 });
  const [row] = await sql`
    INSERT INTO project_assignments (project_id, team_member_id, role_on_project)
    VALUES (${Number(params.id)}, ${b.team_member_id}, ${b.role_on_project ?? ''}) RETURNING id`;
  return Response.json({ id: row.id }, { status: 201 });
}
