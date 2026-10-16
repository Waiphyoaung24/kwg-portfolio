# Vault Finance — client orders design

Date: 2026-10-16. Sub-project 3 of `2026-10-16-vault-finance-design.md`.
Owner-approved through brainstorming, section by section, plus a visual
preview of the order page and the client invoice.

## Goal

Accounting for the owner's purchasing-agent work: clients ask the owner to buy
items online; the owner quotes in the client's currency, takes a deposit, buys
in THB or USD, delivers, and collects the balance. Everything posts to the
existing double-entry ledger so the balance sheet stays complete.

## Decisions

| Topic | Decision |
| --- | --- |
| Currencies | Items are bought in THB, USD or any currency; each client is billed in one currency (default MMK). |
| Earnings | A visible service fee (percentage of the item total, default from settings) plus a margin in the charge rate. |
| Real cost | The owner enters an actual cost rate per purchase currency on each order. |
| Payment | Usually a deposit before buying and the balance on delivery; any payment pattern works. |
| Orders | Several lines, each with its own purchase currency; shipping and fees are lines too. |
| Client output | Invoice and statement pages to screenshot or save as PDF. No client portal. |
| Rounding | Billing amounts round half up to the billing currency's minor unit (whole kyat for MMK). |
| Print | Invoices and statements print on white: an owner-approved exception to DESIGN.md's dark-only rule, for printed and PDF output only. |

## Ledger mapping

Per client, created with the client and hidden from Entries and Accounts
(`system_key` `client:<id>:owes` / `client:<id>:deposits`), scope business:

- **Owes you** — asset in the billing currency.
- **Deposits held** — liability in the billing currency.

Shared system accounts: **Client sales** (income), **Cost of client goods**
(expense), and **Goods bought for clients · <currency>** (asset, created on
first use per purchase currency, `system_key` `goods:<currency>`).

| Step | Ledger entry |
| --- | --- |
| Payment before delivery | money account + / Deposits held + (owed to client) |
| Payment after delivery | money account + / Owes you − up to its balance, remainder to Deposits held |
| Bought | Goods bought · cur + / paying account − (per purchase currency, actual amounts) |
| Delivered | Owes you + total / Client sales; Cost of client goods + / Goods bought − (per currency); Deposits held − / Owes you − by min(deposits held, total) |
| Refund credit | Deposits held − / money account − |

New transaction kinds: `client_payment`, `client_purchase`, `client_delivery`,
`client_refund`. Entries cannot void these; only the order or client page can.

## Order state

Status is derived, never typed: cancelled → `cancelled`; delivery posted →
`closed` when paid in full, else `delivered`; purchase posted → `bought`; any
live payment → `deposit`; otherwise `quote`. Lines, rates and fee are editable
only in `quote`. Undo reverses the latest live step (payment, purchase or
delivery) by voiding its transaction. Cancel is allowed before purchase;
payments stay as client credit. Each step locks the order row
(`select … for update`) and re-checks state inside one transaction.

## Calculation

- Rates are stored as micro-units (6 decimals). Fee is stored in basis points.
- Line price = round(quantity × unit cost × charge rate) in the billing currency.
- Item total = Σ line prices; fee = round(item total × fee %); total = items + fee.
- Real cost = Σ per currency round(actual paid × cost rate); before purchase,
  line costs stand in for actual paid.
- Profit = total − real cost = fee + rate margin (item total − real cost).
- Order paid = deposit applied at delivery + payments linked to the order after
  delivery; balance due = total − paid (before delivery: total − payments).
- Profit is an estimate shown on the order and the monthly report only; the
  balance sheet keeps currencies separate.

## Pages

- `/vault/finance/clients`: clients with owed, held and open orders; add
  client; settings (default fee %, default deposit %, invoice note); monthly
  report of delivered orders with sales and estimated profit.
- `/vault/finance/clients/[id]`: orders, balances, new order, refund credit,
  statement link.
- `/vault/finance/clients/[id]/statement`: printable statement for a date
  range with running balance.
- `/vault/finance/orders/[id]`: status steps, lines, rates and fee, totals,
  owner-only cost and profit, actions (payment, bought, delivered, undo,
  cancel) and history.
- `/vault/finance/orders/[id]/invoice`: printable invoice without cost rates,
  shop costs, account names or profit.

Balance sheet: client accounts are grouped into "Money clients owe you" and
"Client deposits held"; goods accounts list per currency.

## Validation and errors

Lines need a description (≤ 200), quantity 1–10,000, unit cost > 0 and a
currency; links must start with `http://` or `https://` and are shown as text.
Each purchase currency needs both rates; fee 0–100 %. Bought needs a paying
account in each currency; payments need an account in the billing currency;
refunds cannot exceed credit held. A stale or double-submitted step reports the
order's current state instead of posting twice.

## Testing

Unit: line pricing across currencies, half-up rounding, fee, profit split,
actual-paid versus line cost, rate and percent parsing, status derivation.
Database: full lifecycle with the balance sheet balanced after every step,
overpayment credit, cancel and refund, undo of each step, concurrent delivery
posting once, Entries refusing to void client steps. HTTP smoke run and phone
and desktop screenshots, including the invoice print layout.

## Out of scope

Client portal, automatic product prices, returns after purchase, automatic
exchange rates, several billing currencies per client.
