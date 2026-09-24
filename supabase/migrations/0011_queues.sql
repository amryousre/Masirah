-- T022: the processing queues from contracts/queue-message.md, on Supabase Queues (pgmq).
-- Messages carry organisation identifiers and storage paths, so the queues belong to the server:
-- only the service role may send, read or delete. Anonymous and signed-in sessions have no way
-- in, neither through the pgmq_public functions nor through the queue tables.

create extension if not exists pgmq;

select pgmq.create('cv_processing');
-- No Phase 1 producer (weight adjustment is FR-025, Phase 2). Declared now so the worker's
-- routing does not change later.
select pgmq.create('cv_rescoring');

-- Supabase lint 0019: queue tables reachable from the Data API must have row level security.
-- There are no policies on purpose; the service role bypasses RLS and nothing else may read them.
alter table pgmq.q_cv_processing enable row level security;
alter table pgmq.a_cv_processing enable row level security;
alter table pgmq.q_cv_rescoring enable row level security;
alter table pgmq.a_cv_rescoring enable row level security;

revoke all on schema pgmq from anon, authenticated;
revoke all on all tables in schema pgmq from anon, authenticated;
grant usage on schema pgmq to service_role;
grant select, insert, update, delete on all tables in schema pgmq to service_role;
grant usage, select on all sequences in schema pgmq to service_role;

-- The Queues API that the dashboard's "Expose Queues via PostgREST" toggle would create, written
-- here so local and cloud stay identical. Do not use that toggle: it recreates these functions
-- with its own grants.
create schema pgmq_public;

create function pgmq_public.send(queue_name text, message jsonb, sleep_seconds integer default 0)
returns setof bigint
language sql
set search_path = ''
as $$
  select * from pgmq.send(queue_name := queue_name, msg := message, delay := sleep_seconds)
$$;

create function pgmq_public.send_batch(
  queue_name text, messages jsonb[], sleep_seconds integer default 0
)
returns setof bigint
language sql
set search_path = ''
as $$
  select * from pgmq.send_batch(queue_name := queue_name, msgs := messages, delay := sleep_seconds)
$$;

create function pgmq_public.read(queue_name text, sleep_seconds integer, n integer)
returns setof pgmq.message_record
language sql
set search_path = ''
as $$
  select * from pgmq.read(queue_name := queue_name, vt := sleep_seconds, qty := n)
$$;

create function pgmq_public.pop(queue_name text)
returns setof pgmq.message_record
language sql
set search_path = ''
as $$
  select * from pgmq.pop(queue_name := queue_name)
$$;

create function pgmq_public.archive(queue_name text, message_id bigint)
returns boolean
language sql
set search_path = ''
as $$
  select pgmq.archive(queue_name := queue_name, msg_id := message_id)
$$;

create function pgmq_public.delete(queue_name text, message_id bigint)
returns boolean
language sql
set search_path = ''
as $$
  select pgmq.delete(queue_name := queue_name, msg_id := message_id)
$$;

revoke all on schema pgmq_public from public, anon, authenticated;
revoke execute on all functions in schema pgmq_public from public, anon, authenticated;
grant usage on schema pgmq_public to service_role;
grant execute on all functions in schema pgmq_public to service_role;
