// Client orders against a real, disposable Postgres (see db.test.ts for the
// FINANCE_TEST_DATABASE_URL rules). Shares that database, so the finance test
// script runs files one at a time.
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import {
  OrderError,
  addLine,
  cancelOrder,
  clientBalance,
  createClient,
  createOrder,
  deleteLine,
  freeCredit,
  getClient,
  loadOrder,
  loadSettings,
  markBought,
  markDelivered,
  monthReport,
  recordPayment,
  refundCredit,
  saveSettings,
  saveTerms,
  statement,
  undoLatest,
} from './clients.ts';
import { connect, migrate, type Sql } from './db.ts';
import { createAccount, loadAccounts, voidTransaction } from './ledger.ts';
import { parseRate } from './orders.ts';
import { balanceSheet, balances, monthSpending } from './reports.ts';

const url = process.env.FINANCE_TEST_DATABASE_URL;
const safe = !!url && /_test$/.test(new URL(url).pathname.slice(1));
const opts = {
  skip: !url
    ? 'FINANCE_TEST_DATABASE_URL is not set'
    : !safe
      ? 'FINANCE_TEST_DATABASE_URL must name a database ending in _test'
      : false,
};
let sql: Sql;
const ids: Record<string, number> = {};

before(async () => {
  if (!url || !safe) return;
  sql = connect(url);
  await sql.unsafe('drop schema public cascade; create schema public;');
  await migrate(sql);
  const acct = async (
    name: string,
    currency: string,
    type: 'asset' | 'liability' = 'asset',
    opening = 0n,
  ) =>
    (ids[name] = await createAccount(
      sql,
      { name, type, currency, scope: 'personal' },
      { amount: opening, occurredOn: '2026-10-01' },
    ));
  await acct('KBZPay', 'MMK', 'asset', 1000000n);
  await acct('KBank', 'THB', 'asset', 5000000n);
  await acct('Wise', 'USD', 'asset', 10000n);
  await acct('KTC card', 'THB', 'liability');
});
after(async () => {
  await sql?.end();
});

async function assertBalanced(label: string) {
  const cols = balanceSheet(
    await loadAccounts(sql),
    await balances(sql, '2099-12-31'),
    'all',
  );
  for (const c of cols)
    assert.equal(c.balanced, true, `${label}: ${c.currency} balances`);
}

async function previewOrder(clientId: number) {
  const id = await createOrder(sql, clientId, 500, '2026-10-10');
  await addLine(sql, id, {
    description: 'Nike Air Max 90',
    options: 'Size 38',
    link: 'https://www.nike.com/th/x',
    quantity: 1,
    unitCost: 329000n,
    currency: 'THB',
  });
  await addLine(sql, id, {
    description: 'Uniqlo AIRism',
    options: 'M',
    link: '',
    quantity: 2,
    unitCost: 59000n,
    currency: 'THB',
  });
  await addLine(sql, id, {
    description: 'Kindle cover',
    options: '',
    link: '',
    quantity: 1,
    unitCost: 2499n,
    currency: 'USD',
  });
  await addLine(sql, id, {
    description: 'Shop delivery',
    options: '',
    link: '',
    quantity: 1,
    unitCost: 12000n,
    currency: 'THB',
  });
  await saveTerms(sql, id, 500, [
    { currency: 'THB', charge: parseRate('128')!, cost: parseRate('122.5')! },
    { currency: 'USD', charge: parseRate('4500')!, cost: parseRate('4320')! },
  ]);
  return id;
}

test(
  'migration 2 seeds settings and client system accounts',
  opts,
  async () => {
    const s = await loadSettings(sql);
    assert.deepEqual(s, { feeBp: 500, depositBp: 5000, invoiceNote: '' });
    await saveSettings(sql, {
      feeBp: 600,
      depositBp: 4000,
      invoiceNote: 'KBZPay 09-xxx',
    });
    assert.deepEqual(await loadSettings(sql), {
      feeBp: 600,
      depositBp: 4000,
      invoiceNote: 'KBZPay 09-xxx',
    });
    const keys = [...(await loadAccounts(sql)).values()].map(
      (a) => a.system_key,
    );
    assert.ok(keys.includes('client_sales') && keys.includes('client_cost'));
  },
);

