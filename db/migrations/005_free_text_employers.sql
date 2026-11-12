-- 005: the Call Sheet can now see roles whose employer FINN does not track.
--
-- Before: a connection who wrote "Titan Company" on their profile was invisible to the Call Sheet, because only
-- roles linked to a known employer were exposed. A company built later could never find them.
-- Now: every role of an accepted connection is exposed with the employer name as written. The website matches
-- names when a page opens, so the order does not matter (profile first or company first).
--
-- Privacy is unchanged: this is the same view, security invoker, over the same row level security. It only
-- returns careers of you and your accepted connections.
create or replace view network_roles with (security_invoker = true) as
  select r.owner_id, r.person_id, r.employer_key, r.title, r.start_year, r.end_year, e.name as employer_name
  from roles r left join employers e on e.key = r.employer_key
  union all
  select p.owner_id, p.id, pr.employer_key, pr.title, pr.start_year, pr.end_year, pr.employer_name
  from people p join profile_roles pr on pr.profile_id = p.profile_id;
