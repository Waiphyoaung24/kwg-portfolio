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
];
