// Client order arithmetic and the ledger entries each order step writes. Pure:
// no database, so pricing, rounding and every posting rule are unit-tested.
import type { Account, Draft, Line } from './entries.ts';
import { minorDigits } from './money.ts';

export const MICRO = 1_000_000n;

// Rates such as "128.5" or "4,500" (billing units per 1 purchase unit), kept
// to 6 decimals as integer micro-units.
export function parseRate(text: string): bigint | null {
  const m = /^(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,6}))?$/.exec(text.trim());
  if (!m) return null;
  const whole = m[1].replaceAll(',', '');
  if (whole.replace(/^0+/, '').length > 9) return null;
  const v = BigInt(whole) * MICRO + BigInt((m[2] ?? '').padEnd(6, '0'));
  return v > 0n ? v : null;
}

export function formatRate(micro: bigint): string {
  const whole = (micro / MICRO)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  let frac = (micro % MICRO).toString().padStart(6, '0').replace(/0+$/, '');
  if (frac.length < 2) frac = frac.padEnd(2, '0');
  return `${whole}.${frac}`;
}

export function rateInputValue(micro: bigint): string {
  return formatRate(micro).replaceAll(',', '');
}

// "5", "5.5", "12.25" → basis points (500, 550, 1225); 0–100 %.
export function parsePercent(text: string): number | null {
  const m = /^(\d{1,3})(?:\.(\d{1,2}))?$/.exec(text.trim());
  if (!m) return null;
  const bp = Number(m[1]) * 100 + Number((m[2] ?? '').padEnd(2, '0'));
  return bp <= 10000 ? bp : null;
}

export function formatPercent(bp: number): string {
  const whole = Math.floor(bp / 100);
  const frac = String(bp % 100)
    .padStart(2, '0')
    .replace(/0+$/, '');
  return frac ? `${whole}.${frac}%` : `${whole}%`;
}

// Half up, for non-negative values (all order amounts are).
function divRound(num: bigint, den: bigint): bigint {
  return (num * 2n + den) / (den * 2n);
}

// Converts an amount between currencies at a micro-unit rate, rounding half
// up to the target currency's minor unit.
export function convert(
  amount: bigint,
  from: string,
  rate: bigint,
  to: string,
): bigint {
  const num = amount * rate * 10n ** BigInt(minorDigits(to));
  const den = 10n ** BigInt(minorDigits(from)) * MICRO;
  return divRound(num, den);
}

export function percentOf(amount: bigint, bp: number): bigint {
  return divRound(amount * BigInt(bp), 10000n);
}

export interface OrderLine {
  id: number;
  description: string;
  options: string;
  link: string;
  quantity: number;
  unitCost: bigint;
  currency: string;
}

export interface Rate {
  currency: string;
  charge: bigint;
  cost: bigint;
}

export interface Quote {
  prices: Map<number, bigint | null>;
  itemTotal: bigint;
  fee: bigint;
  total: bigint;
  // Purchase-currency totals of the lines, before anything is bought.
  lineCost: Map<string, bigint>;
  missingRates: string[];
}

export function quote(
  lines: OrderLine[],
  rates: Map<string, Rate>,
  feeBp: number,
  billing: string,
): Quote {
  const prices = new Map<number, bigint | null>();
  const lineCost = new Map<string, bigint>();
  const missing = new Set<string>();
  let itemTotal = 0n;
  for (const l of lines) {
    const cost = l.unitCost * BigInt(l.quantity);
    lineCost.set(l.currency, (lineCost.get(l.currency) ?? 0n) + cost);
    const rate = rates.get(l.currency);
    if (!rate) {
      missing.add(l.currency);
      prices.set(l.id, null);
      continue;
    }
    const price = convert(cost, l.currency, rate.charge, billing);
    prices.set(l.id, price);
    itemTotal += price;
  }
  const fee = percentOf(itemTotal, feeBp);
  return {
    prices,
    itemTotal,
    fee,
    total: itemTotal + fee,
    lineCost,
    missingRates: [...missing].sort(),
  };
}

// What the goods really cost in the billing currency, at the owner's cost rates.
export function realCost(
  paid: Map<string, bigint>,
  rates: Map<string, Rate>,
  billing: string,
): bigint | null {
  let sum = 0n;
  for (const [currency, amount] of paid) {
    const rate = rates.get(currency);
    if (!rate) return null;
    sum += convert(amount, currency, rate.cost, billing);
  }
  return sum;
}

