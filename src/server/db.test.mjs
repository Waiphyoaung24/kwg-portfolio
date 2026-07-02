import assert from 'node:assert';
import { readFileSync } from 'node:fs';

if (!process.env.DATABASE_URL) {
  console.log('SKIP db.test — no DATABASE_URL');
  process.exit(0);
}
const postgres = (await import('postgres')).default;
const { seedIfEmpty } = await import('./seed.mjs');

const sql = postgres(process.env.DATABASE_URL);
const schema = readFileSync(new URL('../../db/schema.sql', import.meta.url), 'utf8');
await sql.unsafe(schema);
await seedIfEmpty(sql);

const types = await sql`SELECT name FROM project_types ORDER BY name`;
assert.deepStrictEqual(types.map((t) => t.name), ['Creative Website', 'POS']);
const stages = await sql`SELECT count(*)::int c FROM stage_templates`;
assert.strictEqual(stages[0].c, 24); // 12 per pipeline

await seedIfEmpty(sql); // idempotent — second call must not double-seed
const again = await sql`SELECT count(*)::int c FROM project_types`;
assert.strictEqual(again[0].c, 2);
console.log('db.test OK');
await sql.end();
