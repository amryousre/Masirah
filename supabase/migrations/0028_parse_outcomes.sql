-- T031 (NFR-14): the figures the worker's hourly parse failure alert reads, and the claim that
-- keeps it to one alert an hour however many workers run.
--
-- A file settles when the worker is done with it: extracted, sent for review or failed. settled_at
-- records that moment, set by trigger when the status first moves into one of those from a status
-- the worker was still working in. updated_at would not do: a purge or a person's review changes
-- it too, and an old failure would be counted again as a new one.

alter table public.cv_file add column settled_at timestamptz;

update public.cv_file
set settled_at = updated_at
where status in ('extracted', 'needs_review', 'failed');

create function private.set_settled_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.status in ('extracted', 'needs_review', 'failed')
     and old.status not in ('extracted', 'needs_review', 'failed') then
    new.settled_at := now();
  end if;
  return new;
end
$$;

create trigger set_settled_at before update of status on public.cv_file
  for each row execute function private.set_settled_at();

create index cv_file_settled_at_idx on public.cv_file (settled_at)
  where settled_at is not null;

-- Counts across every organisation and nothing else: no identifier, file name or reason, since
-- the alert goes to an operator's channel. A purged file is left out: its outcome is history.
-- Like the other worker functions it runs as its owner and only the worker may call it.
create function worker.parse_outcomes(window_seconds integer)
returns table (settled integer, failed integer, organisations integer)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if window_seconds < 60 then
    raise exception 'window_seconds % is under a minute', window_seconds
      using errcode = '22023';
  end if;
  return query
    select
      count(*)::integer,
      (count(*) filter (where f.status = 'failed'))::integer,
      (count(distinct f.organisation_id) filter (where f.status = 'failed'))::integer
    from public.cv_file f
    where f.settled_at >= now() - make_interval(secs => window_seconds)
      and f.purged_at is null;
end
$$;

revoke execute on function worker.parse_outcomes(integer)
  from public, anon, authenticated, service_role;
grant execute on function worker.parse_outcomes(integer) to masirah_worker;

-- One alert of a kind per quiet period across every worker: the first to claim it sends it, and
-- the rest, or a worker restarted within the period, stay quiet.
create table private.alert_claim (
  kind text primary key,
  claimed_at timestamptz not null
);
-- Not in an exposed schema, but lint 0013 wants row level security on every table regardless.
alter table private.alert_claim enable row level security;

create function worker.claim_alert(kind text, quiet_seconds integer)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  claimed boolean;
begin
  if quiet_seconds < 60 then
    raise exception 'quiet_seconds % is under a minute', quiet_seconds using errcode = '22023';
  end if;
  insert into private.alert_claim as a (kind, claimed_at) values (claim_alert.kind, now())
  on conflict on constraint alert_claim_pkey do update set claimed_at = excluded.claimed_at
    where a.claimed_at < now() - make_interval(secs => quiet_seconds)
  returning true into claimed;
  return coalesce(claimed, false);
end
$$;

revoke execute on function worker.claim_alert(text, integer)
  from public, anon, authenticated, service_role;
grant execute on function worker.claim_alert(text, integer) to masirah_worker;