test(
  'full lifecycle: quote → deposit → bought → delivered → closed',
  opts,
  async () => {
    const clientId = await createClient(sql, {
      name: 'Ma Hnin Wai',
      contact: 'Viber',
      currency: 'MMK',
    });
    const client = (await getClient(sql, clientId))!;
    const id = await previewOrder(clientId);

    let v = (await loadOrder(sql, id))!;
    assert.equal(v.status, 'quote');
    assert.equal(v.quote.total, 734974n);
    assert.equal(v.realCost, 670232n);

    await recordPayment(sql, id, {
      intoAccountId: ids.KBZPay,
      amount: 370000n,
      occurredOn: '2026-10-11',
    });
    v = (await loadOrder(sql, id))!;
    assert.equal(v.status, 'deposit');
    assert.equal(v.due, 364974n);
    assert.deepEqual(await clientBalance(sql, client), {
      owed: 0n,
      held: 370000n,
    });
    await assertBalanced('after deposit');

    await assert.rejects(
      addLine(sql, id, {
        description: 'x',
        options: '',
        link: '',
        quantity: 1,
        unitCost: 1n,
        currency: 'THB',
      }),
      OrderError,
      'prices lock after a deposit',
    );

    await markBought(
      sql,
      id,
      [
        { currency: 'THB', fromAccountId: ids.KBank, amount: 459000n },
        { currency: 'USD', fromAccountId: ids.Wise, amount: 2499n },
      ],
      '2026-10-12',
    );
    v = (await loadOrder(sql, id))!;
    assert.equal(v.status, 'bought');
    await assertBalanced('after purchase');

    await markDelivered(sql, id, '2026-10-16');
    v = (await loadOrder(sql, id))!;
    assert.equal(v.status, 'delivered');
    assert.equal(v.applied, 370000n);
    assert.equal(v.due, 364974n);
    assert.deepEqual(await clientBalance(sql, client), {
      owed: 364974n,
      held: 0n,
    });
    await assertBalanced('after delivery');

    // The balance sheet groups client money into one line each way.
    const mmk = balanceSheet(
      await loadAccounts(sql),
      await balances(sql, '2026-10-31'),
      'all',
    ).find((c) => c.currency === 'MMK')!;
    assert.equal(mmk.own.find((l) => l.key === 'clients')!.amount, 364974n);

    await recordPayment(sql, id, {
      intoAccountId: ids.KBZPay,
      amount: 364974n,
      occurredOn: '2026-10-18',
    });
    v = (await loadOrder(sql, id))!;
    assert.equal(v.status, 'closed');
    assert.equal(v.due, 0n);
    assert.deepEqual(await clientBalance(sql, client), { owed: 0n, held: 0n });
    await assertBalanced('after balance paid');

    const st = await statement(sql, client, '2026-10-01', '2026-10-31');
    assert.equal(st.opening, 0n);
    assert.deepEqual(
      st.rows.map((r) => r.change),
      [-370000n, 734974n, -364974n],
    );
    assert.equal(st.closing, 0n);

    const report = await monthReport(sql, '2026-10');
    assert.deepEqual(report, [
      {
        currency: 'MMK',
        orders: 1,
        sales: 734974n,
        cost: 670232n,
        profit: 64742n,
        fees: 34999n,
      },
    ]);
  },
);

