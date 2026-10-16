// Clients and their orders, stored beside the ledger. Every order step runs
// in one transaction that locks the order and its client first, re-reads the
// state and only then posts, so a double submit cannot post twice.
import type { Sql } from './db.ts';
import type { Account } from './entries.ts';
import {
  checkDraft,
  insertDraft,
  loadAccounts,
  voidTransaction,
} from './ledger.ts';
import {
  deliveryDraft,
  deriveStatus,
  orderRef,
  paymentDraft,
  percentOf,
  purchaseDraft,
  quote,
  realCost,
  refundDraft,
  type OrderLine,
  type Quote,
  type Rate,
  type Status,
} from './orders.ts';
import { monthRange } from './reports.ts';

// A refusal the owner should read, shown beside the action that caused it.
export class OrderError extends Error {}

export interface Settings {
  feeBp: number;
  depositBp: number;
  invoiceNote: string;
}

export async function loadSettings(sql: Sql): Promise<Settings> {
  const rows = await sql<
    { key: string; value: string }[]
  >`select key, value from fin_settings`;
  const m = new Map(rows.map((r) => [r.key, r.value]));
  return {
    feeBp: Number(m.get('fee_bp') ?? 500),
    depositBp: Number(m.get('deposit_bp') ?? 5000),
    invoiceNote: m.get('invoice_note') ?? '',
  };
}

export async function saveSettings(sql: Sql, s: Settings): Promise<void> {
  await sql.begin(async (tx) => {
    for (const [key, value] of [
      ['fee_bp', String(s.feeBp)],
      ['deposit_bp', String(s.depositBp)],
      ['invoice_note', s.invoiceNote],
    ]) {
      await tx`insert into fin_settings (key, value) values (${key}, ${value})
        on conflict (key) do update set value = excluded.value`;
    }
  });
}

export interface Client {
  id: number;
  name: string;
  contact: string;
  currency: string;
  owesAccountId: number;
  depositsAccountId: number;
}

const CLIENT_COLUMNS = (sql: Sql) => sql`
  id, name, contact, trim(currency) as currency,
  owes_account_id as "owesAccountId", deposits_account_id as "depositsAccountId"`;

export async function getClient(sql: Sql, id: number): Promise<Client | null> {
  const [c] = await sql<
    Client[]
  >`select ${CLIENT_COLUMNS(sql)} from fin_clients where id = ${id}`;
  return c ?? null;
}

export async function createClient(
  sql: Sql,
  input: { name: string; contact: string; currency: string },
): Promise<number> {
  // Account names add up to 16 characters to the client name (limit 80).
  if (input.name.length < 1 || input.name.length > 60) {
    throw new OrderError('Enter a client name up to 60 characters.');
  }
  return sql.begin(async (tx) => {
    const [{ id }] = await tx<
      { id: number }[]
    >`select nextval('fin_clients_id_seq')::int as id`;
    const [owes] = await tx<{ id: number }[]>`
      insert into fin_accounts (name, type, currency, scope, system_key)
      values (${`${input.name} · owes you`}, 'asset', ${input.currency}, 'business', ${`client:${id}:owes`})
      returning id`;
    const [deposits] = await tx<{ id: number }[]>`
      insert into fin_accounts (name, type, currency, scope, system_key)
      values (${`${input.name} · deposits held`}, 'liability', ${input.currency}, 'business', ${`client:${id}:deposits`})
      returning id`;
    await tx`insert into fin_clients (id, name, contact, currency, owes_account_id, deposits_account_id)
      values (${id}, ${input.name}, ${input.contact}, ${input.currency}, ${owes.id}, ${deposits.id})`;
    return id;
  });
}

// What the client owes you, and the deposit or credit you hold for them.
export async function clientBalance(
  sql: Sql,
  c: Client,
): Promise<{ owed: bigint; held: bigint }> {
  const [row] = await sql<{ owed: bigint; held: bigint }[]>`
    select
      coalesce(sum(p.amount_minor) filter (where p.account_id = ${c.owesAccountId}), 0)::bigint as owed,
      (-coalesce(sum(p.amount_minor) filter (where p.account_id = ${c.depositsAccountId}), 0))::bigint as held
    from fin_postings p join fin_transactions t on t.id = p.transaction_id
    where t.voided_at is null and p.account_id in (${c.owesAccountId}, ${c.depositsAccountId})`;
  return row;
}

