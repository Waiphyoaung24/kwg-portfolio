import postgres from 'postgres';
import schema from '../../db/schema.sql?raw';
import { seedIfEmpty } from './seed.mjs';

export const sql = postgres(process.env.DATABASE_URL!);

let ready: Promise<void> | undefined;
export function initDb(): Promise<void> {
  // ponytail: apply schema + seed once per process; add a migration tool when the schema churns.
  // On failure, reset so a transient boot-time DB blip doesn't cache a rejected promise
  // and 500 every later request until restart.
  return (ready ??= (async () => {
    await sql.unsafe(schema);
    await seedIfEmpty(sql);
  })().catch((e) => {
    ready = undefined;
    throw e;
  }));
}
