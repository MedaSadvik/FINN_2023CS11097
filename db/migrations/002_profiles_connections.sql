-- Real users, profiles and connections.
-- Run AFTER db/schema.sql, in the Supabase SQL editor.
--
-- Privacy rules, in plain words:
--   * A profile has a username (unique), a display name and a headline. Career (jobs, schools) is separate.
--   * Career is visible to the owner and to ACCEPTED connections only. Never to anyone else.
--   * Strangers can look a person up only by EXACT username, and learn only the display name.
--   * A connection exists only if the other person accepted. Nobody can add someone one-sidedly.
--   * Your private notes (people.notes, people.last_spoke) are never shared. They stay in your own address book.

-- ---------------------------------------------------------------- tables
create table profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  username     text not null unique check (username ~ '^[a-z0-9_]{3,20}$'),
  display_name text not null check (char_length(display_name) between 1 and 60),
  headline     text check (char_length(headline) <= 120),
  updated_at   timestamptz not null default now()
);

create table profile_roles (
  id            bigserial primary key,
  profile_id    uuid not null references profiles(id) on delete cascade,
  employer_name text not null check (char_length(employer_name) between 1 and 80),
  employer_key  text references employers(key),      -- set when the employer is one FINN tracks
  title         text not null check (char_length(title) between 1 and 80),
  start_year    int  not null check (start_year between 1960 and 2100),
  end_year      int  check (end_year between 1960 and 2100),   -- null = current
  check (end_year is null or end_year >= start_year)
);

create table profile_education (
  id          bigserial primary key,
  profile_id  uuid not null references profiles(id) on delete cascade,
  institution text not null check (char_length(institution) between 1 and 80),
  start_year  int  not null check (start_year between 1960 and 2100),
  end_year    int  not null check (end_year between 1960 and 2100),
  check (end_year >= start_year)
);

create table connections (
  id           bigserial primary key,
  requester_id uuid not null references profiles(id) on delete cascade,
  addressee_id uuid not null references profiles(id) on delete cascade,
  status       text not null default 'pending' check (status in ('pending', 'accepted')),
  created_at   timestamptz not null default now(),
  responded_at timestamptz,
  check (requester_id <> addressee_id)
);
-- one row per pair of people, whichever way round the request went
create unique index connections_pair on connections (least(requester_id, addressee_id), greatest(requester_id, addressee_id));

-- a connection shows up in the investor's own address book, linked to the live profile
alter table people add column profile_id uuid references profiles(id) on delete cascade;
create unique index people_owner_profile on people (owner_id, profile_id) where profile_id is not null;