// Deposits paid on orders that are still open (not delivered or cancelled).
// They belong to those orders: delivery of another order may not use them,
// and they cannot be refunded until their order is delivered or cancelled.
async function reservedDeposits(
  sql: Sql,
  clientId: number,
  exceptOrderId: number | null,
): Promise<bigint> {
  const [row] = await sql<{ reserved: bigint }[]>`
    select coalesce(sum(cp.amount), 0)::bigint as reserved
    from fin_client_payments cp
    join fin_transactions t on t.id = cp.transaction_id
    join fin_orders o on o.id = cp.order_id
    where cp.client_id = ${clientId} and cp.kind = 'payment' and not cp.after_delivery
      and t.voided_at is null and o.cancelled_at is null and o.delivery_tx is null
      and o.id <> ${exceptOrderId ?? 0}`;
  return row.reserved;
}

// Credit held that no open order has a claim on: overpayments and deposits
// from cancelled orders.
export async function freeCredit(sql: Sql, c: Client): Promise<bigint> {
  const { held } = await clientBalance(sql, c);
  const free = held - (await reservedDeposits(sql, c.id, null));
  return free > 0n ? free : 0n;
}

export async function createOrder(
  sql: Sql,
  clientId: number,
  feeBp: number,
  createdOn: string,
): Promise<number> {
  const [o] = await sql<{ id: number }[]>`
    insert into fin_orders (client_id, fee_bp, created_on)
    values (${clientId}, ${feeBp}, ${createdOn}) returning id`;
  return o.id;
}

export interface Step {
  txId: bigint;
  kind: 'payment' | 'purchase' | 'delivery';
  occurredOn: string;
  amount: bigint | null;
  currency: string | null;
  account: string;
  afterDelivery: boolean;
}

export interface OrderView {
  id: number;
  ref: string;
  client: Client;
  createdOn: string;
  feeBp: number;
  note: string;
  cancelled: boolean;
  lines: OrderLine[];
  rates: Map<string, Rate>;
  quote: Quote;
  status: Status;
  paidBefore: bigint;
  applied: bigint;
  paidAfter: bigint;
  paid: bigint;
  due: bigint;
  bought: Map<string, bigint> | null;
  realCost: bigint | null;
  steps: Step[];
}

interface OrderRow {
  id: number;
  clientId: number;
  feeBp: number;
  note: string;
  createdOn: string;
  cancelled: boolean;
  purchaseTx: bigint | null;
  deliveryTx: bigint | null;
}

