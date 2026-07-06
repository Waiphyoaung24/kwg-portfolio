import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';
import { currentStage, blockedOnWho, daysWaiting, preContractWarning } from '../../server/pipeline.mjs';

export const prerender = false;

export async function GET() {
  await initDb();

  const projects = await sql`SELECT * FROM projects ORDER BY created_date DESC`;
  const stages = await sql`SELECT project_id, ord, name, owner_type, status, blocked_since FROM project_stages ORDER BY ord`;
  const byProject = new Map<number, any[]>();
  for (const s of stages) (byProject.get(s.project_id) ?? byProject.set(s.project_id, []).get(s.project_id))!.push(s);

  const now = new Date();
  const rows = projects.map((p) => {
    const ss = byProject.get(p.id) ?? [];
    const cs = currentStage(ss);
    return {
      ...p,
      current_stage: cs?.name ?? null,
      blocked_on: blockedOnWho(ss),
      days_waiting: cs ? daysWaiting(cs.blocked_since, now) : 0,
      warn: preContractWarning(ss),
    };
  });
  return Response.json(rows);
}

export async function POST({ request }: APIContext) {
  await initDb();

  const { client_name, project_type_id } = await request.json();
  if (!client_name || !project_type_id) return new Response('bad request', { status: 400 });

  const [tpl] = await sql`
    SELECT id FROM pipeline_templates WHERE project_type_id = ${project_type_id} ORDER BY version DESC LIMIT 1`;
  if (!tpl) return new Response('no pipeline for type', { status: 400 });

  const id = await sql.begin(async (tx) => {
    const [proj] = await tx`
      INSERT INTO projects (client_name, project_type_id, pipeline_template_id)
      VALUES (${client_name}, ${project_type_id}, ${tpl.id}) RETURNING id`;
    // ponytail: clone stage_templates → project_stages so template edits never touch live projects.
    await tx`
      INSERT INTO project_stages (project_id, stage_template_id, ord, name, owner_type, required_documents)
      SELECT ${proj.id}, id, ord, name, owner_type, required_documents
      FROM stage_templates WHERE pipeline_template_id = ${tpl.id} ORDER BY ord`;
    await tx`INSERT INTO activity_log (project_id, action) VALUES (${proj.id}, 'project created')`;
    return proj.id;
  });
  return Response.json({ id }, { status: 201 });
}
