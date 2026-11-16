-- 008: the Research list shows how many promises each company has. Count them in the database,
-- so the list does not download every company's full research just to count.
alter table companies_live
  add column promise_count int generated always as (
    case when jsonb_typeof(data -> 'promises') = 'array' then jsonb_array_length(data -> 'promises') else 0 end) stored;
