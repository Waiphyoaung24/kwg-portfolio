import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  financeToday,
  isIsoDate,
  openingDraft,
  parseEntry,
  revalueDraft,
  todayIn,
  type EntryForm,
  type Line,
} from './entries.ts';
import { sample } from './test-fixtures.ts';

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

const sums = (lines: Line[]) => {
  const m = new Map<string, bigint>();
  for (const l of lines)
    m.set(l.currency, (m.get(l.currency) ?? 0n) + l.amount);
  return [...m.values()];
};

test('expense debits the category and credits the paying account', () => {
  const r = parseEntry(
    form({ amount: '60', account: '10', category: '20', note: ' Lunch ' }),
    sample,
  );
  assert.ok(r.ok);
  assert.equal(r.draft.description, 'Lunch');
  assert.deepEqual(r.draft.lines, [
    { accountId: 20, currency: 'THB', amount: 6000n },
    { accountId: 10, currency: 'THB', amount: -6000n },
  ]);
});

test('expense paid by card raises what is owed on the card', () => {
  const r = parseEntry(
    form({ amount: '1,284.50', account: '13', category: '20' }),
    sample,
  );
  assert.ok(r.ok);
  assert.deepEqual(r.draft.lines[1], {
    accountId: 13,
    currency: 'THB',
    amount: -128450n,
  });
});

test('the paying account decides the currency and its decimals', () => {
  const ok = parseEntry(
    form({ amount: '4,500', account: '11', category: '20' }),
    sample,
  );
  assert.ok(ok.ok);
  assert.equal(ok.draft.lines[0].currency, 'MMK');
  const bad = parseEntry(
    form({ amount: '4500.50', account: '11', category: '20' }),
    sample,
  );
  assert.ok(!bad.ok);
  assert.match(bad.errors.amount, /whole amount/);
});

test('income debits the receiving asset and may not go onto a card', () => {
  const r = parseEntry(
    form({ kind: 'income', amount: '12000', account: '10', category: '21' }),
    sample,
  );
  assert.ok(r.ok);
  assert.deepEqual(r.draft.lines, [
    { accountId: 10, currency: 'THB', amount: 1200000n },
    { accountId: 21, currency: 'THB', amount: -1200000n },
  ]);
  const card = parseEntry(
    form({ kind: 'income', amount: '1', account: '13', category: '21' }),
    sample,
  );
  assert.ok(!card.ok);
  assert.ok(card.errors.account);
});

test('category must match the kind', () => {
  const r = parseEntry(
    form({ amount: '1', account: '10', category: '21' }),
    sample,
  );
  assert.ok(!r.ok);
  assert.ok(r.errors.category);
});

test('same-currency transfer moves money between two accounts', () => {
  const r = parseEntry(
    form({ kind: 'transfer', amount: '500', account: '10', to: '13' }),
    sample,
  );
  assert.ok(r.ok);
  assert.deepEqual(r.draft.lines, [
    { accountId: 13, currency: 'THB', amount: 50000n },
    { accountId: 10, currency: 'THB', amount: -50000n },
  ]);
});

test('cross-currency transfer balances each currency through Currency exchange', () => {
  const r = parseEntry(
    form({
      kind: 'transfer',
      amount: '3,000',
      account: '10',
      to: '12',
      toAmount: '92.50',
    }),
    sample,
  );
  assert.ok(r.ok);
  assert.deepEqual(sums(r.draft.lines), [0n, 0n]);
  assert.deepEqual(
    r.draft.lines
      .filter((l) => l.accountId === 2)
      .map((l) => [l.currency, l.amount]),
    [
      ['THB', 300000n],
      ['USD', -9250n],
    ],
  );
  const missing = parseEntry(
    form({ kind: 'transfer', amount: '3000', account: '10', to: '12' }),
    sample,
  );
  assert.ok(!missing.ok);
  assert.match(missing.errors.toAmount, /USD/);
});

test('transfer to the same account is refused', () => {
  const r = parseEntry(
    form({ kind: 'transfer', amount: '1', account: '10', to: '10' }),
    sample,
  );
  assert.ok(!r.ok);
  assert.ok(r.errors.to);
});

test('archived, system and unknown accounts cannot be used', () => {
  for (const account of ['14', '1', '999', 'x', '']) {
    const r = parseEntry(
      form({ amount: '1', account, category: '20' }),
      sample,
    );
    assert.ok(!r.ok, account);
    assert.ok(r.errors.account, account);
  }
});

test('collects every field error at once', () => {
  const r = parseEntry(
    form({
      amount: 'abc',
      account: '10',
      category: '',
      date: '2026-02-30',
      note: 'x'.repeat(201),
    }),
    sample,
  );
  assert.ok(!r.ok);
  assert.deepEqual(Object.keys(r.errors).sort(), [
    'amount',
    'category',
    'date',
    'note',
  ]);
});

test('unknown kind is refused', () => {
  const r = parseEntry(form({ kind: 'opening' }), sample);
  assert.ok(!r.ok);
});

test('opening balances: assets positive, liabilities as owed, zero skipped', () => {
  assert.deepEqual(
    openingDraft(sample.get(10)!, 4000000n, '2026-10-01', sample)!.lines,
    [
      { accountId: 10, currency: 'THB', amount: 4000000n },
      { accountId: 1, currency: 'THB', amount: -4000000n },
    ],
  );
  assert.deepEqual(
    openingDraft(sample.get(13)!, 648000n, '2026-10-01', sample)!.lines[0],
    {
      accountId: 13,
      currency: 'THB',
      amount: -648000n,
    },
  );
  assert.equal(openingDraft(sample.get(10)!, 0n, '2026-10-01', sample), null);
});

test('revalue books only the difference, and only for assets', () => {
  const d = revalueDraft(
    sample.get(10)!,
    100000n,
    130000n,
    '2026-10-16',
    sample,
  )!;
  assert.deepEqual(d.lines, [
    { accountId: 10, currency: 'THB', amount: 30000n },
    { accountId: 3, currency: 'THB', amount: -30000n },
  ]);
  assert.equal(
    revalueDraft(sample.get(10)!, 5n, 5n, '2026-10-16', sample),
    null,
  );
  assert.equal(
    revalueDraft(sample.get(13)!, 0n, 5n, '2026-10-16', sample),
    null,
  );
});

test('dates', () => {
  assert.ok(isIsoDate('2024-02-29'));
  assert.ok(!isIsoDate('2026-02-29'));
  assert.ok(!isIsoDate('16/10/2026'));
  // 17:30 UTC on 16 Oct is already 17 Oct in Bangkok.
  assert.equal(
    todayIn('Asia/Bangkok', new Date('2026-10-16T17:30:00Z')),
    '2026-10-17',
  );
  assert.equal(todayIn('UTC', new Date('2026-10-16T17:30:00Z')), '2026-10-16');
});

test('an unknown FINANCE_TZ falls back to Bangkok instead of failing', () => {
  const saved = process.env.FINANCE_TZ;
  process.env.FINANCE_TZ = 'Mars/Olympus';
  try {
    assert.equal(financeToday(new Date('2026-10-16T17:30:00Z')), '2026-10-17');
  } finally {
    if (saved === undefined) delete process.env.FINANCE_TZ;
    else process.env.FINANCE_TZ = saved;
  }
});
