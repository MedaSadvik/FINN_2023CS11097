-- 004: build research for a company nobody planned for, on request.
--
-- Flow: a signed-in user asks for a ticker -> request_build() checks the daily budget and records the request ->
-- the website starts a GitHub Actions job -> the job (holding the model key and the Supabase secret key) builds the
-- research and writes it to companies_live -> the website shows it.
--
-- Privacy and cost rules, all enforced here, not in the website:
--  * Only signed-in users can ask. Nobody can write companies_live or build_requests directly.
--  * A per-user and a global daily cap stop anyone from burning the model quota.
--  * companies_live holds public filing data only. No network data ever goes in it.

create table build_limits (
  id               boolean primary key default true check (id),   -- exactly one row
  per_user_per_day int not null default 3 check (per_user_per_day >= 0),
  global_per_day   int not null default 6 check (global_per_day >= 0)
);
insert into build_limits default values;

create table companies_live (
  ticker   text primary key check (ticker ~ '^[A-Z0-9&-]{1,20}$'),
  name     text not null,
  provider text not null,
  data     jsonb not null,
  built_at timestamptz not null default now()
);

create table build_requests (
  id           bigserial primary key,
  ticker       text not null check (ticker ~ '^[A-Z0-9&-]{1,20}$'),
  requested_by uuid not null references auth.users(id) on delete cascade,
  -- not_started: the job never launched, so no model quota was used and it does not count against the budget
  status       text not null default 'queued'
               check (status in ('queued', 'building', 'done', 'no_data', 'limit', 'failed', 'not_started')),
  message      text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create index build_requests_ticker_idx on build_requests (ticker, created_at desc);
create index build_requests_user_idx   on build_requests (requested_by, created_at desc);

-- Ask for a company. Returns {state, message, request_id}. States:
--   queued, exists, in_progress, no_data, user_limit, global_limit, bad_ticker, sign_in
create function request_build(p_ticker text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare
  me uuid := auth.uid();
  t text := upper(btrim(coalesce(p_ticker, '')));
  lim build_limits%rowtype;
  existing build_requests%rowtype;
  used_me int; used_all int; new_id bigint;
begin
  if me is null then
    return jsonb_build_object('state', 'sign_in', 'message', 'Sign in to add a company.');
  end if;
  if t !~ '^[A-Z0-9&-]{1,20}$' then
    return jsonb_build_object('state', 'bad_ticker', 'message', 'Use the NSE symbol, like INFY or ZOMATO.');
  end if;
  if exists (select 1 from companies_live where ticker = t) then
    return jsonb_build_object('state', 'exists', 'message', 'Already built.');
  end if;

  select * into existing from build_requests
   where ticker = t and status in ('queued', 'building') and updated_at > now() - interval '30 minutes'
   order by id desc limit 1;
  if found then
    return jsonb_build_object('state', 'in_progress', 'message', 'Already being built.', 'request_id', existing.id);
  end if;

  -- a ticker with no transcripts stays that way for a day; do not let people retry it
  select * into existing from build_requests
   where ticker = t and status = 'no_data' and created_at > now() - interval '24 hours'
   order by id desc limit 1;
  if found then
    return jsonb_build_object('state', 'no_data', 'message', coalesce(existing.message, 'No earnings call transcripts found.'));
  end if;

  select * into lim from build_limits;
  select count(*) into used_me from build_requests
   where requested_by = me and created_at > now() - interval '24 hours' and status not in ('no_data', 'not_started');
  if used_me >= lim.per_user_per_day then
    return jsonb_build_object('state', 'user_limit',
      'message', format('You can add %s companies a day. Try again tomorrow.', lim.per_user_per_day));
  end if;
  select count(*) into used_all from build_requests
   where created_at > now() - interval '24 hours' and status not in ('no_data', 'not_started');
  if used_all >= lim.global_per_day then
    return jsonb_build_object('state', 'global_limit',
      'message', 'Daily limit reached for this demo. Try again later.');
  end if;

  insert into build_requests (ticker, requested_by) values (t, me) returning id into new_id;
  return jsonb_build_object('state', 'queued', 'message', 'Queued.', 'request_id', new_id);
end $$;

-- The website calls this when it could not start the job, so the request does not eat the budget.
create function mark_not_started(p_id bigint) returns void
language sql security definer set search_path = public as $$
  update build_requests set status = 'not_started', message = 'Could not start the build.', updated_at = now()
   where id = p_id and requested_by = auth.uid() and status = 'queued'
$$;

-- Where is the latest build for this ticker? Anyone can ask; only status text comes back.
create function build_status(p_ticker text) returns jsonb
language sql stable security definer set search_path = public as $$
  select coalesce(
    (select jsonb_build_object('state', status, 'message', message, 'updated_at', updated_at)
       from build_requests where ticker = upper(btrim(p_ticker)) order by id desc limit 1),
    jsonb_build_object('state', 'none'))
$$;

alter table companies_live enable row level security;
alter table build_requests enable row level security;
alter table build_limits   enable row level security;
create policy live_read on companies_live for select using (true);
create policy my_requests on build_requests for select using (requested_by = auth.uid());

-- Start from nothing. Writes happen only through the functions above, or the job using the secret key.
revoke all on companies_live, build_requests, build_limits from anon, authenticated;
grant select on companies_live to anon, authenticated;
grant select on build_requests to authenticated;
revoke all on sequence build_requests_id_seq from anon, authenticated;

revoke execute on function request_build, mark_not_started, build_status from public, anon, authenticated;
grant execute on function request_build, mark_not_started to authenticated;
grant execute on function build_status to anon, authenticated;
