-- T030: the worker's heartbeat, and the figures /api/health reports. A stopped worker is silent:
-- messages pile up and nothing fails. The heartbeat and the age of the oldest waiting message are
-- the cheapest way to notice.

create table private.worker_heartbeat (
  worker text primary key,
  seen_at timestamptz not null default now()
);
-- Not in an exposed schema, but lint 0013 wants row level security on every table regardless.
alter table private.worker_heartbeat enable row level security;

-- The worker records that it is alive. Like the queue functions, this runs as its owner, so the
-- worker role needs no grant on the table.
create function worker.beat(worker_name text)
returns void
language sql
security definer
set search_path = ''
as $$
  insert into private.worker_heartbeat (worker, seen_at) values (worker_name, now())
  on conflict (worker) do update set seen_at = excluded.seen_at
$$;
revoke execute on function worker.beat(text) from public, anon, authenticated, service_role;
grant execute on function worker.beat(text) to masirah_worker;

-- Three aggregate figures and nothing else: no identifier, file name or content of any
-- organisation. /api/health calls this without a session, so a monitor needs no credentials.
-- The rescoring queue has no producer in Phase 1, so only cv_processing is counted.
create function public.service_health()
returns table (
  queue_depth integer,
  oldest_message_seconds double precision,
  heartbeat_age_seconds double precision
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    (select count(*)::integer from pgmq.q_cv_processing),
    (select extract(epoch from now() - min(enqueued_at)) from pgmq.q_cv_processing),
    (select extract(epoch from now() - max(seen_at)) from private.worker_heartbeat)
$$;
revoke execute on function public.service_health() from public;
grant execute on function public.service_health() to anon, authenticated, service_role;