test(
  'undo reverses each step, newest first, back to a quote',
  opts,
  async () => {
    const clientId = await createClient(sql, {
      name: 'Ko Aung',
      contact: '',
      currency: 'MMK',
    });
    const client = (await getClient(sql, clientId))!;
    const id = await previewOrder(clientId);
    await recordPayment(sql, id, {
      intoAccountId: ids.KBZPay,
      amount: 300000n,
      occurredOn: '2026-10-11',
    });
    await markBought(
      sql,
      id,
      [
        { currency: 'THB', fromAccountId: ids['KTC card'], amount: 459000n },
        { currency: 'USD', fromAccountId: ids.Wise, amount: 2499n },
      ],
      '2026-10-12',
    );
    await markDelivered(sql, id, '2026-10-16');
    await recordPayment(sql, id, {
      intoAccountId: ids.KBZPay,
      amount: 500000n,
      occurredOn: '2026-10-17',
    });
    let v = (await loadOrder(sql, id))!;
    assert.equal(v.status, 'closed');
    assert.deepEqual(
      await clientBalance(sql, client),
      { owed: 0n, held: 500000n - 434974n },
      'overpayment becomes credit',
    );

    for (const [kind, status] of [
      ['payment', 'delivered'],
      ['delivery', 'bought'],
      ['purchase', 'deposit'],
      ['payment', 'quote'],
    ]) {
      assert.equal(await undoLatest(sql, id), kind);
      v = (await loadOrder(sql, id))!;
      assert.equal(v.status, status, `after undoing ${kind}`);
      await assertBalanced(`after undoing ${kind}`);
    }
    assert.deepEqual(await clientBalance(sql, client), { owed: 0n, held: 0n });
    await assert.rejects(undoLatest(sql, id), /nothing to undo/);
    // Back to a quote, so items can change again.
    await deleteLine(sql, id, v.lines[0].id);
    assert.equal((await loadOrder(sql, id))!.lines.length, 3);
  },
);

test(
  'cancel keeps the deposit as credit; refund pays it back',
  opts,
  async () => {
    const clientId = await createClient(sql, {
      name: 'Daw Mya',
      contact: '',
      currency: 'MMK',
    });
    const client = (await getClient(sql, clientId))!;
    const id = await previewOrder(clientId);
    await recordPayment(sql, id, {
      intoAccountId: ids.KBZPay,
      amount: 200000n,
      occurredOn: '2026-10-11',
    });
    await cancelOrder(sql, id);
    assert.equal((await loadOrder(sql, id))!.status, 'cancelled');
    await assert.rejects(
      recordPayment(sql, id, {
        intoAccountId: ids.KBZPay,
        amount: 1n,
        occurredOn: '2026-10-11',
      }),
      OrderError,
    );
    assert.deepEqual(await clientBalance(sql, client), {
      owed: 0n,
      held: 200000n,
    });
    await assert.rejects(
      refundCredit(sql, clientId, {
        fromAccountId: ids.KBZPay,
        amount: 200001n,
        occurredOn: '2026-10-12',
      }),
      /more than the credit/,
    );
    await refundCredit(sql, clientId, {
      fromAccountId: ids.KBZPay,
      amount: 200000n,
      occurredOn: '2026-10-12',
    });
    assert.deepEqual(await clientBalance(sql, client), { owed: 0n, held: 0n });
    await assertBalanced('after refund');
  },
);

test('a payment whose credit was refunded cannot be undone', opts, async () => {
  const clientId = await createClient(sql, {
    name: 'Ko Zaw',
    contact: '',
    currency: 'MMK',
  });
  const client = (await getClient(sql, clientId))!;
  const id = await previewOrder(clientId);
  await markBought(
    sql,
    id,
    [
      { currency: 'THB', fromAccountId: ids.KBank, amount: 459000n },
      { currency: 'USD', fromAccountId: ids.Wise, amount: 2499n },
    ],
    '2026-10-12',
  );
  await markDelivered(sql, id, '2026-10-16');
  await recordPayment(sql, id, {
    intoAccountId: ids.KBZPay,
    amount: 800000n,
    occurredOn: '2026-10-17',
  });
  assert.deepEqual(await clientBalance(sql, client), {
    owed: 0n,
    held: 65026n,
  });
  await refundCredit(sql, clientId, {
    fromAccountId: ids.KBZPay,
    amount: 65026n,
    occurredOn: '2026-10-18',
  });
  await assert.rejects(undoLatest(sql, id), /already been used or refunded/);
  assert.deepEqual(await clientBalance(sql, client), { owed: 0n, held: 0n });
  await assertBalanced('after refused undo');
});

