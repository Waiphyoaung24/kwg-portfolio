import assert from 'node:assert/strict';
import { test } from 'node:test';
import type { Account, Line } from './entries.ts';
import {
  convert,
  deliveryDraft,
  deriveStatus,
  formatPercent,
  formatRate,
  isHttpLink,
  orderRef,
  parsePercent,
  parseRate,
  paymentDraft,
  purchaseDraft,
  quote,
  realCost,
  refundDraft,
  type OrderLine,
  type Rate,
} from './orders.ts';

// The preview order ORD-0042: THB and USD lines billed in MMK.
const lines: OrderLine[] = [
  {
    id: 1,
    description: 'Nike Air Max 90',
    options: 'Size 38',
    link: '',
    quantity: 1,
    unitCost: 329000n,
    currency: 'THB',
  },
  {
    id: 2,
    description: 'Uniqlo AIRism T-shirt',
    options: 'M',
    link: '',
    quantity: 2,
    unitCost: 59000n,
    currency: 'THB',
  },
  {
    id: 3,
    description: 'Kindle cover',
    options: '',
    link: '',
    quantity: 1,
    unitCost: 2499n,
    currency: 'USD',
  },
  {
    id: 4,
    description: 'Shop delivery',
    options: '',
    link: '',
    quantity: 1,
    unitCost: 12000n,
    currency: 'THB',
  },
];
const rates = new Map<string, Rate>([
  [
    'THB',
    { currency: 'THB', charge: parseRate('128')!, cost: parseRate('122.5')! },
  ],
  [
    'USD',
    { currency: 'USD', charge: parseRate('4,500')!, cost: parseRate('4320')! },
  ],
]);

test('rates parse to micro-units and format back', () => {
  assert.equal(parseRate('128'), 128_000_000n);
  assert.equal(parseRate('122.5'), 122_500_000n);
  assert.equal(parseRate('4,500'), 4_500_000_000n);
  assert.equal(parseRate('0.027345'), 27_345n);
  for (const bad of ['', '0', '-1', '1.2345678', 'abc', '1,23', '9999999999'])
    assert.equal(parseRate(bad), null, bad);
  assert.equal(formatRate(122_500_000n), '122.50');
  assert.equal(formatRate(4_500_000_000n), '4,500.00');
  assert.equal(formatRate(27_345n), '0.027345');
});

test('percent parses to basis points', () => {
  assert.equal(parsePercent('5'), 500);
  assert.equal(parsePercent('5.5'), 550);
  assert.equal(parsePercent('0'), 0);
  assert.equal(parsePercent('100'), 10000);
  for (const bad of ['101', '5.555', '-1', '', 'x'])
    assert.equal(parsePercent(bad), null, bad);
  assert.equal(formatPercent(500), '5%');
  assert.equal(formatPercent(1225), '12.25%');
});

test('conversion rounds half up to the target currency', () => {
  assert.equal(convert(329000n, 'THB', 128_000_000n, 'MMK'), 421120n);
  assert.equal(convert(2499n, 'USD', 4_500_000_000n, 'MMK'), 112455n);
  // 0.01 THB at 50 MMK = 0.5 MMK → 1; at 49.999999 → 0.49999999 → 0.
  assert.equal(convert(1n, 'THB', 50_000_000n, 'MMK'), 1n);
  assert.equal(convert(1n, 'THB', 49_999_999n, 'MMK'), 0n);
  // MMK → THB keeps satang: 1000 MMK at 0.0078 = 7.80 THB.
  assert.equal(convert(1000n, 'MMK', 7_800n, 'THB'), 780n);
});

test('the preview order prices exactly', () => {
  const q = quote(lines, rates, 500, 'MMK');
  assert.deepEqual([...q.prices.values()], [421120n, 151040n, 112455n, 15360n]);
  assert.equal(q.itemTotal, 699975n);
  assert.equal(q.fee, 34999n, '34,998.75 rounds up');
  assert.equal(q.total, 734974n);
  assert.deepEqual(
    [...q.lineCost],
    [
      ['THB', 459000n],
      ['USD', 2499n],
    ],
  );
  assert.deepEqual(q.missingRates, []);
  const cost = realCost(q.lineCost, rates, 'MMK')!;
  assert.equal(cost, 670232n);
  assert.equal(q.total - cost, 64742n, 'profit');
  assert.equal(
    q.itemTotal - cost + q.fee,
    64742n,
    'rate margin + fee = profit',
  );
});

test('missing rates are reported and excluded, not guessed', () => {
  const q = quote(lines, new Map([['THB', rates.get('THB')!]]), 500, 'MMK');
  assert.deepEqual(q.missingRates, ['USD']);
  assert.equal(q.prices.get(3), null);
  assert.equal(q.itemTotal, 587520n);
  assert.equal(realCost(q.lineCost, new Map(), 'MMK'), null);
});

test('real cost uses what was actually paid', () => {
  const paid = new Map([
    ['THB', 470000n],
    ['USD', 2499n],
  ]);
  assert.equal(realCost(paid, rates, 'MMK'), 575750n + 107957n);
});

