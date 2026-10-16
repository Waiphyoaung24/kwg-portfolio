// Runs against a real, disposable Postgres. Set FINANCE_TEST_DATABASE_URL to a
// database this test may wipe, e.g. postgres://kwg@127.0.0.1:5433/kwg_test.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { after, before, test } from 'node:test';
import {
  beginAttempt,
  createSession,
  endAllSessions,
  endSession,
  finishAttempt,
  hashPassword,
  sessionValid,
  verifyPassword,
} from './auth.ts';
import { connect, migrate, type Sql } from './db.ts';
import { MIGRATIONS } from './schema.ts';
import { parseEntry, type EntryForm } from './entries.ts';
import {
  LedgerError,
  createAccount,
  lastUsedAccount,
  loadAccounts,
  post,
  setArchived,
  voidTransaction,
} from './ledger.ts';
import {
  accountHistory,
  balanceSheet,
  balances,
  monthEntries,
  monthSpending,
} from './reports.ts';

const url = process.env.FINANCE_TEST_DATABASE_URL;
// The suite drops the whole public schema, so it refuses any database whose
// name does not end in _test (the site's own database is "kwg").
const safe = !!url && /_test$/.test(new URL(url).pathname.slice(1));
const opts = {
  skip: !url
    ? 'FINANCE_TEST_DATABASE_URL is not set'
    : !safe
      ? 'FINANCE_TEST_DATABASE_URL must name a database ending in _test'
      : false,
};
let sql: Sql;

before(async () => {
  if (!url || !safe) return;
  sql = connect(url);
  await sql.unsafe('drop schema public cascade; create schema public;');
  await migrate(sql);
});
after(async () => {
  await sql?.end();
});

const form = (f: Partial<EntryForm>): EntryForm => ({
  kind: 'expense',
  amount: '',
  account: '',
  category: '',
  to: '',
  toAmount: '',
  date: '2026-10-16',
  note: '',
  ...f,
});

async function entry(f: Partial<EntryForm>) {
  const accounts = await loadAccounts(sql);
  const r = parseEntry(form(f), accounts);
  if (!r.ok) throw new Error(JSON.stringify(r.errors));
  return post(sql, r.draft, accounts);
}

const idOf = async (name: string) =>
  [...(await loadAccounts(sql)).values()].find((a) => a.name === name)!.id;

test(
  'migrations are idempotent and seed system accounts and categories',
  opts,
  async () => {
    await migrate(sql);
    await Promise.all([migrate(sql), migrate(sql)]);
    const accounts = [...(await loadAccounts(sql)).values()];
    assert.deepEqual(
      accounts
        .filter((a) => a.system_key)
        .map((a) => a.system_key)
        .sort(),
      ['client_cost', 'client_sales', 'fx', 'opening', 'revaluation'],
    );
    assert.equal(
      accounts.filter((a) => a.type === 'expense' && !a.system_key).length,
      7,
    );
    const [{ n }] = await sql<
      { n: bigint }[]
    >`select count(*) as n from fin_schema_migrations`;
    assert.equal(n, BigInt(MIGRATIONS.length));
  },
);

