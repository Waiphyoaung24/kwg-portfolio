// Read side of the ledger. Queries fetch raw sums; the shaping into what a
// page shows is pure so the balance-sheet identity is unit-tested.
import type { Sql } from './db.ts';
import type { Account, Kind, Scope } from './entries.ts';

export interface Balance {
  accountId: number;
  currency: string;
  balance: bigint;
}

export async function balances(sql: Sql, asOf: string): Promise<Balance[]> {
  return sql<Balance[]>`
    select p.account_id as "accountId", trim(p.currency) as currency,
           sum(p.amount_minor)::bigint as balance
    from fin_postings p join fin_transactions t on t.id = p.transaction_id
    where t.voided_at is null and t.occurred_on <= ${asOf}
    group by p.account_id, p.currency`;
}

export async function accountBalance(
  sql: Sql,
  accountId: number,
  asOf: string,
): Promise<bigint> {
  const [row] = await sql<{ balance: bigint }[]>`
    select coalesce(sum(p.amount_minor), 0)::bigint as balance
    from fin_postings p join fin_transactions t on t.id = p.transaction_id
    where p.account_id = ${accountId} and t.voided_at is null and t.occurred_on <= ${asOf}`;
  return row.balance;
}

export function isMonth(s: string): boolean {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(s);
}

export function monthRange(month: string): { from: string; until: string } {
  const [y, m] = month.split('-').map(Number);
  const next =
    m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, '0')}`;
  return { from: `${month}-01`, until: `${next}-01` };
}

export function shiftMonth(month: string, by: number): string {
  const [y, m] = month.split('-').map(Number);
  const i = y * 12 + (m - 1) + by;
  return `${Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, '0')}`;
}

export interface TxLine {
  accountId: number;
  currency: string;
  amount: bigint;
}

export interface Tx {
  id: bigint;
  kind: Kind;
  occurredOn: string;
  description: string;
  voidedAt: Date | null;
  lines: TxLine[];
}

interface TxRow {
  id: bigint;
  kind: Kind;
  occurredOn: string;
  description: string;
  voidedAt: Date | null;
  accountId: number;
  currency: string;
  amount: bigint;
}

function group(rows: TxRow[]): Tx[] {
  const out = new Map<bigint, Tx>();
  for (const r of rows) {
    let t = out.get(r.id);
    if (!t) {
      t = {
        id: r.id,
        kind: r.kind,
        occurredOn: r.occurredOn,
        description: r.description,
        voidedAt: r.voidedAt,
        lines: [],
      };
      out.set(r.id, t);
    }
    t.lines.push({
      accountId: r.accountId,
      currency: r.currency,
      amount: r.amount,
    });
  }
  return [...out.values()];
}

// The month's entries, newest first, voided ones included so corrections stay
// visible. `accountId` keeps entries that touch that account (or category).
export async function monthEntries(
  sql: Sql,
  month: string,
  accountId: number | null,
): Promise<Tx[]> {
  const { from, until } = monthRange(month);
  const rows = await sql<TxRow[]>`
    select t.id, t.kind, to_char(t.occurred_on, 'YYYY-MM-DD') as "occurredOn",
           t.description, t.voided_at as "voidedAt",
           p.account_id as "accountId", trim(p.currency) as currency, p.amount_minor as amount
    from fin_transactions t join fin_postings p on p.transaction_id = t.id
    where t.occurred_on >= ${from} and t.occurred_on < ${until}
      and (${accountId}::int is null or exists (
        select 1 from fin_postings q where q.transaction_id = t.id and q.account_id = ${accountId}::int))
    order by t.occurred_on desc, t.id desc, p.id`;
  return group(rows);
}

export interface AccountLine {
  id: bigint;
  kind: Kind;
  occurredOn: string;
  description: string;
  amount: bigint;
  running: bigint;
}

// One account's live entries up to a date with a running balance, oldest first.
export async function accountHistory(
  sql: Sql,
  accountId: number,
  upTo: string,
): Promise<AccountLine[]> {
  const rows = await sql<Omit<AccountLine, 'running'>[]>`
    select t.id, t.kind, to_char(t.occurred_on, 'YYYY-MM-DD') as "occurredOn",
           t.description, p.amount_minor as amount
    from fin_postings p join fin_transactions t on t.id = p.transaction_id
    where p.account_id = ${accountId} and t.voided_at is null and t.occurred_on <= ${upTo}
    order by t.occurred_on, t.id, p.id`;
  let running = 0n;
  return rows.map((r) => ({ ...r, running: (running += r.amount) }));
}

export interface Spending {
  accountId: number;
  currency: string;
  total: bigint;
}

export async function monthSpending(
  sql: Sql,
  month: string,
): Promise<Spending[]> {
  const { from, until } = monthRange(month);
  return sql<Spending[]>`
    select p.account_id as "accountId", trim(p.currency) as currency,
           sum(p.amount_minor)::bigint as total
    from fin_postings p
    join fin_transactions t on t.id = p.transaction_id
    join fin_accounts a on a.id = p.account_id
    where a.type = 'expense' and t.voided_at is null
      and t.occurred_on >= ${from} and t.occurred_on < ${until}
    group by p.account_id, p.currency
    order by currency, total desc`;
}

// How a transaction reads in a table row.
export interface Described {
  category: string;
  account: string;
  amounts: { currency: string; amount: bigint }[];
}

export function describe(tx: Tx, accounts: Map<number, Account>): Described {
  const name = (id: number) => accounts.get(id)?.name ?? `#${id}`;
  const balance = tx.lines.filter((l) => {
    const t = accounts.get(l.accountId)?.type;
    return t === 'asset' || t === 'liability';
  });
  const other = tx.lines.filter((l) => !balance.includes(l));
  if (tx.kind === 'transfer') {
    const from = balance.filter((l) => l.amount < 0);
    const to = balance.filter((l) => l.amount > 0);
    return {
      category: 'Transfer',
      account: `${from.map((l) => name(l.accountId)).join(', ')} → ${to.map((l) => name(l.accountId)).join(', ')}`,
      amounts: [...from, ...to].map((l) => ({
        currency: l.currency,
        amount: l.amount,
      })),
    };
  }
  return {
    category: other.map((l) => name(l.accountId)).join(', '),
    account: balance.map((l) => name(l.accountId)).join(', '),
    // Money out of an account (or onto a card) shows as negative.
    amounts: balance.map((l) => ({ currency: l.currency, amount: l.amount })),
  };
}

