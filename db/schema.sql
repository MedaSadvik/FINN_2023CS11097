-- FINN schema (Supabase Postgres 15+). Run in the Supabase SQL editor.
-- Three groups: market data (public), fundamentals (public), network (private, RLS).

-- =====================================================================
-- 1. MARKET DATA (public read)
-- =====================================================================
create table companies (
  ticker        text primary key,           -- NSE symbol, e.g. 'KAYNES'
  name          text not null,
  sector        text,
  in_portfolio  boolean not null default false,
  screener_slug text                         -- path on screener.in
);

create table prices_eod (
  ticker  text references companies(ticker),
  day     date not null,
  close   numeric not null,
  volume  bigint  not null,
  primary key (ticker, day)
);

create table filings (
  id           bigserial primary key,
  ticker       text not null references companies(ticker),
  exchange     text not null check (exchange in ('BSE','NSE')),
  exchange_id  text not null,                -- id on the exchange, for dedup
  announced_at timestamptz not null,
  category     text not null,                -- our own bucket (results, mgmt_change, ma, ...)
  subject      text not null,
  pdf_url      text,
  priority     smallint not null default 0,  -- 0 hide, 1 routine, 2 notable, 3 important
  summary      text,                         -- one line, LLM or rule-made
  extracted    jsonb,                        -- results numbers, people named, etc.
  unique (exchange, exchange_id)
);
create index on filings (ticker, announced_at desc);

-- =====================================================================
-- 2. FUNDAMENTALS (public read)
-- =====================================================================
create table documents (
  id          bigserial primary key,
  ticker      text not null references companies(ticker),
  kind        text not null check (kind in ('transcript','annual_report')),
  period      text not null,                 -- 'Q2FY26' or 'FY25'
  source_url  text not null,
  sha256      text,                          -- cache key: same file = no re-processing
  fetched_at  timestamptz default now(),
  unique (ticker, kind, period)
);

create table chunks (                        -- one row per PDF page (no vector DB in MVP)
  id          bigserial primary key,
  document_id bigint not null references documents(id) on delete cascade,
  page        int not null,
  text        text not null
);
create index on chunks (document_id, page);

create table quarters (                      -- headline numbers, INR crore
  ticker     text not null references companies(ticker),
  period     text not null,                  -- 'Q2FY27'
  revenue    numeric,
  ebitda     numeric,
  pbt        numeric,
  pat        numeric,
  filing_id  bigint references filings(id),
  primary key (ticker, period)
);

create table guidance_claims (               -- what management promised
  id           bigserial primary key,
  ticker       text not null references companies(ticker),
  document_id  bigint not null references documents(id),
  page         int not null,
  quote        text not null,                -- verbatim; code verifies it exists on the page
  metric       text not null,                -- revenue_growth, ebitda_margin, capex, ...
  target_text  text not null,                -- "20-25% YoY growth in FY27"
  made_in      text not null,                -- period of the call
  check_period text                          -- period we compare against
);

create table verdicts (                      -- promised vs delivered
  claim_id        bigint primary key references guidance_claims(id) on delete cascade,
  outcome         text not null check (outcome in ('delivered','partly','missed','unclear')),
  delivered_text  text not null,
  evidence_quote  text,
  model           text,                      -- which LLM, for audit
  created_at      timestamptz default now()
);

-- =====================================================================
-- 3. NETWORK (private to one investor; Row Level Security on)
-- =====================================================================
create table employers (                     -- shared lookup, not personal data
  key     text primary key,                  -- 'kaynes', 'micron'
  name    text not null,
  sector  text not null,
  ticker  text references companies(ticker)  -- set if listed in our universe
);

create table employer_relations (            -- "relation to this company"
  employer_key text references employers(key),
  ticker       text references companies(ticker),
  relation     text not null check (relation in ('competitor','supplier','customer')),
  primary key (employer_key, ticker)
);

create table people (
  id          bigserial primary key,
  owner_id    uuid not null,                 -- the investor; RLS key
  kind        text not null check (kind in ('contact','extended','filing_person')),
  full_name   text not null,
  headline    text,
  last_spoke  date,                          -- from investor's own notes; contacts only
  notes       text,
  synthetic   boolean not null default true  -- prototype data is fake, and says so
);

create table roles (
  id           bigserial primary key,
  owner_id     uuid not null,
  person_id    bigint not null references people(id) on delete cascade,
  employer_key text not null references employers(key),
  title        text not null,
  start_year   int  not null,
  end_year     int                           -- null = current
);

create table education (
  id          bigserial primary key,
  owner_id    uuid not null,
  person_id   bigint not null references people(id) on delete cascade,
  institution text not null,
  start_year  int not null,
  end_year    int not null
);

create table filing_people (                 -- a name in a filing, linked to the network
  id             bigserial primary key,
  owner_id       uuid not null,
  filing_id      bigint not null references filings(id),
  name_in_filing text not null,
  role_in_filing text,                       -- 'incoming CFO'
  person_id      bigint references people(id),
  match_evidence jsonb                       -- why we matched: employer, years
);

-- "Knows" = overlapped at the same employer or school in the same years.
-- Plain SQL, so every claim on a Call Sheet can be explained.
create view person_overlaps with (security_invoker = true) as
select a.owner_id, a.person_id as person_a, b.person_id as person_b,
       'employer'::text as via_kind, a.employer_key as via,
       greatest(a.start_year, b.start_year) as from_year,
       least(coalesce(a.end_year, extract(year from now())::int),
             coalesce(b.end_year, extract(year from now())::int)) as to_year
from roles a join roles b
  on a.owner_id = b.owner_id and a.employer_key = b.employer_key and a.person_id < b.person_id
where greatest(a.start_year, b.start_year) <=
      least(coalesce(a.end_year, extract(year from now())::int),
            coalesce(b.end_year, extract(year from now())::int))
union all
select a.owner_id, a.person_id, b.person_id, 'school', a.institution,
       greatest(a.start_year, b.start_year), least(a.end_year, b.end_year)
from education a join education b
  on a.owner_id = b.owner_id and a.institution = b.institution and a.person_id < b.person_id
where greatest(a.start_year, b.start_year) <= least(a.end_year, b.end_year);

-- =====================================================================
-- 4. ALERTS (private)
-- =====================================================================
create table alert_rules (
  id        bigserial primary key,
  owner_id  uuid not null,
  kind      text not null check (kind in ('volume_multiple','price_move','filing_category')),
  params    jsonb not null                   -- {"multiple": 2.0} / {"pct": 5} / {"categories": ["results"]}
);

create table alerts_fired (
  id         bigserial primary key,
  owner_id   uuid not null,
  rule_id    bigint references alert_rules(id) on delete cascade,
  ticker     text not null references companies(ticker),
  fired_at   timestamptz not null default now(),
  detail     jsonb not null
);

-- =====================================================================
-- 5. ROW LEVEL SECURITY: investor sees only own rows
-- =====================================================================
alter table people         enable row level security;
alter table roles          enable row level security;
alter table education      enable row level security;
alter table filing_people  enable row level security;
alter table alert_rules    enable row level security;
alter table alerts_fired   enable row level security;

create policy own_rows on people        for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy own_rows on roles         for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy own_rows on education     for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy own_rows on filing_people for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy own_rows on alert_rules   for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy own_rows on alerts_fired  for all using (owner_id = auth.uid()) with check (owner_id = auth.uid());
