// One shared Postgres connection for finance, migrated on first use.
import postgres from 'postgres';
import { MIGRATIONS } from './schema.ts';

export type Sql = postgres.Sql<{ bigint: bigint }>;

let sql: Sql | undefined;
let ready: Promise<void> | undefined;

export function connect(url: string): Sql {
  // int8 comes back as a JS bigint so money never passes through Number.
  return postgres(url, {
    types: { bigint: postgres.BigInt },
    max: 5,
    onnotice: () => undefined,
  });
}

export async function migrate(db: Sql): Promise<void> {
  await db.begin(async (tx) => {
    // Serialises concurrent first requests (and app replicas).
    await tx`select pg_advisory_xact_lock(hashtext('kwg_finance_migrations'))`;
    await tx`create table if not exists fin_schema_migrations (
      version int primary key, applied_at timestamptz not null default now())`;
    const done = await tx<
      { version: number }[]
    >`select version from fin_schema_migrations`;
    const applied = new Set(done.map((r) => r.version));
    for (const [i, text] of MIGRATIONS.entries()) {
      const version = i + 1;
      if (applied.has(version)) continue;
      await tx.unsafe(text);
      await tx`insert into fin_schema_migrations (version) values (${version})`;
    }
  });
}

export async function db(): Promise<Sql> {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error('DATABASE_URL is not set');
  sql ??= connect(url);
  // A failed migration is retried on the next request rather than cached.
  ready ??= migrate(sql).catch((e) => {
    ready = undefined;
    throw e;
  });
  await ready;
  return sql;
}