export async function loadOrder(
  sql: Sql,
  id: number,
): Promise<OrderView | null> {
  const [o] = await sql<OrderRow[]>`
    select id, client_id as "clientId", fee_bp as "feeBp", note,
           to_char(created_on, 'YYYY-MM-DD') as "createdOn",
           cancelled_at is not null as cancelled,
           purchase_tx as "purchaseTx", delivery_tx as "deliveryTx"
    from fin_orders where id = ${id}`;
  if (!o) return null;
  const client = (await getClient(sql, o.clientId))!;
  const lines = await sql<OrderLine[]>`
    select id, description, options, link, quantity, unit_cost as "unitCost", trim(currency) as currency
    from fin_order_lines where order_id = ${id} order by id`;
  const rateRows = await sql<Rate[]>`
    select trim(currency) as currency, charge_micro as charge, cost_micro as cost
    from fin_order_rates where order_id = ${id}`;
  const rates = new Map(rateRows.map((r) => [r.currency, r]));

  const payments = await sql<(Step & { kind: 'payment' })[]>`
    select t.id as "txId", 'payment' as kind, to_char(t.occurred_on, 'YYYY-MM-DD') as "occurredOn",
           cp.amount, trim(c.currency) as currency, cp.after_delivery as "afterDelivery",
           (select a.name from fin_postings p join fin_accounts a on a.id = p.account_id
             where p.transaction_id = t.id and a.system_key is null limit 1) as account
    from fin_client_payments cp
    join fin_transactions t on t.id = cp.transaction_id
    join fin_clients c on c.id = cp.client_id
    where cp.order_id = ${id} and cp.kind = 'payment' and t.voided_at is null`;

  const steps: Step[] = [...payments];
  let bought: Map<string, bigint> | null = null;
  if (o.purchaseTx !== null) {
    const parts = await sql<
      {
        currency: string;
        amount: bigint;
        account: string;
        occurredOn: string;
      }[]
    >`
      select trim(p.currency) as currency, p.amount_minor as amount, a.name as account,
             to_char(t.occurred_on, 'YYYY-MM-DD') as "occurredOn"
      from fin_postings p join fin_accounts a on a.id = p.account_id
      join fin_transactions t on t.id = p.transaction_id
      where p.transaction_id = ${o.purchaseTx} and a.system_key is null`;
    bought = new Map(parts.map((p) => [p.currency, -p.amount]));
    steps.push({
      txId: o.purchaseTx,
      kind: 'purchase',
      occurredOn: parts[0]?.occurredOn ?? '',
      amount: null,
      currency: null,
      account: parts.map((p) => p.account).join(', '),
      afterDelivery: false,
    });
  }
  let applied = 0n;
  if (o.deliveryTx !== null) {
    const [d] = await sql<{ applied: bigint; occurredOn: string }[]>`
      select coalesce(sum(p.amount_minor) filter (where p.account_id = ${client.depositsAccountId}), 0)::bigint as applied,
             max(to_char(t.occurred_on, 'YYYY-MM-DD')) as "occurredOn"
      from fin_postings p join fin_transactions t on t.id = p.transaction_id
      where p.transaction_id = ${o.deliveryTx}`;
    applied = d.applied;
    steps.push({
      txId: o.deliveryTx,
      kind: 'delivery',
      occurredOn: d.occurredOn,
      amount: null,
      currency: null,
      account: '',
      afterDelivery: false,
    });
  }
  steps.sort((a, b) => (a.txId < b.txId ? -1 : 1));

  const q = quote(lines, rates, o.feeBp, client.currency);
  const delivered = o.deliveryTx !== null;
  const before = payments.filter((p) => !p.afterDelivery);
  const paidBefore = before.reduce((s, p) => s + p.amount!, 0n);
  const paidAfter = payments
    .filter((p) => p.afterDelivery)
    .reduce((s, p) => s + p.amount!, 0n);
  const paid = delivered ? applied + paidAfter : paidBefore;
  const due = q.total - paid;
  return {
    id: o.id,
    ref: orderRef(o.id),
    client,
    createdOn: o.createdOn,
    feeBp: o.feeBp,
    note: o.note,
    cancelled: o.cancelled,
    lines,
    rates,
    quote: q,
    status: deriveStatus({
      cancelled: o.cancelled,
      delivered,
      bought: bought !== null,
      payments: before.length,
      due,
    }),
    paidBefore,
    applied,
    paidAfter,
    paid,
    due,
    bought,
    realCost: realCost(bought ?? q.lineCost, rates, client.currency),
    steps,
  };
}

export async function clientOrders(
  sql: Sql,
  clientId: number,
): Promise<OrderView[]> {
  const ids = await sql<{ id: number }[]>`
    select id from fin_orders where client_id = ${clientId} order by id desc`;
  const out: OrderView[] = [];
  for (const { id } of ids) out.push((await loadOrder(sql, id))!);
  return out;
}

// Locks the order and its client, then hands over a fresh view.
async function withOrder<T>(
  sql: Sql,
  id: number,
  fn: (tx: Sql, view: OrderView, accounts: Map<number, Account>) => Promise<T>,
): Promise<T> {
  // postgres.js types begin()'s result as an unwrapped array; T is never one.
  return sql.begin(async (raw) => {
    const tx = raw as unknown as Sql;
    const [o] = await tx<{ clientId: number }[]>`
      select client_id as "clientId" from fin_orders where id = ${id} for update`;
    if (!o) throw new OrderError('That order no longer exists.');
    await tx`select id from fin_clients where id = ${o.clientId} for update`;
    const view = (await loadOrder(tx, id))!;
    return fn(tx, view, await loadAccounts(tx));
  }) as Promise<T>;
}

const STATUS_LABEL: Record<Status, string> = {
  quote: 'a quote',
  deposit: 'paid a deposit',
  bought: 'bought',
  delivered: 'delivered',
  closed: 'closed',
  cancelled: 'cancelled',
};

function requireStatus(
  view: OrderView,
  allowed: Status[],
  action: string,
): void {
  if (!allowed.includes(view.status)) {
    throw new OrderError(
      `${view.ref} is ${STATUS_LABEL[view.status]}, so you can't ${action} now.`,
    );
  }
}

