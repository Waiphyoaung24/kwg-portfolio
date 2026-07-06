import type { APIContext } from 'astro';
import { sql, initDb } from '../../../server/db';

export const prerender = false;

export async function PATCH({ request, params }: APIContext) {
  await initDb();
  const id = Number(params.id);
  const body = await request.json();

  const [stage] = await sql`SELECT * FROM project_stages WHERE id = ${id}`;
  if (!stage) return new Response('not found', { status: 404 });

  const status: string = body.status ?? stage.status;
  if ((status === 'waiting_on_client' || status === 'blocked_internal') && !body.blocked_reason)
    return new Response('blocked_reason required', { status: 400 });
  if (status === 'skipped' && (!body.skip_reason || !body.approved_by))
    return new Response('skip_reason and approved_by required', { status: 400 });

  const now = new Date();
  await sql.begin(async (tx) => {
    await tx`
      UPDATE project_stages SET
        status = ${status},
        notes = ${body.notes ?? stage.notes},
        blocked_reason = ${status === 'waiting_on_client' || status === 'blocked_internal' ? body.blocked_reason : null},
        blocked_since = ${status === 'waiting_on_client' ? (stage.blocked_since ?? now) : null},
        started_at = ${stage.started_at ?? (status === 'in_progress' ? now : null)},
        completed_at = ${status === 'done' ? (stage.completed_at ?? now) : stage.completed_at}
      WHERE id = ${id}`;

    const action =
      status === 'skipped'
        ? `skipped "${stage.name}" — ${body.skip_reason} (approved by ${body.approved_by})`
        : `"${stage.name}" → ${status}${body.blocked_reason ? ' — ' + body.blocked_reason : ''}`;
    await tx`INSERT INTO activity_log (project_id, action) VALUES (${stage.project_id}, ${action})`;
  });
  return Response.json({ ok: true });
}