test(
  'a full month: accounts, entries, voids and the balance sheet',
  opts,
  async () => {
    await createAccount(
      sql,
      { name: 'KBank', type: 'asset', currency: 'THB', scope: 'personal' },
      { amount: 4000000n, occurredOn: '2026-10-01' },
    );
    await createAccount(
      sql,
      {
        name: 'KTC card',
        type: 'liability',
        currency: 'THB',
        scope: 'personal',
      },
      { amount: 50000n, occurredOn: '2026-10-01' },
    );
    await createAccount(
      sql,
      { name: 'KBZPay', type: 'asset', currency: 'MMK', scope: 'personal' },
      { amount: 300000n, occurredOn: '2026-10-01' },
    );
    await createAccount(
      sql,
      { name: 'Wise', type: 'asset', currency: 'USD', scope: 'business' },
      { amount: 0n, occurredOn: '2026-10-01' },
    );

    const kbank = await idOf('KBank'),
      card = await idOf('KTC card'),
      kbz = await idOf('KBZPay'),
      wise = await idOf('Wise');
    const food = await idOf('Food'),
      fee = await idOf('Project fee');

    await entry({
      amount: '60',
      account: String(kbank),
      category: String(food),
      note: 'Lunch',
    });
    await entry({
      amount: '1,284.50',
      account: String(card),
      category: String(food),
    });
    await entry({
      amount: '4,500',
      account: String(kbz),
      category: String(food),
    });
    await entry({
      kind: 'income',
      amount: '12,000',
      account: String(kbank),
      category: String(fee),
    });
    await entry({
      kind: 'transfer',
      amount: '3,000',
      account: String(kbank),
      to: String(wise),
      toAmount: '92.50',
      date: '2026-10-14',
    });
    const wrong = await entry({
      amount: '3,990',
      account: String(kbank),
      category: String(food),
      note: 'Phone (wrong)',
    });
    assert.equal(await voidTransaction(sql, wrong), true);
    assert.equal(
      await voidTransaction(sql, wrong),
      false,
      'second void is refused',
    );

    const accounts = await loadAccounts(sql);
    const cols = balanceSheet(
      accounts,
      await balances(sql, '2026-10-31'),
      'all',
    );
    const thb = cols.find((c) => c.currency === 'THB')!;
    // 40,000 − 60 + 12,000 − 3,000 = 48,940; card 500 + 1,284.50 owed.
    assert.equal(thb.ownTotal, 4894000n);
    assert.equal(thb.oweTotal, 178450n);
    assert.equal(thb.net, 4715550n);
    for (const c of cols) assert.equal(c.balanced, true, c.currency);
    assert.equal(cols.find((c) => c.currency === 'USD')!.net, 9250n);
    assert.equal(cols.find((c) => c.currency === 'MMK')!.net, 295500n);

    // As-of date respects history: before the transfer, Wise held nothing.
    const early = balanceSheet(
      accounts,
      await balances(sql, '2026-10-13'),
      'all',
    );
    assert.equal(early.find((c) => c.currency === 'USD')!.net, 0n);

    const spending = await monthSpending(sql, '2026-10');
    assert.deepEqual(spending.map((s) => [s.currency, s.total]).sort(), [
      ['MMK', 4500n],
      ['THB', 134450n],
    ]);

    const all = await monthEntries(sql, '2026-10', null);
    assert.equal(
      all.filter((t) => t.voidedAt).length,
      1,
      'voided entry stays listed',
    );
    const onlyWise = await monthEntries(sql, '2026-10', wise);
    assert.deepEqual(
      onlyWise.map((t) => t.kind),
      ['transfer'],
      'a zero opening balance records nothing',
    );

    const hist = await accountHistory(sql, kbank, '2026-10-31');
    assert.equal(hist.at(-1)!.running, 4894000n);
    assert.equal(await lastUsedAccount(sql, 'expense'), kbz);
  },
);

test(
  'the database refuses unbalanced or mismatched postings',
  opts,
  async () => {
    const kbank = await idOf('KBank'),
      food = await idOf('Food');
    await assert.rejects(
      sql.begin(async (tx) => {
        const [t] =
          await tx`insert into fin_transactions (kind, occurred_on) values ('expense', '2026-10-16') returning id`;
        await tx`insert into fin_postings (transaction_id, account_id, currency, amount_minor) values (${t.id}, ${food}, 'THB', 100)`;
        await tx`insert into fin_postings (transaction_id, account_id, currency, amount_minor) values (${t.id}, ${kbank}, 'THB', -99)`;
      }),
      /does not balance/,
    );
    await assert.rejects(
      sql.begin(async (tx) => {
        const [t] =
          await tx`insert into fin_transactions (kind, occurred_on) values ('expense', '2026-10-16') returning id`;
        await tx`insert into fin_postings (transaction_id, account_id, currency, amount_minor) values (${t.id}, ${food}, 'USD', 100)`;
        await tx`insert into fin_postings (transaction_id, account_id, currency, amount_minor) values (${t.id}, ${kbank}, 'USD', -100)`;
      }),
      /does not match account/,
    );
    // Nothing half-saved.
    const [{ n }] = await sql<
      { n: bigint }[]
    >`select count(*) as n from fin_transactions t
    where not exists (select 1 from fin_postings p where p.transaction_id = t.id)`;
    assert.equal(n, 0n);
  },
);

