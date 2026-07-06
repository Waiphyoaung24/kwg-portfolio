import type { APIContext } from 'astro';
import { sql, initDb } from '../../server/db';

export const prerender = false;

export async function POST({ request }: APIContext) {
  await initDb();
  const b = await request.json();
  if (!b.project_stage_id || !b.filename || !b.doc_type) return new Response('bad request', { status: 400 });
  if (b.doc_type === 'brs' && !b.version_number) return new Response('version_number required for BRS', { status: 400 });

  const [row] = await sql`
    INSERT INTO documents (project_stage_id, filename, doc_type, version_number, uploaded_by, note)
    VALUES (${b.project_stage_id}, ${b.filename}, ${b.doc_type}, ${b.version_number ?? null}, ${b.uploaded_by ?? ''}, ${b.note ?? ''})
    RETURNING id`;
  const [{ project_id }] = await sql`SELECT project_id FROM project_stages WHERE id = ${b.project_stage_id}`;
  await sql`INSERT INTO activity_log (project_id, action) VALUES (${project_id}, ${'document: ' + b.filename + (b.version_number ? ' r' + b.version_number : '')})`;
  return Response.json({ id: row.id }, { status: 201 });
}