export type Status =
  | 'quote'
  | 'deposit'
  | 'bought'
  | 'delivered'
  | 'closed'
  | 'cancelled';

export const STATUS_STEPS: Status[] = [
  'quote',
  'deposit',
  'bought',
  'delivered',
  'closed',
];

export function deriveStatus(s: {
  cancelled: boolean;
  delivered: boolean;
  bought: boolean;
  payments: number;
  due: bigint;
}): Status {
  if (s.cancelled) return 'cancelled';
  if (s.delivered) return s.due <= 0n ? 'closed' : 'delivered';
  if (s.bought) return 'bought';
  return s.payments > 0 ? 'deposit' : 'quote';
}

export function orderRef(id: number): string {
  return `ORD-${String(id).padStart(4, '0')}`;
}

// ── Ledger entries ──────────────────────────────────────────────────────────

export interface ClientAccounts {
  owes: Account;
  deposits: Account;
}

// Before delivery a payment is held as a deposit. After delivery it settles
// what the client owes, and any excess becomes credit.
export function paymentDraft(p: {
  client: ClientAccounts;
  into: Account;
  amount: bigint;
  occurredOn: string;
  afterDelivery: boolean;
  owed: bigint;
  description: string;
}): Draft {
  const c = p.into.currency!;
  const toOwes = p.afterDelivery
    ? p.owed > 0n
      ? p.amount < p.owed
        ? p.amount
        : p.owed
      : 0n
    : 0n;
  const toDeposits = p.amount - toOwes;
  const lines: Line[] = [
    { accountId: p.into.id, currency: c, amount: p.amount },
  ];
  if (toOwes > 0n)
    lines.push({ accountId: p.client.owes.id, currency: c, amount: -toOwes });
  if (toDeposits > 0n)
    lines.push({
      accountId: p.client.deposits.id,
      currency: c,
      amount: -toDeposits,
    });
  return {
    kind: 'client_payment',
    occurredOn: p.occurredOn,
    description: p.description,
    lines,
  };
}

export interface Purchase {
  from: Account;
  goods: Account;
  amount: bigint;
}

export function purchaseDraft(
  parts: Purchase[],
  occurredOn: string,
  description: string,
): Draft {
  const lines: Line[] = [];
  for (const p of parts) {
    lines.push({
      accountId: p.goods.id,
      currency: p.goods.currency!,
      amount: p.amount,
    });
    lines.push({
      accountId: p.from.id,
      currency: p.from.currency!,
      amount: -p.amount,
    });
  }
  return { kind: 'client_purchase', occurredOn, description, lines };
}

// Books the sale, moves bought goods to cost, and applies held credit.
export function deliveryDraft(d: {
  client: ClientAccounts;
  sales: Account;
  cost: Account;
  goods: { goods: Account; amount: bigint }[];
  total: bigint;
  held: bigint;
  occurredOn: string;
  description: string;
}): { draft: Draft; applied: bigint } {
  const c = d.client.owes.currency!;
  const lines: Line[] = [
    { accountId: d.client.owes.id, currency: c, amount: d.total },
    { accountId: d.sales.id, currency: c, amount: -d.total },
  ];
  for (const g of d.goods) {
    lines.push({
      accountId: d.cost.id,
      currency: g.goods.currency!,
      amount: g.amount,
    });
    lines.push({
      accountId: g.goods.id,
      currency: g.goods.currency!,
      amount: -g.amount,
    });
  }
  const applied = d.held > 0n ? (d.held < d.total ? d.held : d.total) : 0n;
  if (applied > 0n) {
    lines.push({
      accountId: d.client.deposits.id,
      currency: c,
      amount: applied,
    });
    lines.push({ accountId: d.client.owes.id, currency: c, amount: -applied });
  }
  return {
    draft: {
      kind: 'client_delivery',
      occurredOn: d.occurredOn,
      description: d.description,
      lines,
    },
    applied,
  };
}

export function refundDraft(r: {
  client: ClientAccounts;
  from: Account;
  amount: bigint;
  occurredOn: string;
  description: string;
}): Draft {
  const c = r.from.currency!;
  return {
    kind: 'client_refund',
    occurredOn: r.occurredOn,
    description: r.description,
    lines: [
      { accountId: r.client.deposits.id, currency: c, amount: r.amount },
      { accountId: r.from.id, currency: c, amount: -r.amount },
    ],
  };
}

export function isHttpLink(s: string): boolean {
  if (!/^https?:\/\//i.test(s)) return false;
  try {
    new URL(s);
    return true;
  } catch {
    return false;
  }
}
