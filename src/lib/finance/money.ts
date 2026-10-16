// Money is always a bigint count of the currency's minor unit (satang, cents).
// Nothing in finance touches floating point.

const KNOWN = new Set(Intl.supportedValuesOf('currency'));

// ISO 4217 minor units, overridden where everyday use differs: kyat is
// written in whole units in practice, so MMK amounts take no decimals.
const DIGITS: Record<string, number> = {
  MMK: 0,
  JPY: 0,
  KRW: 0,
  VND: 0,
  CLP: 0,
  ISK: 0,
  PYG: 0,
  UGX: 0,
  XAF: 0,
  XOF: 0,
  BHD: 3,
  IQD: 3,
  JOD: 3,
  KWD: 3,
  LYD: 3,
  OMR: 3,
  TND: 3,
};

export function isCurrency(code: string): boolean {
  return /^[A-Z]{3}$/.test(code) && KNOWN.has(code);
}

export function minorDigits(currency: string): number {
  return DIGITS[currency] ?? 2;
}

const MAX_DIGITS = 15;

// Parses a positive amount as typed by a person: "1,284.50", "60", "4500".
// Commas are accepted only as thousands separators. Returns null when the
// text is not a valid positive amount in this currency.
export function parseAmount(text: string, currency: string): bigint | null {
  const s = text.trim();
  const m = /^(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?$/.exec(s);
  if (!m) return null;
  const whole = m[1].replaceAll(',', '');
  const frac = m[2] ?? '';
  const digits = minorDigits(currency);
  if (frac.length > digits) return null;
  if (whole.replace(/^0+/, '').length + digits > MAX_DIGITS) return null;
  const minor = BigInt(whole + frac.padEnd(digits, '0'));
  return minor > 0n ? minor : null;
}

// "0" or "0.00": an explicit zero, which parseAmount rejects.
export function isZeroText(text: string): boolean {
  return /^0+(?:\.0+)?$/.test(text.trim());
}

// Formats minor units with thousands separators and the currency's decimals.
export function formatAmount(minor: bigint, currency: string): string {
  const digits = minorDigits(currency);
  const neg = minor < 0n;
  const abs = (neg ? -minor : minor).toString().padStart(digits + 1, '0');
  const whole = abs.slice(0, abs.length - digits);
  const frac = abs.slice(abs.length - digits);
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return (neg ? '−' : '') + grouped + (digits ? '.' + frac : '');
}

// The plain form for an input's value attribute: no grouping, ASCII minus.
export function amountInputValue(minor: bigint, currency: string): string {
  return formatAmount(minor, currency).replaceAll(',', '').replace('−', '-');
}
