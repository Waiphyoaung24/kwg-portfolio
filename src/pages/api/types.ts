import { sql, initDb } from '../../server/db';

export const prerender = false;

export async function GET() {
  await initDb();
  return Response.json(
    await sql`SELECT id, name FROM project_types ORDER BY name`,
  );
}