async function post(
  tx: Sql,
  draft: Parameters<typeof checkDraft>[0],
  accounts: Map<number, Account>,
) {
  checkDraft(draft, accounts);
  return insertDraft(tx, draft);
}

function clientAccounts(
  view: OrderView | { client: Client },
  accounts: Map<number, Account>,
) {
  return {
    owes: accounts.get(view.client.owesAccountId)!,
    deposits: accounts.get(view.client.depositsAccountId)!,
  };
}

function systemKey(accounts: Map<number, Account>, key: string): Account {
  for (const a of accounts.values()) if (a.system_key === key) return a;
  throw new Error(`Missing system account ${key}`);
}

// A live, owner-visible account of the right kind and currency.
function moneyAccount(
  accounts: Map<number, Account>,
  id: number | null,
  currency: string,
  types: Account['type'][],
): Account {
  const a = id === null ? undefined : accounts.get(id);
  if (
    !a ||
    a.archived_at ||
    a.system_key ||
    !types.includes(a.type) ||
    a.currency !== currency
  ) {
    throw new OrderError(`Choose one of your ${currency} accounts.`);
  }
  return a;
}

export async function addLine(
  sql: Sql,
  orderId: number,
  line: Omit<OrderLine, 'id'>,
): Promise<void> {
  await withOrder(sql, orderId, async (tx, view) => {
    requireStatus(view, ['quote'], 'change its items');
    await tx`insert into fin_order_lines (order_id, description, options, link, quantity, unit_cost, currency)
      values (${orderId}, ${line.description}, ${line.options}, ${line.link}, ${line.quantity}, ${line.unitCost}, ${line.currency})`;
  });
}

export async function deleteLine(
  sql: Sql,
  orderId: number,
  lineId: number,
): Promise<void> {
  await withOrder(sql, orderId, async (tx, view) => {
    requireStatus(view, ['quote'], 'change its items');
    await tx`delete from fin_order_lines where id = ${lineId} and order_id = ${orderId}`;
  });
}

export async function saveTerms(
  sql: Sql,
  orderId: number,
  feeBp: number,
  rates: Rate[],
): Promise<void> {
  await withOrder(sql, orderId, async (tx, view) => {
    requireStatus(view, ['quote'], 'change its rates or fee');
    const needed = [...view.quote.lineCost.keys()].sort().join();
    if (
      rates
        .map((r) => r.currency)
        .sort()
        .join() !== needed
    ) {
      throw new OrderError(
        'The items changed since this page loaded. Reload the order and enter the rates again.',
      );
    }
    await tx`update fin_orders set fee_bp = ${feeBp} where id = ${orderId}`;
    await tx`delete from fin_order_rates where order_id = ${orderId}`;
    for (const r of rates) {
      await tx`insert into fin_order_rates (order_id, currency, charge_micro, cost_micro)
        values (${orderId}, ${r.currency}, ${r.charge}, ${r.cost})`;
    }
  });
}

export async function saveNote(
  sql: Sql,
  orderId: number,
  note: string,
): Promise<void> {
  await sql`update fin_orders set note = ${note} where id = ${orderId}`;
}

export async function recordPayment(
  sql: Sql,
  orderId: number,
  p: { intoAccountId: number | null; amount: bigint; occurredOn: string },
): Promise<void> {
  await withOrder(sql, orderId, async (tx, view, accounts) => {
    requireStatus(
      view,
      ['quote', 'deposit', 'bought', 'delivered', 'closed'],
      'record a payment',
    );
    const into = moneyAccount(accounts, p.intoAccountId, view.client.currency, [
      'asset',
    ]);
    const afterDelivery =
      view.status === 'delivered' || view.status === 'closed';
    // Settles only this order's balance; anything beyond it becomes credit.
    const draft = paymentDraft({
      client: clientAccounts(view, accounts),
      into,
      amount: p.amount,
      occurredOn: p.occurredOn,
      afterDelivery,
      owed: view.due > 0n ? view.due : 0n,
      description: `${view.ref} · payment from ${view.client.name}`,
    });
    const txId = await post(tx, draft, accounts);
    await tx`insert into fin_client_payments (client_id, order_id, transaction_id, kind, after_delivery, amount)
      values (${view.client.id}, ${orderId}, ${txId}, 'payment', ${afterDelivery}, ${p.amount})`;
  });
}

