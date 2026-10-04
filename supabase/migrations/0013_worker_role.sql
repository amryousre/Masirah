-- T053: the worker's own database role (contracts/queue-message.md, worker obligation 3).
-- The worker reads, deletes and archives queue messages. It never sends one, so a compromised
-- worker cannot plant work for itself, and it is not the service role, which bypasses row level
-- security on every table. Its access to tenant tables arrives with the consume loop (T054).
--
-- The role cannot log in here. Where the worker is deployed, an operator runs
-- `alter role masirah_worker with login password '...'`, so no password ever sits in git.

create role masirah_worker nologin noinherit;
-- Lets the migration owner act as the role, as the tests do with `set local role`.
grant masirah_worker to postgres;

-- The role touches no queue table. pgmq's own functions run with the caller's rights and would
-- need the tables granted, which would let the role push a message's visibility out forever,
-- rewrite its read count, or forge archived messages. Instead it calls these three functions,
-- which run as their owner and do only what the worker needs, within bounds. The schema is not
-- exposed through the Data API: the worker connects to Postgres directly.
create schema worker;

create function worker.read(queue_name text, visibility_seconds integer, quantity integer)
returns setof pgmq.message_record
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform worker.check_queue(queue_name);
  -- Long enough for the slowest CV, short enough that a crashed worker's message returns.
  if visibility_seconds not between 0 and 3600 then
    raise exception 'visibility_seconds % is outside 0 to 3600', visibility_seconds
      using errcode = '22023';
  end if;
  if quantity not between 1 and 100 then
    raise exception 'quantity % is outside 1 to 100', quantity using errcode = '22023';
  end if;
  return query select * from pgmq.read(queue_name, visibility_seconds, quantity);
end
$$;

create function worker.delete(queue_name text, message_id bigint)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform worker.check_queue(queue_name);
  return pgmq.delete(queue_name, message_id);
end
$$;

create function worker.archive(queue_name text, message_id bigint)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  perform worker.check_queue(queue_name);
  return pgmq.archive(queue_name, message_id);
end
$$;

-- Only the contract's queues: the definer could otherwise reach any queue pgmq holds.
create function worker.check_queue(queue_name text)
returns void
language plpgsql
set search_path = ''
as $$
begin
  if queue_name is distinct from 'cv_processing' and queue_name is distinct from 'cv_rescoring'
  then
    raise exception 'queue % is not in the contract', queue_name using errcode = '22023';
  end if;
end
$$;

revoke all on schema worker from public, anon, authenticated, service_role;
revoke execute on all functions in schema worker from public, anon, authenticated, service_role;
grant usage on schema worker to masirah_worker;
grant execute on function worker.read(text, integer, integer) to masirah_worker;
grant execute on function worker.delete(text, bigint) to masirah_worker;
grant execute on function worker.archive(text, bigint) to masirah_worker;
