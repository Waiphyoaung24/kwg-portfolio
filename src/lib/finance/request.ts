// Small helpers shared by the finance pages.

export function field(form: FormData, name: string): string {
  const v = form.get(name);
  return typeof v === 'string' ? v : '';
}

// Cloudflare's tunnel sets CF-Connecting-IP; without it, the socket address.
// Used only to bucket failed sign-ins, so a spoofed header can at most move
// an attacker to the overall limit.
export function clientKey(
  request: Request,
  clientAddress: () => string,
): string {
  const cf = request.headers.get('cf-connecting-ip');
  if (cf) return `cf:${cf.slice(0, 64)}`;
  try {
    return `ip:${clientAddress()}`;
  } catch {
    return 'unknown';
  }
}

export function parseId(raw: string | null | undefined): number | null {
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 && n < 2 ** 31 ? n : null;
}