test('steps are refused when they do not fit the order', opts, async () => {
  const clientId = await createClient(sql, {
    name: 'U Ba',
    contact: '',
    currency: 'MMK',
  });
  const id = await createOrder(sql, clientId, 500, '2026-10-10');
  await assert.rejects(
    markBought(sql, id, [], '2026-10-12'),
    /at least one item/,
  );
  await addLine(sql, id, {
    description: 'Thing',
    options: '',
    link: '',
    quantity: 1,
    unitCost: 1000n,
    currency: 'THB',
  });
  await assert.rejects(
    markBought(
      sql,
      id,
      [{ currency: 'THB', fromAccountId: ids.KBank, amount: 1000n }],
      '2026-10-12',
    ),
    /THB rates/,
  );
  await assert.rejects(markDelivered(sql, id, '2026-10-12'), /quote/);
  await saveTerms(sql, id, 500, [
    { currency: 'THB', charge: parseRate('128')!, cost: parseRate('120')! },
  ]);
  await assert.rejects(
    markBought(
      sql,
      id,
      [{ currency: 'THB', fromAccountId: ids.Wise, amount: 1000n }],
      '2026-10-12',
    ),
    /THB accounts/,
  );
  await assert.rejects(
    recordPayment(sql, id, {
      intoAccountId: ids.KBank,
      amount: 1n,
      occurredOn: '2026-10-12',
    }),
    /MMK accounts/,
  );
  const owes = (await getClient(sql, clientId))!.owesAccountId;
  await assert.rejects(
    recordPayment(sql, id, {
      intoAccountId: owes,
      amount: 1n,
      occurredOn: '2026-10-12',
    }),
    /MMK accounts/,
    'system accounts are not money accounts',
  );
});

test('a double-submitted delivery posts once', opts, async () => {
  const clientId = await createClient(sql, {
    name: 'Ma Su',
    contact: '',
    currency: 'MMK',
  });
  const id = await previewOrder(clientId);
  await markBought(
    sql,
    id,
    [
      { currency: 'THB', fromAccountId: ids.KBank, amount: 459000n },
      { currency: 'USD', fromAccountId: ids.Wise, amount: 2499n },
    ],
    '2026-10-12',
  );
  const results = await Promise.allSettled(
    [1, 2, 3].map(() => markDelivered(sql, id, '2026-10-16')),
  );
  assert.equal(results.filter((r) => r.status === 'fulfilled').length, 1);
  const [{ n }] = await sql<
    { n: bigint }[]
  >`select count(*) as n from fin_transactions where kind = 'client_delivery' and voided_at is null and description like ${`%${'Ma Su'}%`}`;
  assert.equal(n, 1n);
  await assertBalanced('after racing deliveries');
});

test('Entries cannot void client order steps', opts, async () => {
  const [{ id }] = await sql<
    { id: bigint }[]
  >`select id from fin_transactions where kind = 'client_payment' and voided_at is null limit 1`;
  assert.equal(await voidTransaction(sql, id), false);
  const [{ voided }] = await sql<
    { voided: boolean }[]
  >`select voided_at is not null as voided from fin_transactions where id = ${id}`;
  assert.equal(voided, false);
});

// One THB 1.00 item at 80 MMK per THB, no fee: an 80 MMK order.
async function smallOrder(clientId: number) {
  const id = await createOrder(sql, clientId, 0, '2026-10-10');
  await addLine(sql, id, {
    description: 'Small item',
    options: '',
    link: '',
    quantity: 1,
    unitCost: 100n,
    currency: 'THB',
  });
  await saveTerms(sql, id, 0, [
    { currency: 'THB', charge: parseRate('80')!, cost: parseRate('75')! },
  ]);
  return id;
}
const buy = (id: number) =>
  markBought(
    sql,
    id,
    [{ currency: 'THB', fromAccountId: ids.KBank, amount: 100n }],
    '2026-10-12',
  );

