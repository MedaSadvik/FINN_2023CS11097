-- 007: a built company can be updated when a newer earnings call is out.
--
-- A scheduled job (scripts/check_stale.py) reads the list of calls on screener.in for each built company and compares
-- it with the newest call the research was built from. No model is used. When a newer call exists it sets newer_call.
-- request_build then lets a signed-in user build that ticker again, under the same daily caps as a first build.
-- The build job replaces the row and clears newer_call. Everything is public filing data; nothing about the network.
--
--   built_call   newest call (e.g. 'Q1FY27') the stored research was built from
--   newer_call   a newer call that exists but is not in the research yet, or null
--   checked_at   when the daily check last looked

alter table companies_live add column built_call text, add column newer_call text, add column checked_at timestamptz;

create or replace function request_build(p_ticker text) returns jsonb
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
  -- Built already. It can be built again only when the daily check found a newer earnings call (newer_call is set).
  if exists (select 1 from companies_live where ticker = t and newer_call is null) then
    return jsonb_build_object('state', 'exists', 'message', 'Already up to date.');
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

revoke execute on function request_build from public, anon, authenticated;
grant execute on function request_build to authenticated;