export interface SheetLine {
  account: Account;
  amount: bigint;
}

export interface SheetColumn {
  currency: string;
  own: SheetLine[];
  owe: SheetLine[];
  ownTotal: bigint;
  oweTotal: bigint;
  net: bigint;
  // Present only for the All scope, where equity explains net worth.
  equity: {
    opening: bigint;
    earnings: bigint;
    fx: bigint;
    revaluation: bigint;
  } | null;
  balanced: boolean | null;
}

export function balanceSheet(
  accounts: Map<number, Account>,
  sums: Balance[],
  scope: Scope | 'all',
): SheetColumn[] {
  const byKey = new Map(
    sums.map((b) => [`${b.accountId}:${b.currency}`, b.balance]),
  );
  const get = (id: number, c: string) => byKey.get(`${id}:${c}`) ?? 0n;
  const inScope = (a: Account) => scope === 'all' || a.scope === scope;

  const currencies = new Set<string>();
  for (const a of accounts.values()) {
    if (a.currency && !a.archived_at && inScope(a)) currencies.add(a.currency);
  }
  for (const b of sums) {
    const a = accounts.get(b.accountId);
    if (
      b.balance !== 0n &&
      a &&
      (a.type === 'asset' || a.type === 'liability') &&
      inScope(a)
    ) {
      currencies.add(b.currency);
    }
  }

  return [...currencies].sort().map((currency) => {
    const lines = (type: 'asset' | 'liability') =>
      [...accounts.values()]
        .filter((a) => a.type === type && a.currency === currency && inScope(a))
        .map((a) => ({
          account: a,
          amount: type === 'asset' ? get(a.id, currency) : -get(a.id, currency),
        }))
        // Archived accounts drop out only once they are empty.
        .filter((l) => !l.account.archived_at || l.amount !== 0n);
    const own = lines('asset');
    const owe = lines('liability');
    const ownTotal = own.reduce((s, l) => s + l.amount, 0n);
    const oweTotal = owe.reduce((s, l) => s + l.amount, 0n);
    const net = ownTotal - oweTotal;

    let equity: SheetColumn['equity'] = null;
    let balanced: boolean | null = null;
    if (scope === 'all') {
      let opening = 0n,
        fx = 0n,
        revaluation = 0n,
        earnings = 0n;
      for (const a of accounts.values()) {
        const v = -get(a.id, currency);
        if (a.system_key === 'opening') opening += v;
        else if (a.system_key === 'fx') fx += v;
        else if (a.system_key === 'revaluation') revaluation += v;
        else if (a.type === 'income' || a.type === 'expense') earnings += v;
      }
      equity = { opening, earnings, fx, revaluation };
      balanced = net === opening + earnings + fx + revaluation;
    }
    return { currency, own, owe, ownTotal, oweTotal, net, equity, balanced };
  });
}