test('status follows the steps', () => {
  const base = {
    cancelled: false,
    delivered: false,
    bought: false,
    payments: 0,
    due: 100n,
  };
  assert.equal(deriveStatus(base), 'quote');
  assert.equal(deriveStatus({ ...base, payments: 1 }), 'deposit');
  assert.equal(deriveStatus({ ...base, payments: 1, bought: true }), 'bought');
  assert.equal(
    deriveStatus({ ...base, bought: true, delivered: true }),
    'delivered',
  );
  assert.equal(
    deriveStatus({ ...base, bought: true, delivered: true, due: 0n }),
    'closed',
  );
  assert.equal(deriveStatus({ ...base, delivered: true, due: -5n }), 'closed');
  assert.equal(
    deriveStatus({ ...base, payments: 1, cancelled: true }),
    'cancelled',
  );
  assert.equal(orderRef(42), 'ORD-0042');
});

const acct = (
  id: number,
  type: Account['type'],
  currency: string | null,
): Account => ({
  id,
  name: `#${id}`,
  type,
  currency,
  scope: 'business',
  system_key: null,
  archived_at: null,
});
const owes = acct(100, 'asset', 'MMK');
const deposits = acct(101, 'liability', 'MMK');
const kbz = acct(10, 'asset', 'MMK');
const kbank = acct(11, 'asset', 'THB');
const wise = acct(12, 'asset', 'USD');
const goodsThb = acct(20, 'asset', 'THB');
const goodsUsd = acct(21, 'asset', 'USD');
const sales = acct(30, 'income', null);
const cost = acct(31, 'expense', null);
const client = { owes, deposits };

const balanced = (ls: Line[]) => {
  const m = new Map<string, bigint>();
  for (const l of ls) m.set(l.currency, (m.get(l.currency) ?? 0n) + l.amount);
  return [...m.values()].every((v) => v === 0n);
};

test('a deposit before delivery is held for the client', () => {
  const d = paymentDraft({
    client,
    into: kbz,
    amount: 370000n,
    occurredOn: '2026-10-11',
    afterDelivery: false,
    owed: 0n,
    description: '',
  });
  assert.ok(balanced(d.lines));
  assert.deepEqual(d.lines, [
    { accountId: 10, currency: 'MMK', amount: 370000n },
    { accountId: 101, currency: 'MMK', amount: -370000n },
  ]);
});

test('a payment after delivery settles what is owed; any excess becomes credit', () => {
  const exact = paymentDraft({
    client,
    into: kbz,
    amount: 364974n,
    occurredOn: 'x',
    afterDelivery: true,
    owed: 364974n,
    description: '',
  });
  assert.deepEqual(
    exact.lines.map((l) => [l.accountId, l.amount]),
    [
      [10, 364974n],
      [100, -364974n],
    ],
  );
  const over = paymentDraft({
    client,
    into: kbz,
    amount: 400000n,
    occurredOn: 'x',
    afterDelivery: true,
    owed: 364974n,
    description: '',
  });
  assert.ok(balanced(over.lines));
  assert.deepEqual(
    over.lines.map((l) => [l.accountId, l.amount]),
    [
      [10, 400000n],
      [100, -364974n],
      [101, -35026n],
    ],
  );
});

test('purchase moves money into goods bought, per currency', () => {
  const d = purchaseDraft(
    [
      { from: kbank, goods: goodsThb, amount: 459000n },
      { from: wise, goods: goodsUsd, amount: 2499n },
    ],
    '2026-10-12',
    '',
  );
  assert.ok(balanced(d.lines));
  assert.equal(d.kind, 'client_purchase');
  assert.equal(d.lines.length, 4);
});

test('delivery books the sale, moves goods to cost and applies held credit', () => {
  const { draft, applied } = deliveryDraft({
    client,
    sales,
    cost,
    goods: [
      { goods: goodsThb, amount: 459000n },
      { goods: goodsUsd, amount: 2499n },
    ],
    total: 734974n,
    held: 370000n,
    occurredOn: '2026-10-16',
    description: '',
  });
  assert.ok(balanced(draft.lines));
  assert.equal(applied, 370000n);
  const owesNet = draft.lines
    .filter((l) => l.accountId === 100)
    .reduce((s, l) => s + l.amount, 0n);
  assert.equal(owesNet, 364974n, 'balance due');
  const capped = deliveryDraft({
    client,
    sales,
    cost,
    goods: [{ goods: goodsThb, amount: 1n }],
    total: 1000n,
    held: 5000n,
    occurredOn: 'x',
    description: '',
  });
  assert.equal(capped.applied, 1000n, 'never applies more than the total');
  const none = deliveryDraft({
    client,
    sales,
    cost,
    goods: [{ goods: goodsThb, amount: 1n }],
    total: 1000n,
    held: 0n,
    occurredOn: 'x',
    description: '',
  });
  assert.equal(none.applied, 0n);
  assert.equal(none.draft.lines.length, 4);
});

test('refund pays held credit back out', () => {
  const d = refundDraft({
    client,
    from: kbz,
    amount: 35026n,
    occurredOn: 'x',
    description: '',
  });
  assert.ok(balanced(d.lines));
  assert.deepEqual(
    d.lines.map((l) => [l.accountId, l.amount]),
    [
      [101, 35026n],
      [10, -35026n],
    ],
  );
});

test('only http and https links are accepted', () => {
  assert.ok(isHttpLink('https://www.nike.com/th/t/air-max-90'));
  assert.ok(isHttpLink('http://shop.example/item?id=1'));
  for (const bad of [
    'javascript:alert(1)',
    'ftp://x',
    'www.nike.com',
    'https://',
    'data:text/html,hi',
  ]) {
    assert.ok(!isHttpLink(bad), bad);
  }
});
