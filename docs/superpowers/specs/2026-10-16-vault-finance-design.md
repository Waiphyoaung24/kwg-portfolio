# Vault Finance — design

Date: 2026-10-16. Owner-approved through brainstorming, section by section, plus
a visual preview of the quick-add, entries, balance sheet and sign-in screens.

## Goal

Replace the self-hosted Firefly III link behind **Vault → Finance** with the
owner's own tools, built in this repository on one double-entry ledger:

1. **Daily expenses** (this sub-project): expense, income and transfer entry.
2. **Balance sheet** (this sub-project): own / owe / net worth per currency.
3. **Client accounting for online purchasing** (later sub-project, own design
   round). The owner is a purchasing agent: buys online for clients, takes
   deposits or pays upfront, tracks what each client owes and the fee earned.

## Decisions

| Topic | Decision |
| --- | --- |
| Firefly III | Empty; removed cleanly. VPS volume deletion is a separate, owner-confirmed step. |
| Currencies | Any ISO 4217 code. Totals per currency, never converted. |
| Entry | Phone quick-add and desktop table, equally. |
| Access | Owner password checked on the server (not Cloudflare Access). |
| Client money | Paid from mixed personal and business accounts, so all money lives in one ledger; accounts carry a personal/business scope. |
| Engine | Double-entry ledger in the existing app Postgres. |

## Structure

Pages (on-demand rendered, guarded by `src/middleware.ts`):

- `/vault/finance/login`, `/vault/finance/logout` (POST)
- `/vault/finance` — overview: balances by account, this month's spending by
  category per currency
- `/vault/finance/entries` — quick-add form (stacked on phone, one row on
  desktop) plus the month's table with account/category filters and Void
- `/vault/finance/accounts` — add accounts with opening balance, categories,
  archive, revalue
- `/vault/finance/accounts/[id]` — one account's entries up to a date with a
  running balance (balance-sheet drill-down)
- `/vault/finance/balance-sheet` and `/vault/finance/balance-sheet.csv`

Forms post back to their own page and redirect after success (POST/Redirect/GET).
There is no JSON API. Astro's default `security.checkOrigin` rejects form posts
whose `Origin` differs from the request URL; `security.allowedDomains` trusts the
tunnel's forwarded host and protocol for `waiphyoaung.com` so that URL is the
real `https` origin in production. The middleware additionally refuses any
unsafe method whose `Sec-Fetch-Site` is not `same-origin` (or whose `Origin`
host differs when that header is absent).

Code in `src/lib/finance/`, one job per file:

- `money.ts` — currency validation, minor-unit digits, parsing and formatting.
  Amounts are `bigint` minor units; no floating point.
- `entries.ts` — pure builders that turn an expense, income, transfer, opening
  balance or revaluation into balanced posting lines.
- `ledger.ts` — validates and writes a transaction atomically; voids.
- `reports.ts` — balances, monthly spending, balance sheet.
- `auth.ts` — scrypt password check, sessions, rate limit.
- `db.ts` / `schema.ts` — one shared connection; versioned migrations applied on
  first use under an advisory lock.

## Data

```
fin_accounts      id, name, type (asset|liability|income|expense|equity),
                  currency (asset/liability only; others hold any currency),
                  scope (personal|business), system_key, archived_at
fin_transactions  id, kind (expense|income|transfer|opening|revalue),
                  occurred_on (date), description, created_at, voided_at
fin_postings      id, transaction_id, account_id, currency, amount_minor bigint
fin_sessions      token_hash, created_at, expires_at
fin_login_attempts key, attempted_at, succeeded
```

Sign convention: postings are debits when positive. Assets and expenses carry
positive balances; liabilities, income and equity carry negative raw balances
and are shown negated.

A deferred constraint trigger rejects any transaction whose postings do not sum
to zero per currency, and any posting whose currency differs from a
single-currency account. The application checks the same rules first so the
owner sees a message instead of a database error.

System equity accounts: **Opening balances**, **Currency exchange**,
**Revaluation**. Seeded categories: Food, Transport, Shopping, Bills, Health,
Family, Other (expense); Salary, Project fee, Other income (income).

Corrections are void and re-enter; postings are never edited in place.

## Entry rules

- Expense: debit category, credit the paying asset or liability.
- Income: debit the receiving asset, credit the income source.
- Transfer, same currency: debit destination, credit source.
- Transfer, two currencies: both amounts required; each leg balances through
  Currency exchange.
- Opening balance: account against Opening balances (owed amounts for
  liabilities).
- Revalue: the difference between the new and current value against
  Revaluation.
- The paying account defaults to the one used most recently.
- "Today" uses `FINANCE_TZ`, default `Asia/Bangkok`.

## Balance sheet

As-of date (default today) and scope (Personal, Business, All). One column per
currency held. What you own (assets), what you owe (liabilities), net worth.
In the **All** scope net worth is explained by opening balances, earnings to
date (income minus expenses), currency exchange and revaluation, and a check
line confirms own = owe + net worth. Scoped views show own, owe and net worth
only, because equity is not split by scope. Accounts link to their drill-down.
CSV download of the same figures. Client receivable and deposit lines appear
once sub-project 3 adds those accounts.

## Access

- `FINANCE_PASSWORD_HASH` (server setting, never in Git) holds
  `scrypt:N:r:p:salt:hash` (base64url). Generate it with
  `node scripts/finance-password-hash.mjs`. Without it, sign-in is refused with
  a setup message.
- Session cookie `kwg_fin`: random 32 bytes, `HttpOnly`, `Secure`,
  `SameSite=Lax`, path `/vault/finance`, 30 days. Only its SHA-256 is stored.
  Sign out removes the session; "Sign out everywhere" removes all.
- Rate limit: 5 failures per client in 15 minutes, and 30 failures overall in
  15 minutes, block further attempts until the window passes. Each attempt is
  recorded before the password is checked, so parallel guesses count against
  each other. A malformed or truncated hash refuses sign-in with a setup message.
- `SameSite=Lax` (not Strict) so a finance link opened from another site keeps
  the session; cross-site posts carry no cookie and are refused regardless.
- Finance responses send `Cache-Control: no-store`, `X-Robots-Tag: noindex`,
  `Referrer-Policy: same-origin`.

## Errors

Server-side validation with messages beside the field; typed values are kept.
Unbalanced or invalid transactions are refused and nothing is half-saved. If the
database is unreachable the finance pages return a 503 "Finance is unavailable
right now" page. Expired sessions redirect to sign-in and back to the page.

## Testing

Node's test runner (`yarn test:finance`): money parsing and formatting, entry
builders, and — against a real Postgres from `FINANCE_TEST_DATABASE_URL` —
ledger writes, the balance trigger, voiding, the balance sheet identity, and
sign-in rate limiting and sessions. An HTTP smoke run against the built server
covers redirects when signed out, sign-in, adding an expense and the balance
sheet.

## Removal

`firefly`, `firefly-cron`, `firefly-db` and their volumes leave `compose.yml`;
`PUBLIC_FIREFLY_URL` and the Firefly variables leave `.env.example`; the Vault
tile points to `/vault/finance`; `PRODUCT.md` is updated. Containers already
running on the VPS and the `firefly_db` volume are removed only after the owner
confirms.

## Out of scope

Receipt photos, recurring entries, budgets, bank CSV import, side-by-side date
comparison, income statements beyond monthly spending, and client accounting.