test(
  'a payment settles only its own order; the rest becomes credit',
  opts,
  async () => {
    const clientId = await createClient(sql, {
      name: 'Two Orders',
      contact: '',
      currency: 'MMK',
    });
    const client = (await getClient(sql, clientId))!;
    const a = await smallOrder(clientId);
    const b = await smallOrder(clientId);
    for (const id of [a, b]) {
      await buy(id);
      await markDelivered(sql, id, '2026-10-16');
    }
    await recordPayment(sql, b, {
      intoAccountId: ids.KBZPay,
      amount: 160n,
      occurredOn: '2026-10-17',
    });
    const [va, vb] = [(await loadOrder(sql, a))!, (await loadOrder(sql, b))!];
    assert.equal(vb.status, 'closed');
    assert.equal(vb.due, -80n, 'B overpaid by 80');
    assert.equal(va.status, 'delivered');
    assert.equal(va.due, 80n, 'A still owes its own 80');
    assert.deepEqual(
      await clientBalance(sql, client),
      { owed: 80n, held: 80n },
      'ledger matches the orders',
    );
    await assertBalanced('after cross-order payment');
  },
);

test(
  'delivery uses its own deposit and free credit, never another open order’s',
  opts,
  async () => {
    const clientId = await createClient(sql, {
      name: 'Two Deposits',
      contact: '',
      currency: 'MMK',
    });
    const client = (await getClient(sql, clientId))!;
    const a = await smallOrder(clientId);
    const b = await smallOrder(clientId);
    await recordPayment(sql, a, {
      intoAccountId: ids.KBZPay,
      amount: 50n,
      occurredOn: '2026-10-11',
    });
    await recordPayment(sql, b, {
      intoAccountId: ids.KBZPay,
      amount: 50n,
      occurredOn: '2026-10-11',
    });
    await buy(a);
    await markDelivered(sql, a, '2026-10-16');
    let va = (await loadOrder(sql, a))!;
    assert.equal(va.applied, 50n, 'only A’s own deposit');
    assert.equal(va.due, 30n);
    assert.equal(await freeCredit(sql, client), 0n, 'B’s deposit is not free');
    await assert.rejects(
      refundCredit(sql, clientId, {
        fromAccountId: ids.KBZPay,
        amount: 1n,
        occurredOn: '2026-10-17',
      }),
      /Deposits on open orders/,
    );
    await buy(b);
    await markDelivered(sql, b, '2026-10-16');
    const vb = (await loadOrder(sql, b))!;
    assert.equal(vb.applied, 50n);
    assert.equal(vb.due, 30n);
    // Cancelled-order deposits and overpayments are free and do get applied.
    const c = await smallOrder(clientId);
    const d = await smallOrder(clientId);
    await recordPayment(sql, c, {
      intoAccountId: ids.KBZPay,
      amount: 60n,
      occurredOn: '2026-10-11',
    });
    await cancelOrder(sql, c);
    assert.equal(await freeCredit(sql, client), 60n);
    await buy(d);
    await markDelivered(sql, d, '2026-10-16');
    const vd = (await loadOrder(sql, d))!;
    assert.equal(vd.applied, 60n);
    assert.equal(vd.due, 20n);
    va = (await loadOrder(sql, a))!;
    assert.equal(va.due, 30n, 'A unchanged');
    assert.deepEqual(await clientBalance(sql, client), { owed: 80n, held: 0n });
    await assertBalanced('after deposits across orders');
  },
);

test(
  'client and goods accounts never clash with owner account names',
  opts,
  async () => {
    await createAccount(
      sql,
      {
        name: 'Goods bought for clients · THB',
        type: 'asset',
        currency: 'THB',
        scope: 'personal',
      },
      null,
    );
    await createAccount(
      sql,
      {
        name: 'Clash · owes you',
        type: 'asset',
        currency: 'MMK',
        scope: 'personal',
      },
      null,
    );
    const clientId = await createClient(sql, {
      name: 'Clash',
      contact: '',
      currency: 'MMK',
    });
    const id = await smallOrder(clientId);
    await buy(id);
    assert.equal((await loadOrder(sql, id))!.status, 'bought');
    await assert.rejects(
      createClient(sql, { name: 'x'.repeat(61), contact: '', currency: 'MMK' }),
      /60 characters/,
    );
  },
);

test('client goods are not counted as monthly spending', opts, async () => {
  const spending = await monthSpending(sql, '2026-10');
  const accounts = await loadAccounts(sql);
  assert.ok(spending.every((s) => !accounts.get(s.accountId)!.system_key));
});
