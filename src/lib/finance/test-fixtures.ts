// Shared example book for the finance unit tests.
import type { Account } from './entries.ts';

const acct = (
  id: number,
  name: string,
  type: Account['type'],
  currency: string | null,
  extra: Partial<Account> = {},
): Account => ({
  id,
  name,
  type,
  currency,
  scope: 'personal',
  system_key: null,
  archived_at: null,
  ...extra,
});

export const sample = new Map<number, Account>(
  [
    acct(1, 'Opening balances', 'equity', null, { system_key: 'opening' }),
    acct(2, 'Currency exchange', 'equity', null, { system_key: 'fx' }),
    acct(3, 'Revaluation', 'equity', null, { system_key: 'revaluation' }),
    acct(10, 'KBank', 'asset', 'THB'),
    acct(11, 'Cash', 'asset', 'MMK'),
    acct(12, 'Wise', 'asset', 'USD', { scope: 'business' }),
    acct(13, 'KTC card', 'liability', 'THB'),
    acct(14, 'Old wallet', 'asset', 'THB', { archived_at: new Date() }),
    acct(20, 'Food', 'expense', null),
    acct(21, 'Salary', 'income', null),
  ].map((a) => [a.id, a]),
);
