-- 006: demo accounts that connect instantly.
--
-- An evaluator signs up, types a demo username, and is connected at once, so they can see a real connection's
-- career in their Call Sheets without waiting for a second person. Nobody signs in as a demo account.
--
-- Safeguards:
--  * Only the service role can mark a profile as a demo. Users cannot, not even on their own profile: the column
--    is left out of every user grant.
--  * Demo accounts hold invented people and careers only.
--  * Everything else about connections is unchanged. Demo profiles are still found by exact username only.
alter table profiles add column is_demo boolean not null default false;

-- Replace the table-wide write grants with column grants that leave out is_demo.
revoke insert, update on profiles from authenticated;
grant insert (id, username, display_name, headline) on profiles to authenticated;
grant update (username, display_name, headline) on profiles to authenticated;

create or replace function request_connection(p_username text) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); other uuid; demo boolean; existing connections;
begin
  if me is null then raise exception 'sign in first'; end if;
  if not exists (select 1 from profiles where id = me) then raise exception 'create your profile first'; end if;
  select id, is_demo into other, demo from profiles where username = lower(btrim(p_username));
  if other is null or other = me then raise exception 'No user with that username.'; end if;
  select * into existing from connections
   where least(requester_id, addressee_id) = least(me, other) and greatest(requester_id, addressee_id) = greatest(me, other);
  if found then
    if existing.status = 'accepted' then return 'already_connected'; end if;
    if existing.requester_id = me then return 'already_requested'; end if;
    update connections set status = 'accepted', responded_at = now() where id = existing.id;
    return 'connected';
  end if;
  if demo then   -- demo accounts accept straight away
    insert into connections (requester_id, addressee_id, status, responded_at) values (me, other, 'accepted', now());
    return 'connected';
  end if;
  insert into connections (requester_id, addressee_id) values (me, other);
  return 'requested';
end $$;