test(
  'the ledger refuses drafts before they reach the database',
  opts,
  async () => {
    const accounts = await loadAccounts(sql);
    const kbank = await idOf('KBank'),
      food = await idOf('Food');
    await assert.rejects(
      post(
        sql,
        {
          kind: 'expense',
          occurredOn: '2026-10-16',
          description: '',
          lines: [
            { accountId: food, currency: 'THB', amount: 100n },
            { accountId: kbank, currency: 'THB', amount: -1n },
          ],
        },
        accounts,
      ),
      LedgerError,
    );
    await setArchived(sql, kbank, true);
    await assert.rejects(
      post(
        sql,
        {
          kind: 'expense',
          occurredOn: '2026-10-16',
          description: '',
          lines: [
            { accountId: food, currency: 'THB', amount: 100n },
            { accountId: kbank, currency: 'THB', amount: -100n },
          ],
        },
        await loadAccounts(sql),
      ),
      /not available/,
    );
    await setArchived(sql, kbank, false);
  },
);

test(
  'account names are unique among live accounts of a type',
  opts,
  async () => {
    await assert.rejects(
      createAccount(
        sql,
        { name: 'kbank', type: 'asset', currency: 'THB', scope: 'personal' },
        null,
      ),
      (e: { code?: string }) => e.code === '23505',
    );
  },
);

test(
  'password hashes from the script verify, wrong passwords do not',
  opts,
  async () => {
    const stored = await hashPassword('correct horse battery');
    assert.equal(await verifyPassword('correct horse battery', stored), true);
    assert.equal(await verifyPassword('wrong', stored), false);
    const fromScript = execFileSync(
      process.execPath,
      ['scripts/finance-password-hash.mjs'],
      {
        input: 'script password 123\n',
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'ignore'],
      },
    ).trim();
    assert.match(fromScript, /^scrypt:32768:8:1:[\w-]+:[\w-]+$/);
    assert.equal(await verifyPassword('script password 123', fromScript), true);
    await assert.rejects(verifyPassword('x', 'plain-text'), /scrypt hash/);
  },
);

test('sessions: create, check, end one, end all, expire', opts, async () => {
  const a = await createSession(sql),
    b = await createSession(sql);
  assert.equal(await sessionValid(sql, a), true);
  assert.equal(await sessionValid(sql, 'forged'), false);
  assert.equal(await sessionValid(sql, undefined), false);
  await endSession(sql, a);
  assert.equal(await sessionValid(sql, a), false);
  assert.equal(await sessionValid(sql, b), true);
  await endAllSessions(sql);
  assert.equal(await sessionValid(sql, b), false);
  const c = await createSession(sql);
  await sql`update fin_sessions set expires_at = now() - interval '1 second'`;
  assert.equal(await sessionValid(sql, c), false);
});

test(
  'sign-in limit: 5 failures per client, 30 overall, inside 15 minutes',
  opts,
  async () => {
    await sql`delete from fin_login_attempts`;
    const fail = async (key: string) => {
      const id = await beginAttempt(sql, key);
      if (id !== null) await finishAttempt(sql, id, false);
      return id;
    };
    for (let i = 0; i < 5; i++)
      assert.notEqual(await fail('ip:a'), null, `attempt ${i + 1} is checked`);
    assert.equal(await beginAttempt(sql, 'ip:a'), null, 'sixth is blocked');
    const ok = await beginAttempt(sql, 'ip:b');
    assert.notEqual(ok, null);
    await finishAttempt(sql, ok!, true);
    for (let i = 0; i < 25; i++) await fail(`ip:spread-${i}`);
    assert.equal(await beginAttempt(sql, 'ip:new'), null, 'overall limit');
    await sql`update fin_login_attempts set attempted_at = now() - interval '16 minutes'`;
    assert.notEqual(await beginAttempt(sql, 'ip:a'), null, 'window passes');
  },
);

test('parallel guesses cannot get past the limit', opts, async () => {
  await sql`delete from fin_login_attempts`;
  const ids = await Promise.all(
    Array.from({ length: 40 }, () => beginAttempt(sql, 'ip:burst')),
  );
  assert.ok(
    ids.filter((id) => id !== null).length <= 5,
    'at most five passwords are ever checked',
  );
});

test('a truncated or malformed hash never verifies', opts, async () => {
  const good = await hashPassword('correct horse battery');
  const [tag, n, r, p, salt] = good.split(':');
  for (const bad of [
    `${tag}:${n}:${r}:${p}:${salt}:`,
    `${tag}:${n}:${r}:${p}:${salt}:A`,
    `${tag}:${n}:${r}:${p}::${good.split(':')[5]}`,
    `${tag}:1000:${r}:${p}:${salt}:${good.split(':')[5]}`,
    good.split(':').slice(0, 5).join(':'),
  ]) {
    await assert.rejects(verifyPassword('anything', bad), /scrypt hash/, bad);
  }
});
