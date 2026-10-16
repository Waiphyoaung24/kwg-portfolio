// Turns what the owner typed into balanced posting lines. Pure: no database,
// so every rule here is covered by plain unit tests.
import { minorDigits, parseAmount } from './money.ts';

export type AccountType =
  | 'asset'
  | 'liability'
  | 'income'
  | 'expense'
  | 'equity';
export type Scope = 'personal' | 'business';
export type Kind =
  | 'expense'
  | 'income'
  | 'transfer'
  | 'opening'
  | 'revalue'
  | 'client_payment'
  | 'client_purchase'
  | 'client_delivery'
  | 'client_refund';

// Client order steps are voided only through their order, never from Entries,
// so an order's state and its ledger entries cannot drift apart.
export function isClientKind(kind: string): boolean {
  return kind.startsWith('client_');
}

export interface Account {
  id: number;
  name: string;
  type: AccountType;
  currency: string | null;
  scope: Scope;
  system_key: string | null;
  archived_at: Date | null;
}

// Positive amounts are debits. Each transaction sums to zero per currency.
export interface Line {
  accountId: number;
  currency: string;
  amount: bigint;
}

export interface Draft {
  kind: Kind;
  occurredOn: string;
  description: string;
  lines: Line[];
}

export type Errors = Record<string, string>;
export type Parsed = { ok: true; draft: Draft } | { ok: false; errors: Errors };

export const ENTRY_KINDS = ['expense', 'income', 'transfer'] as const;
export type EntryKind = (typeof ENTRY_KINDS)[number];

export function isBalanceAccount(a: Account): boolean {
  return a.type === 'asset' || a.type === 'liability';
}

export function isIsoDate(s: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(s + 'T00:00:00Z');
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

export function todayIn(timeZone: string, now = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone }).format(now);
}

// "Today" for finance, in FINANCE_TZ. An unknown zone falls back to the
// default instead of failing every page.
export const DEFAULT_TZ = 'Asia/Bangkok';
export function financeToday(now = new Date()): string {
  try {
    return todayIn(process.env.FINANCE_TZ || DEFAULT_TZ, now);
  } catch {
    return todayIn(DEFAULT_TZ, now);
  }
}

export interface EntryForm {
  kind: string;
  amount: string;
  account: string;
  category: string;
  to: string;
  toAmount: string;
  date: string;
  note: string;
}

function lookup(
  accounts: Map<number, Account>,
  raw: string,
): Account | undefined {
  const id = Number(raw);
  if (!Number.isInteger(id)) return undefined;
  const a = accounts.get(id);
  return a && !a.archived_at ? a : undefined;
}

export function parseEntry(
  form: EntryForm,
  accounts: Map<number, Account>,
): Parsed {
  const errors: Errors = {};
  const kind = form.kind as EntryKind;
  if (!ENTRY_KINDS.includes(kind))
    return {
      ok: false,
      errors: { kind: 'Choose Expense, Income or Transfer.' },
    };

  if (!isIsoDate(form.date)) errors.date = 'Enter a date like 2026-10-16.';
  const note = form.note.trim();
  if (note.length > 200) errors.note = 'Keep the note under 200 characters.';

  const from = lookup(accounts, form.account);
  const fromOk =
    from &&
    (kind === 'income' ? from.type === 'asset' : isBalanceAccount(from));
  if (!fromOk) {
    errors.account =
      kind === 'income'
        ? 'Choose the account the money went into.'
        : 'Choose the account the money came from.';
  }

  const currency = fromOk ? from.currency! : null;
  const amount = currency ? parseAmount(form.amount, currency) : null;
  if (currency && amount === null) errors.amount = amountMessage(currency);

  let lines: Line[] = [];
  if (kind === 'expense' || kind === 'income') {
    const want = kind === 'expense' ? 'expense' : 'income';
    const cat = lookup(accounts, form.category);
    if (!cat || cat.type !== want) {
      errors.category =
        kind === 'expense'
          ? 'Choose a category.'
          : 'Choose where the income came from.';
    } else if (fromOk && amount !== null) {
      lines =
        kind === 'expense'
          ? [
              { accountId: cat.id, currency: currency!, amount },
              { accountId: from.id, currency: currency!, amount: -amount },
            ]
          : [
              { accountId: from.id, currency: currency!, amount },
              { accountId: cat.id, currency: currency!, amount: -amount },
            ];
    }
  } else {
    const to = lookup(accounts, form.to);
    if (!to || !isBalanceAccount(to))
      errors.to = 'Choose the account the money went to.';
    else if (fromOk && to.id === from.id)
      errors.to = 'Choose a different account to transfer to.';
    else if (fromOk && amount !== null) {
      if (to.currency === currency) {
        lines = [
          { accountId: to.id, currency: currency!, amount },
          { accountId: from.id, currency: currency!, amount: -amount },
        ];
      } else {
        const received = parseAmount(form.toAmount, to.currency!);
        if (received === null) {
          errors.toAmount = `Enter the amount received in ${to.currency}. ${amountMessage(to.currency!)}`;
        } else {
          const fx = systemAccount(accounts, 'fx');
          lines = [
            { accountId: from.id, currency: currency!, amount: -amount },
            { accountId: fx.id, currency: currency!, amount },
            { accountId: to.id, currency: to.currency!, amount: received },
            { accountId: fx.id, currency: to.currency!, amount: -received },
          ];
        }
      }
    }
  }

  if (Object.keys(errors).length) return { ok: false, errors };
  return {
    ok: true,
    draft: { kind, occurredOn: form.date, description: note, lines },
  };
}

export function amountMessage(currency: string): string {
  return minorDigits(currency) === 0
    ? `Enter a whole amount greater than 0, like 4,500.`
    : `Enter an amount greater than 0, like 1,284.50.`;
}

export function systemAccount(
  accounts: Map<number, Account>,
  key: string,
): Account {
  for (const a of accounts.values()) if (a.system_key === key) return a;
  throw new Error(`Missing system account ${key}`);
}

// Opening balance for a new account. For a liability the amount is what is
// owed. Returns null when there is nothing to record.
export function openingDraft(
  account: Account,
  amount: bigint,
  occurredOn: string,
  accounts: Map<number, Account>,
): Draft | null {
  if (amount === 0n || !account.currency) return null;
  const signed = account.type === 'liability' ? -amount : amount;
  const opening = systemAccount(accounts, 'opening');
  return {
    kind: 'opening',
    occurredOn,
    description: 'Opening balance',
    lines: [
      { accountId: account.id, currency: account.currency, amount: signed },
      { accountId: opening.id, currency: account.currency, amount: -signed },
    ],
  };
}

// Sets an asset to a new value by booking the difference to Revaluation.
export function revalueDraft(
  account: Account,
  current: bigint,
  next: bigint,
  occurredOn: string,
  accounts: Map<number, Account>,
): Draft | null {
  const diff = next - current;
  if (diff === 0n || account.type !== 'asset' || !account.currency) return null;
  const reval = systemAccount(accounts, 'revaluation');
  return {
    kind: 'revalue',
    occurredOn,
    description: 'Revalued',
    lines: [
      { accountId: account.id, currency: account.currency, amount: diff },
      { accountId: reval.id, currency: account.currency, amount: -diff },
    ],
  };
}
