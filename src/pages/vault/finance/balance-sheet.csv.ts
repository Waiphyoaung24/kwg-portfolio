import type { APIRoute } from 'astro';
import { amountInputValue } from '../../../lib/finance/money.ts';
import { loadSheet } from '../../../lib/finance/sheet.ts';

export const prerender = false;

const cell = (v: string) => `"${v.replaceAll('"', '""')}"`;
// Account names are free text: neutralise a leading formula character so a
// name like "=HYPERLINK(...)" cannot run when the file opens in a spreadsheet.
const text = (v: string) => (/^[=+\-@\t\r]/.test(v) ? `'${v}` : v);

export const GET: APIRoute = async ({ url }) => {
  const { asOf, scope, columns } = await loadSheet(url);
  const rows: string[][] = [
    ['as_of', 'scope', 'currency', 'section', 'line', 'amount'],
  ];
  for (const c of columns) {
    const amt = (v: bigint) => amountInputValue(v, c.currency);
    const add = (section: string, line: string, v: bigint) =>
      rows.push([asOf, scope, c.currency, section, text(line), amt(v)]);
    for (const l of c.own) add('own', l.label, l.amount);
    add('own', 'Total', c.ownTotal);
    for (const l of c.owe) add('owe', l.label, l.amount);
    add('owe', 'Total', c.oweTotal);
    add('net_worth', 'Net worth', c.net);
    if (c.equity) {
      add('net_worth', 'Opening balances', c.equity.opening);
      add('net_worth', 'Earnings to date', c.equity.earnings);
      add('net_worth', 'Currency exchange', c.equity.fx);
      add('net_worth', 'Revaluation', c.equity.revaluation);
    }
  }
  const body = rows.map((r) => r.map(cell).join(',')).join('\r\n') + '\r\n';
  return new Response(body, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="balance-sheet-${asOf}-${scope}.csv"`,
    },
  });
};
