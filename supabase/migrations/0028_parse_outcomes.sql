-- T031 (NFR-14): the figures the worker's hourly parse failure alert reads. A file has settled
-- when the worker is done with it: extracted, sent for review or failed. updated_at is when it
-- settled, near enough: after that a file changes only by a person's review or a purge.
--
-- Counts across every organisation and nothing else: no identifier, file name or reason, since
-- the alert goes to an operator's channel. Like the other worker functions it runs as its owner
-- and only the worker may call it.

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
    where f.status in ('extracted', 'needs_review', 'failed')
      and f.updated_at >= now() - make_interval(secs => window_seconds);
end
$$;

revoke execute on function worker.parse_outcomes(integer)
  from public, anon, authenticated, service_role;
grant execute on function worker.parse_outcomes(integer) to masirah_worker;
