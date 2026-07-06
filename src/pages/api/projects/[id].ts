import type { APIContext } from 'astro';
import { sql, initDb } from '../../../server/db';
import { blockedOnWho, preContractWarning } from '../../../server/pipeline.mjs';

export const prerender = false;

export async function GET({ params }: APIContext) {
  await initDb();
  const id = Number(params.id);

  const [project] = await sql`SELECT * FROM projects WHERE id = ${id}`;
  if (!project) return new Response('not found', { status: 404 });
  const stages = await sql`SELECT * FROM project_stages WHERE project_id = ${id} ORDER BY ord`;
  const documents = await sql`
    SELECT d.* FROM documents d JOIN project_stages s ON s.id = d.project_stage_id
    WHERE s.project_id = ${id} ORDER BY d.uploaded_at DESC`;
  const activity = await sql`SELECT * FROM activity_log WHERE project_id = ${id} ORDER BY timestamp DESC`;

  return Response.json({
    project,
    stages,
    documents,
    activity,
    rollup: { blocked_on: blockedOnWho(stages), warn: preContractWarning(stages) },
  });
}