-- ---------------------------------------------------------------- helpers
-- security definer: reads connections regardless of the caller's row rules, so the rules cannot loop.
-- Only ever answers about the caller, so it cannot be used to probe whether two other people are connected.
create function connected_to_me(other uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select auth.uid() is not null and exists (select 1 from connections
         where status = 'accepted'
           and ((requester_id = auth.uid() and addressee_id = other) or (requester_id = other and addressee_id = auth.uid())))
$$;

-- Exact-username lookup. Returns the display name and nothing else.
create function find_user(p_username text) returns table (username text, display_name text)
language sql stable security definer set search_path = public as $$
  select p.username, p.display_name from profiles p
  where auth.uid() is not null and p.username = lower(btrim(p_username)) and p.id <> auth.uid()
$$;

-- Ask to connect. If they already asked you, this accepts their request instead.
create function request_connection(p_username text) returns text
language plpgsql security definer set search_path = public as $$
declare me uuid := auth.uid(); other uuid; existing connections;
begin
  if me is null then raise exception 'sign in first'; end if;
  if not exists (select 1 from profiles where id = me) then raise exception 'create your profile first'; end if;
  select id into other from profiles where username = lower(btrim(p_username));
  if other is null or other = me then raise exception 'No user with that username.'; end if;
  select * into existing from connections
   where least(requester_id, addressee_id) = least(me, other) and greatest(requester_id, addressee_id) = greatest(me, other);
  if found then
    if existing.status = 'accepted' then return 'already_connected'; end if;
    if existing.requester_id = me then return 'already_requested'; end if;
    update connections set status = 'accepted', responded_at = now() where id = existing.id;
    return 'connected';
  end if;
  insert into connections (requester_id, addressee_id) values (me, other);
  return 'requested';
end $$;

-- The person who was asked accepts or declines.
create function respond_connection(p_id bigint, p_accept boolean) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_accept then
    update connections set status = 'accepted', responded_at = now()
     where id = p_id and addressee_id = auth.uid() and status = 'pending';
  else
    delete from connections where id = p_id and addressee_id = auth.uid() and status = 'pending';
  end if;
  if not found then raise exception 'No pending request to answer.'; end if;
end $$;

-- When a connection is accepted, each side gets the other in their own address book (notes stay private).
create function link_people_on_accept() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.status = 'accepted' and (tg_op = 'INSERT' or old.status <> 'accepted') then
    insert into people (owner_id, kind, full_name, headline, synthetic, profile_id)
      select new.requester_id, 'contact', p.display_name, p.headline, false, p.id from profiles p where p.id = new.addressee_id
      on conflict do nothing;
    insert into people (owner_id, kind, full_name, headline, synthetic, profile_id)
      select new.addressee_id, 'contact', p.display_name, p.headline, false, p.id from profiles p where p.id = new.requester_id
      on conflict do nothing;
  end if;
  return new;
end $$;
create trigger connection_accepted after insert or update on connections
  for each row execute function link_people_on_accept();

-- Removing a connection removes the address-book link on both sides.
create function unlink_people_on_delete() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  delete from people where profile_id = old.addressee_id and owner_id = old.requester_id;
  delete from people where profile_id = old.requester_id and owner_id = old.addressee_id;
  return old;
end $$;
create trigger connection_removed after delete on connections
  for each row execute function unlink_people_on_delete();

-- Keep a linked contact's name and headline in step with the live profile.
create function sync_linked_people() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  update people set full_name = new.display_name, headline = new.headline where profile_id = new.id;
  new.updated_at := now();
  return new;
end $$;
create trigger profile_updated before update on profiles
  for each row execute function sync_linked_people();

-- ---------------------------------------------------------------- the network the Call Sheet reads
-- Your hand-entered or synthetic contacts, plus the live careers of your accepted connections.
create view network_roles with (security_invoker = true) as
  select r.owner_id, r.person_id, r.employer_key, r.title, r.start_year, r.end_year from roles r
  union all
  select p.owner_id, p.id, pr.employer_key, pr.title, pr.start_year, pr.end_year
  from people p join profile_roles pr on pr.profile_id = p.profile_id
  where pr.employer_key is not null;

create view network_education with (security_invoker = true) as
  select e.owner_id, e.person_id, e.institution, e.start_year, e.end_year from education e
  union all
  select p.owner_id, p.id, pe.institution, pe.start_year, pe.end_year
  from people p join profile_education pe on pe.profile_id = p.profile_id;

-- ---------------------------------------------------------------- row level security
alter table profiles          enable row level security;
alter table profile_roles     enable row level security;
alter table profile_education enable row level security;
alter table connections       enable row level security;

create policy profile_read on profiles for select using (
  id = auth.uid()
  or connected_to_me(id)
  or exists (select 1 from connections c where c.status = 'pending'
             and ((c.requester_id = auth.uid() and c.addressee_id = profiles.id)
               or (c.addressee_id = auth.uid() and c.requester_id = profiles.id))));
create policy profile_insert on profiles for insert with check (id = auth.uid());
create policy profile_update on profiles for update using (id = auth.uid()) with check (id = auth.uid());

create policy career_read   on profile_roles for select using (profile_id = auth.uid() or connected_to_me(profile_id));
create policy career_write  on profile_roles for all    using (profile_id = auth.uid()) with check (profile_id = auth.uid());
create policy school_read   on profile_education for select using (profile_id = auth.uid() or connected_to_me(profile_id));
create policy school_write  on profile_education for all    using (profile_id = auth.uid()) with check (profile_id = auth.uid());

-- connections: you see your own; changes go through the functions above (no insert or update policy on purpose)
create policy connection_read   on connections for select using (requester_id = auth.uid() or addressee_id = auth.uid());
create policy connection_remove on connections for delete using (requester_id = auth.uid() or addressee_id = auth.uid());

-- ---------------------------------------------------------------- grants
-- Supabase grants new tables to every role by default; start from nothing and grant only what is needed.
revoke all on profiles, profile_roles, profile_education, connections from anon, authenticated;
grant select, insert, update on profiles to authenticated;
grant select, insert, update, delete on profile_roles, profile_education to authenticated;
grant select, delete on connections to authenticated;
revoke all on network_roles, network_education from anon, authenticated;
grant select on network_roles, network_education to authenticated;
grant usage on sequence profile_roles_id_seq, profile_education_id_seq to authenticated;
revoke execute on function connected_to_me, find_user, request_connection, respond_connection from public, anon;
grant execute on function connected_to_me, find_user, request_connection, respond_connection to authenticated;
