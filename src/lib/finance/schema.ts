// Versioned finance migrations. Each entry runs once, in order, inside one
// transaction, and is recorded in fin_schema_migrations. Append only: never
// edit a migration that may already have run on the VPS.
export const MIGRATIONS: string[] = [
  /* 1 — ledger, sessions, seed accounts */ `
  create table fin_accounts (
    id serial primary key,
    name text not null check (length(name) between 1 and 80),
    type text not null check (type in ('asset','liability','income','expense','equity')),
    currency char(3) check (currency ~ '^[A-Z]{3}$'),
    scope text not null default 'personal' check (scope in ('personal','business')),
    system_key text unique,
    archived_at timestamptz,
    created_at timestamptz not null default now(),
    -- Balance accounts hold one currency; categories and equity hold any.
    check ((type in ('asset','liability')) = (currency is not null))
  );
  create unique index fin_accounts_name_live
    on fin_accounts (type, lower(name)) where archived_at is null;

  create table fin_transactions (
    id bigserial primary key,
    kind text not null check (kind in ('expense','income','transfer','opening','revalue')),
    occurred_on date not null,
    description text not null default '' check (length(description) <= 200),
    created_at timestamptz not null default now(),
    voided_at timestamptz
  );
  create index fin_transactions_date on fin_transactions (occurred_on);

  create table fin_postings (
    id bigserial primary key,
    transaction_id bigint not null references fin_transactions(id),
    account_id int not null references fin_accounts(id),
    currency char(3) not null,
    amount_minor bigint not null check (amount_minor <> 0)
  );
  create index fin_postings_tx on fin_postings (transaction_id);
  create index fin_postings_account on fin_postings (account_id);

  -- Second line of defence behind ledger.ts: checked at commit, so all lines
  -- of a transaction are inserted before the sums are compared.
  create function fin_check_balanced() returns trigger language plpgsql as $$
  declare
    tx bigint := coalesce(new.transaction_id, old.transaction_id);
    bad text;
  begin
    select currency into bad from fin_postings
      where transaction_id = tx group by currency having sum(amount_minor) <> 0 limit 1;
    if bad is not null then
      raise exception 'Transaction % does not balance in %', tx, bad;
    end if;
    if tg_op <> 'DELETE' and exists (
      select 1 from fin_accounts a where a.id = new.account_id
        and a.currency is not null and a.currency <> new.currency
    ) then
      raise exception 'Posting currency % does not match account %', new.currency, new.account_id;
    end if;
    return null;
  end $$;
  create constraint trigger fin_postings_balanced
    after insert or update or delete on fin_postings
    deferrable initially deferred
    for each row execute function fin_check_balanced();

  create table fin_sessions (
    token_hash bytea primary key,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null
  );

  create table fin_login_attempts (
    id bigserial primary key,
    client_key text not null,
    attempted_at timestamptz not null default now(),
    succeeded boolean not null
  );
  create index fin_login_attempts_at on fin_login_attempts (attempted_at);

  insert into fin_accounts (name, type, system_key) values
    ('Opening balances', 'equity', 'opening'),
    ('Currency exchange', 'equity', 'fx'),
    ('Revaluation', 'equity', 'revaluation');
  insert into fin_accounts (name, type) values
    ('Food','expense'), ('Transport','expense'), ('Shopping','expense'),
    ('Bills','expense'), ('Health','expense'), ('Family','expense'),
    ('Other','expense'),
    ('Salary','income'), ('Project fee','income'), ('Other income','income');
  `,
  /* 2 — client orders (docs/superpowers/specs/2026-10-16-vault-finance-clients-design.md) */ `
  alter table fin_transactions drop constraint fin_transactions_kind_check;
  alter table fin_transactions add constraint fin_transactions_kind_check check (kind in (
    'expense','income','transfer','opening','revalue',
    'client_payment','client_purchase','client_delivery','client_refund'));

  create table fin_settings (
    key text primary key,
    value text not null
  );
  insert into fin_settings (key, value) values
    ('fee_bp', '500'), ('deposit_bp', '5000'), ('invoice_note', '');

  create table fin_clients (
    id serial primary key,
    name text not null check (length(name) between 1 and 80),
    contact text not null default '' check (length(contact) <= 200),
    currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
    owes_account_id int not null references fin_accounts(id),
    deposits_account_id int not null references fin_accounts(id),
    created_at timestamptz not null default now()
  );
  create unique index fin_clients_name on fin_clients (lower(name));

  create table fin_orders (
    id serial primary key,
    client_id int not null references fin_clients(id),
    fee_bp int not null check (fee_bp between 0 and 10000),
    note text not null default '' check (length(note) <= 500),
    created_on date not null,
    created_at timestamptz not null default now(),
    cancelled_at timestamptz,
    purchase_tx bigint references fin_transactions(id),
    delivery_tx bigint references fin_transactions(id)
  );
  create index fin_orders_client on fin_orders (client_id);

  create table fin_order_rates (
    order_id int not null references fin_orders(id) on delete cascade,
    currency char(3) not null check (currency ~ '^[A-Z]{3}$'),
    charge_micro bigint not null check (charge_micro > 0),
    cost_micro bigint not null check (cost_micro > 0),
    primary key (order_id, currency)
  );

  create table fin_order_lines (
    id serial primary key,
    order_id int not null references fin_orders(id) on delete cascade,
    description text not null check (length(description) between 1 and 200),
    options text not null default '' check (length(options) <= 200),
    link text not null default '' check (length(link) <= 500),
    quantity int not null check (quantity between 1 and 10000),
    unit_cost bigint not null check (unit_cost > 0),
    currency char(3) not null check (currency ~ '^[A-Z]{3}$')
  );
  create index fin_order_lines_order on fin_order_lines (order_id);

  -- Payments and refunds. order_id is null for client-level refunds.
  create table fin_client_payments (
    id serial primary key,
    client_id int not null references fin_clients(id),
    order_id int references fin_orders(id),
    transaction_id bigint not null unique references fin_transactions(id),
    kind text not null check (kind in ('payment','refund')),
    after_delivery boolean not null default false,
    amount bigint not null check (amount > 0)
  );
  create index fin_client_payments_order on fin_client_payments (order_id);

  -- Owner account names stay unique; system accounts (one pair per client,
  -- goods per currency) are keyed by system_key and may not clash with them.
  drop index fin_accounts_name_live;
  create unique index fin_accounts_name_live
    on fin_accounts (type, lower(name)) where archived_at is null and system_key is null;

  insert into fin_accounts (name, type, scope, system_key) values
    ('Client sales', 'income', 'business', 'client_sales'),
    ('Cost of client goods', 'expense', 'business', 'client_cost');
  `,
];
