// Writes to the ledger. Every write is one database transaction; a draft that
// does not balance is refused before it reaches the database trigger.
import type { Sql } from './db.ts';
import type { Account, AccountType, Draft, Scope } from './entries.ts';
import { openingDraft } from './entries.ts';

export class LedgerError extends Error {}

export async function loadAccounts(sql: Sql): Promise<Map<number, Account>> {
  const rows = await sql<Account[]>`
    select id, name, type, trim(currency) as currency, scope, system_key, archived_at
    from fin_accounts order by type, lower(name)`;
  return new Map(rows.map((a) => [a.id, a]));
}

export function checkDraft(draft: Draft, accounts: Map<number, Account>): void {
  if (draft.lines.length < 2)
    throw new LedgerError('A transaction needs at least two lines.');
  const sums = new Map<string, bigint>();
  for (const l of draft.lines) {
    const a = accounts.get(l.accountId);
    if (!a || a.archived_at)
      throw new LedgerError(`Account ${l.accountId} is not available.`);
    if (a.currency && a.currency !== l.currency) {
      throw new LedgerError(
        `${a.name} holds ${a.currency}, not ${l.currency}.`,
      );
    }
    if (l.amount === 0n) throw new LedgerError('A line cannot be zero.');
    sums.set(l.currency, (sums.get(l.currency) ?? 0n) + l.amount);
  }
  for (const [currency, sum] of sums) {
    if (sum !== 0n)
      throw new LedgerError(`The entry does not balance in ${currency}.`);
  }
}

async function insertDraft(tx: Sql, draft: Draft): Promise<bigint> {
  const [t] = await tx<{ id: bigint }[]>`
    insert into fin_transactions (kind, occurred_on, description)
    values (${draft.kind}, ${draft.occurredOn}, ${draft.description})
    returning id`;
  for (const l of draft.lines) {
    await tx`insert into fin_postings (transaction_id, account_id, currency, amount_minor)
      values (${t.id}, ${l.accountId}, ${l.currency}, ${l.amount})`;
  }
  return t.id;
}

export async function post(
  sql: Sql,
  draft: Draft,
  accounts: Map<number, Account>,
): Promise<bigint> {
  checkDraft(draft, accounts);
  return sql.begin((tx) => insertDraft(tx as unknown as Sql, draft));
}

// Returns false when the transaction does not exist or is already voided.
export async function voidTransaction(sql: Sql, id: bigint): Promise<boolean> {
  const rows = await sql`
    update fin_transactions set voided_at = now()
    where id = ${id} and voided_at is null returning id`;
  return rows.length === 1;
}

export interface NewAccount {
  name: string;
  type: AccountType;
  currency: string | null;
  scope: Scope;
}

// Creates an account and, for balance accounts, its opening balance, together.
export async function createAccount(
  sql: Sql,
  input: NewAccount,
  opening: { amount: bigint; occurredOn: string } | null,
): Promise<number> {
  return sql.begin(async (tx) => {
    const [row] = await tx<{ id: number }[]>`
      insert into fin_accounts (name, type, currency, scope)
      values (${input.name}, ${input.type}, ${input.currency}, ${input.scope})
      returning id`;
    if (opening) {
      const accounts = await loadAccounts(tx as unknown as Sql);
      const draft = openingDraft(
        accounts.get(row.id)!,
        opening.amount,
        opening.occurredOn,
        accounts,
      );
      if (draft) {
        checkDraft(draft, accounts);
        await insertDraft(tx as unknown as Sql, draft);
      }
    }
    return row.id;
  });
}

export async function setArchived(
  sql: Sql,
  id: number,
  archived: boolean,
): Promise<void> {
  await sql`update fin_accounts
    set archived_at = case when ${archived} then now() end
    where id = ${id} and system_key is null`;
}

// The balance account used by the most recent live entry of this kind.
export async function lastUsedAccount(
  sql: Sql,
  kind: string,
): Promise<number | null> {
  const [row] = await sql<{ id: number }[]>`
    select p.account_id as id from fin_postings p
    join fin_transactions t on t.id = p.transaction_id
    join fin_accounts a on a.id = p.account_id
    where t.kind = ${kind} and t.voided_at is null and a.archived_at is null
      and a.type in ('asset','liability')
      and (${kind} = 'income' or p.amount_minor < 0)
    order by t.created_at desc, p.id limit 1`;
  return row?.id ?? null;
}
