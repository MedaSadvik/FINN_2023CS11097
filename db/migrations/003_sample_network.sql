-- "Load sample contacts": gives a new account a believable (synthetic, labelled) address book to try FINN with.
-- Runs as the caller (security invoker), so row level security applies: it can only ever write the caller's own rows.
-- Input is the JSON in data/network/synthetic_network.json: {"people": [{id, kind, full_name, headline, last_spoke, roles[], education[]}]}.

grant select, insert, update, delete on people, roles, education to authenticated;
grant usage on sequence people_id_seq, roles_id_seq, education_id_seq to authenticated;

create function load_sample_network(p jsonb) returns int
language plpgsql security invoker as $$
declare me uuid := auth.uid(); person jsonb; new_id bigint; n int := 0;
begin
  if me is null then raise exception 'sign in first'; end if;
  -- replace an earlier sample load, never touch real connections (those have a profile_id)
  delete from people where owner_id = me and synthetic and profile_id is null;
  for person in select * from jsonb_array_elements(p -> 'people') loop
    insert into people (owner_id, kind, full_name, headline, last_spoke, synthetic)
    values (me, person ->> 'kind', person ->> 'full_name', person ->> 'headline',
            nullif(person ->> 'last_spoke', '')::date, true)
    returning id into new_id;
    insert into roles (owner_id, person_id, employer_key, title, start_year, end_year)
      select me, new_id, r ->> 'employer_key', r ->> 'title', (r ->> 'start_year')::int, (r ->> 'end_year')::int
      from jsonb_array_elements(person -> 'roles') r;
    insert into education (owner_id, person_id, institution, start_year, end_year)
      select me, new_id, e ->> 'institution', (e ->> 'start_year')::int, (e ->> 'end_year')::int
      from jsonb_array_elements(person -> 'education') e;
    n := n + 1;
  end loop;
  return n;
end $$;
revoke execute on function load_sample_network from public, anon;
grant execute on function load_sample_network to authenticated;

-- Remove the sample contacts again.
create function clear_sample_network() returns void
language sql security invoker as $$
  delete from people where owner_id = auth.uid() and synthetic and profile_id is null
$$;
revoke execute on function clear_sample_network from public, anon;
grant execute on function clear_sample_network to authenticated;
