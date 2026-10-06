-- T093: per-organisation processing limits and a hard monthly spend ceiling (AI-06, FR-026).
-- Every model call is recorded with what it cost as it is made, so an organisation's spend this
-- month is what it really cost; once it reaches its ceiling, or its monthly CV limit, the worker
-- puts its work back until the next month starts rather than continuing to accrue cost. These
-- are cost controls, not billing (spec: billing and quotas are Phase 3), so only the operator
-- sets them. The defaults are the pilot's: 300 CVs, and 750 EGP, which is 300 CVs at the 2.5 EGP
-- each that SC-010 allows.

alter table public.organisation
  add column monthly_cv_limit integer not null default 300
    check (monthly_cv_limit >= 0),
  add column monthly_spend_ceiling_egp numeric(10, 2) not null default 750
    check (monthly_spend_ceiling_egp >= 0);

-- One row per paid model call, usable or not. cv_file_id carries no foreign key, like
-- activity.actor_id: a file's removal must never rewrite what was spent on it.
create table public.model_spend (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  cv_file_id uuid not null,
  kind text not null check (kind in ('extraction', 'scoring', 'summary')),
  provider text,
  model text,
  cost_egp numeric(10, 4) not null check (cost_egp >= 0),
  spent_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index model_spend_month_idx on public.model_spend (organisation_id, spent_at);

alter table public.model_spend enable row level security;
revoke all on public.model_spend from anon, authenticated;
revoke update, delete, truncate on public.model_spend from service_role;

-- Members see what their organisation's CVs cost, for the usage shown to them.
grant select on public.model_spend to authenticated;
create policy "members read their organisation's spend" on public.model_spend
  for select to authenticated
  using (organisation_id = (select private.current_organisation_id()));

-- The worker adds a row per call and reads the month's total, for the organisation it declared.
grant select, insert (organisation_id, cv_file_id, kind, provider, model, cost_egp)
  on public.model_spend to masirah_worker;
create policy "the worker records and reads the declared organisation's spend"
  on public.model_spend
  for all to masirah_worker
  using (organisation_id = (select private.worker_organisation_id()))
  with check (organisation_id = (select private.worker_organisation_id()));

-- The worker reads the declared organisation's limits, and nothing else of it.
grant select (id, monthly_cv_limit, monthly_spend_ceiling_egp) on public.organisation
  to masirah_worker;
create policy "the worker reads the declared organisation's limits" on public.organisation
  for select to masirah_worker
  using (id = (select private.worker_organisation_id()));

-- Puts a message back to be read again after delay_seconds, as a new message: work that waits
-- for its organisation's limits to renew has used none of its attempts. Sent and deleted in one
-- transaction, so the file always has exactly one message and is never taken for stranded.
-- Returns the new message's id, or null when the message was already gone.
create function worker.defer(queue_name text, message_id bigint, delay_seconds integer)
returns bigint
language plpgsql
security definer
set search_path = ''
as $$
declare
  body jsonb;
  sent bigint;
begin
  perform worker.check_queue(queue_name);
  -- At most a little over a month: a deferral waits for the next month, never longer.
  if delay_seconds not between 0 and 3024000 then
    raise exception 'delay_seconds % is outside 0 to 35 days', delay_seconds
      using errcode = '22023';
  end if;
  execute format('select message from pgmq.%I where msg_id = $1', 'q_' || queue_name)
    into body
    using message_id;
  if body is null then
    return null;
  end if;
  select pgmq.send(queue_name, body, delay_seconds) into sent;
  perform pgmq.delete(queue_name, message_id);
  return sent;
end
$$;

revoke execute on function worker.defer(text, bigint, integer)
  from public, anon, authenticated, service_role;
grant execute on function worker.defer(text, bigint, integer) to masirah_worker;