async function ensureGoodsAccount(tx: Sql, currency: string): Promise<void> {
  await tx`insert into fin_accounts (name, type, currency, scope, system_key)
    values (${`Goods bought for clients · ${currency}`}, 'asset', ${currency}, 'business', ${`goods:${currency}`})
    on conflict (system_key) do nothing`;
}

export async function markBought(
  sql: Sql,
  orderId: number,
  parts: { currency: string; fromAccountId: number | null; amount: bigint }[],
  occurredOn: string,
): Promise<void> {
  await withOrder(sql, orderId, async (tx, view) => {
    requireStatus(view, ['quote', 'deposit'], 'mark it bought');
    if (view.lines.length === 0)
      throw new OrderError('Add at least one item before marking it bought.');
    if (view.quote.missingRates.length) {
      throw new OrderError(
        `Set the ${view.quote.missingRates.join(' and ')} rates first.`,
      );
    }
    const needed = [...view.quote.lineCost.keys()].sort();
    const given = parts.map((p) => p.currency).sort();
    if (needed.join() !== given.join())
      throw new OrderError(`Enter what you paid in ${needed.join(' and ')}.`);
    for (const c of needed) await ensureGoodsAccount(tx, c);
    const accounts = await loadAccounts(tx);
    const draft = purchaseDraft(
      parts.map((p) => ({
        from: moneyAccount(accounts, p.fromAccountId, p.currency, [
          'asset',
          'liability',
        ]),
        goods: systemKey(accounts, `goods:${p.currency}`),
        amount: p.amount,
      })),
      occurredOn,
      `${view.ref} · bought for ${view.client.name}`,
    );
    const txId = await post(tx, draft, accounts);
    await tx`update fin_orders set purchase_tx = ${txId} where id = ${orderId}`;
  });
}

export async function markDelivered(
  sql: Sql,
  orderId: number,
  occurredOn: string,
): Promise<void> {
  await withOrder(sql, orderId, async (tx, view, accounts) => {
    requireStatus(view, ['bought'], 'mark it delivered');
    if (view.quote.total <= 0n) {
      throw new OrderError(
        `${view.ref} totals 0 ${view.client.currency}. Check the rates before delivering it.`,
      );
    }
    // This order's own deposits plus free credit; never another open order's deposit.
    const { held } = await clientBalance(tx, view.client);
    const available =
      held - (await reservedDeposits(tx, view.client.id, view.id));
    const { draft } = deliveryDraft({
      client: clientAccounts(view, accounts),
      sales: systemKey(accounts, 'client_sales'),
      cost: systemKey(accounts, 'client_cost'),
      goods: [...view.bought!].map(([c, amount]) => ({
        goods: systemKey(accounts, `goods:${c}`),
        amount,
      })),
      total: view.quote.total,
      held: available,
      occurredOn,
      description: `${view.ref} · delivered to ${view.client.name}`,
    });
    const txId = await post(tx, draft, accounts);
    await tx`update fin_orders set delivery_tx = ${txId} where id = ${orderId}`;
  });
}

// Reverses the order's latest step by voiding its ledger entry.
export async function undoLatest(
  sql: Sql,
  orderId: number,
): Promise<Step['kind']> {
  return withOrder(sql, orderId, async (tx, view) => {
    const last = view.steps.at(-1);
    if (!last || view.cancelled)
      throw new OrderError('There is nothing to undo on this order.');
    const { held, owed } = await clientBalance(tx, view.client);
    if (last.kind === 'payment') {
      // Whatever this payment added to the client's credit must still be held,
      // without touching deposits that belong to other open orders.
      const [{ credited }] = await tx<{ credited: bigint }[]>`
        select (-coalesce(sum(amount_minor), 0))::bigint as credited from fin_postings
        where transaction_id = ${last.txId} and account_id = ${view.client.depositsAccountId}`;
      const others = await reservedDeposits(tx, view.client.id, view.id);
      if (held - credited < others) {
        throw new OrderError(
          'That payment has already been used or refunded as credit, so it cannot be undone.',
        );
      }
    }
    if (
      last.kind === 'delivery' &&
      owed - (view.quote.total - view.applied) < 0n
    ) {
      throw new OrderError(
        'Payments already settle this delivery, so it cannot be undone.',
      );
    }
    await voidTransaction(tx, last.txId, true);
    if (last.kind === 'purchase')
      await tx`update fin_orders set purchase_tx = null where id = ${orderId}`;
    if (last.kind === 'delivery')
      await tx`update fin_orders set delivery_tx = null where id = ${orderId}`;
    return last.kind;
  });
}

