import assert from 'node:assert/strict';
import { test } from 'node:test';
import { sample } from './test-fixtures.ts';
import {
  balanceSheet,
  describe,
  isMonth,
  monthRange,
  shiftMonth,
  type Balance,
} from './reports.ts';

// The preview's example book: THB with a card and an FX transfer out, MMK
// with spending, USD received through the transfer.
const sums: Balance[] = [
  { accountId: 10, currency: 'THB', balance: 5137000n },
  { accountId: 13, currency: 'THB', balance: -648000n },
  { accountId: 1, currency: 'THB', balance: -4000000n },
  { accountId: 2, currency: 'THB', balance: 300000n },
  { accountId: 20, currency: 'THB', balance: 411000n },
  { accountId: 21, currency: 'THB', balance: -1200000n },
  { accountId: 11, currency: 'MMK', balance: 247000n },
  { accountId: 1, currency: 'MMK', balance: -300000n },
  { accountId: 20, currency: 'MMK', balance: 53000n },
  { accountId: 12, currency: 'USD', balance: 9250n },
  { accountId: 2, currency: 'USD', balance: -9250n },
];

test('balance sheet: own, owe and net per currency, and the identity holds', () => {
  const cols = balanceSheet(sample, sums, 'all');
  assert.deepEqual(
    cols.map((c) => c.currency),
    ['MMK', 'THB', 'USD'],
  );
  const thb = cols.find((c) => c.currency === 'THB')!;
  assert.equal(thb.ownTotal, 5137000n);
  assert.equal(thb.oweTotal, 648000n);
  assert.equal(thb.net, 4489000n);
  assert.deepEqual(thb.equity, {
    opening: 4000000n,
    earnings: 789000n,
    fx: -300000n,
    revaluation: 0n,
  });
  for (const c of cols) assert.equal(c.balanced, true, c.currency);
  const usd = cols.find((c) => c.currency === 'USD')!;
  assert.equal(usd.net, 9250n);
  assert.equal(usd.equity!.fx, 9250n);
});

test('a broken book is flagged, not hidden', () => {
  const broken = [...sums, { accountId: 10, currency: 'THB', balance: 1n }];
  const cols = balanceSheet(
    sample,
    broken.filter((b, i) => !(b.accountId === 10 && i === 0)),
    'all',
  );
  assert.equal(cols.find((c) => c.currency === 'THB')!.balanced, false);
});

test('scoped views filter accounts and skip the equity breakdown', () => {
  const business = balanceSheet(sample, sums, 'business');
  assert.deepEqual(
    business.map((c) => c.currency),
    ['USD'],
  );
  assert.equal(business[0].equity, null);
  assert.equal(business[0].balanced, null);
  const personal = balanceSheet(sample, sums, 'personal');
  assert.deepEqual(
    personal.map((c) => c.currency),
    ['MMK', 'THB'],
  );
});

test('archived accounts leave the sheet once empty', () => {
  const cols = balanceSheet(sample, sums, 'all');
  assert.ok(
    !cols
      .find((c) => c.currency === 'THB')!
      .own.some((l) => l.account.id === 14),
  );
  const withMoney = balanceSheet(
    sample,
    [...sums, { accountId: 14, currency: 'THB', balance: 100n }],
    'all',
  );
  assert.ok(
    withMoney
      .find((c) => c.currency === 'THB')!
      .own.some((l) => l.account.id === 14),
  );
});

test('describe reads expenses and cross-currency transfers', () => {
  const exp = describe(
    {
      id: 1n,
      kind: 'expense',
      occurredOn: '2026-10-16',
      description: '',
      voidedAt: null,
      lines: [
        { accountId: 20, currency: 'THB', amount: 6000n },
        { accountId: 10, currency: 'THB', amount: -6000n },
      ],
    },
    sample,
  );
  assert.deepEqual(exp, {
    category: 'Food',
    account: 'KBank',
    amounts: [{ currency: 'THB', amount: -6000n }],
  });
  const fx = describe(
    {
      id: 2n,
      kind: 'transfer',
      occurredOn: '2026-10-14',
      description: '',
      voidedAt: null,
      lines: [
        { accountId: 10, currency: 'THB', amount: -300000n },
        { accountId: 2, currency: 'THB', amount: 300000n },
        { accountId: 12, currency: 'USD', amount: 9250n },
        { accountId: 2, currency: 'USD', amount: -9250n },
      ],
    },
    sample,
  );
  assert.equal(fx.account, 'KBank → Wise');
  assert.deepEqual(fx.amounts, [
    { currency: 'THB', amount: -300000n },
    { currency: 'USD', amount: 9250n },
  ]);
});

test('month helpers', () => {
  assert.ok(isMonth('2026-10'));
  assert.ok(!isMonth('2026-13'));
  assert.deepEqual(monthRange('2026-12'), {
    from: '2026-12-01',
    until: '2027-01-01',
  });
  assert.equal(shiftMonth('2026-01', -1), '2025-12');
  assert.equal(shiftMonth('2026-12', 1), '2027-01');
});
