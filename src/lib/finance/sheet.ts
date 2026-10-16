// Loads the balance sheet for a request; shared by the page and the CSV.
import { db } from './db.ts';
import { financeToday, isIsoDate, type Scope } from './entries.ts';
import { loadAccounts } from './ledger.ts';
import { balanceSheet, balances, type SheetColumn } from './reports.ts';

export const SCOPES = ['personal', 'business', 'all'] as const;
export type SheetScope = Scope | 'all';

export async function loadSheet(
  url: URL,
): Promise<{ asOf: string; scope: SheetScope; columns: SheetColumn[] }> {
  const today = financeToday();
  const asOfRaw = url.searchParams.get('asOf') ?? '';
  const asOf = isIsoDate(asOfRaw) ? asOfRaw : today;
  const scopeRaw = url.searchParams.get('scope') ?? 'all';
  const scope = (SCOPES as readonly string[]).includes(scopeRaw)
    ? (scopeRaw as SheetScope)
    : 'all';
  const sql = await db();
  const accounts = await loadAccounts(sql);
  return {
    asOf,
    scope,
    columns: balanceSheet(accounts, await balances(sql, asOf), scope),
  };
}