export async function cancelOrder(sql: Sql, orderId: number): Promise<void> {
  await withOrder(sql, orderId, async (tx, view) => {
    requireStatus(view, ['quote', 'deposit'], 'cancel it');
    await tx`update fin_orders set cancelled_at = now() where id = ${orderId}`;
  });
}

export async function refundCredit(
  sql: Sql,
  clientId: number,
  r: { fromAccountId: number | null; amount: bigint; occurredOn: string },
): Promise<void> {
  await sql.begin(async (raw) => {
    const tx = raw as unknown as Sql;
    await tx`select id from fin_clients where id = ${clientId} for update`;
    const client = await getClient(tx, clientId);
    if (!client) throw new OrderError('That client no longer exists.');
    if (r.amount > (await freeCredit(tx, client)))
      throw new OrderError(
        'That is more than the credit you can refund. Deposits on open orders stay with those orders until they are delivered or cancelled.',
      );
    const accounts = await loadAccounts(tx);
    const draft = refundDraft({
      client: clientAccounts({ client }, accounts),
      from: moneyAccount(accounts, r.fromAccountId, client.currency, ['asset']),
      amount: r.amount,
      occurredOn: r.occurredOn,
      description: `Refund to ${client.name}`,
    });
    const txId = await post(tx, draft, accounts);
    await tx`insert into fin_client_payments (client_id, order_id, transaction_id, kind, amount)
      values (${clientId}, null, ${txId}, 'refund', ${r.amount})`;
  });
}

export interface StatementRow {
  occurredOn: string;
  description: string;
  change: bigint;
  running: bigint;
}

// Net owed by the client (owes you minus credit held), over a date range.
export async function statement(
  sql: Sql,
  c: Client,
  from: string,
  to: string,
): Promise<{ opening: bigint; rows: StatementRow[]; closing: bigint }> {
  const rows = await sql<
    {
      occurredOn: string;
      description: string;
      change: bigint;
      before: boolean;
    }[]
  >`
    select to_char(t.occurred_on, 'YYYY-MM-DD') as "occurredOn", t.description,
           sum(p.amount_minor)::bigint as change, t.occurred_on < ${from} as before
    from fin_postings p join fin_transactions t on t.id = p.transaction_id
    where t.voided_at is null and t.occurred_on <= ${to}
      and p.account_id in (${c.owesAccountId}, ${c.depositsAccountId})
    group by t.id, t.occurred_on, t.description
    having sum(p.amount_minor) <> 0
    order by t.occurred_on, t.id`;
  const opening = rows
    .filter((r) => r.before)
    .reduce((s, r) => s + r.change, 0n);
  let running = opening;
  const out = rows
    .filter((r) => !r.before)
    .map((r) => ({
      occurredOn: r.occurredOn,
      description: r.description,
      change: r.change,
      running: (running += r.change),
    }));
  return { opening, rows: out, closing: running };
}

export interface MonthReport {
  currency: string;
  orders: number;
  sales: bigint;
  cost: bigint;
  profit: bigint;
  fees: bigint;
}

// Orders delivered in the month, with estimated profit per billing currency.
export async function monthReport(
  sql: Sql,
  month: string,
): Promise<MonthReport[]> {
  const { from, until } = monthRange(month);
  const ids = await sql<{ id: number }[]>`
    select o.id from fin_orders o join fin_transactions t on t.id = o.delivery_tx
    where t.voided_at is null and t.occurred_on >= ${from} and t.occurred_on < ${until}`;
  const out = new Map<string, MonthReport>();
  for (const { id } of ids) {
    const v = (await loadOrder(sql, id))!;
    const r = out.get(v.client.currency) ?? {
      currency: v.client.currency,
      orders: 0,
      sales: 0n,
      cost: 0n,
      profit: 0n,
      fees: 0n,
    };
    r.orders += 1;
    r.sales += v.quote.total;
    r.fees += v.quote.fee;
    r.cost += v.realCost ?? 0n;
    r.profit += v.quote.total - (v.realCost ?? 0n);
    out.set(v.client.currency, r);
  }
  return [...out.values()];
}

export function suggestedDeposit(view: OrderView, depositBp: number): bigint {
  return percentOf(view.quote.total, depositBp);
}
