-- T097, T100, T101: personal data removed on request (FR-076) and once the organisation's retention
-- period passes (NFR-10). Both paths share one purge, run by the worker, which holds the Storage
-- key the web application does not: it removes the stored originals first, then calls
-- worker.purge_candidate, which clears the candidate's identity, empties the profile content and
-- the corrections, renames the file to nothing personal and writes an activity row saying what
-- went. Scores and the audit trail stay, so the record of what was decided survives the person's
-- data. A purged file never feeds the content-hash cache again (the worker store checks purged_at).

alter table public.candidate add column purged_at timestamptz;
alter table public.cv_file add column purged_at timestamptz;

-- A member's request, kept until the worker completes it.
create table public.deletion_request (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  candidate_id uuid not null,
  requested_by uuid not null,
  requested_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (organisation_id, candidate_id) references public.candidate (organisation_id, id)
);

create index deletion_request_candidate_idx on public.deletion_request (organisation_id, candidate_id);
create unique index deletion_request_one_open_idx on public.deletion_request (candidate_id)
  where completed_at is null;

create trigger set_updated_at before update on public.deletion_request
  for each row execute function private.set_updated_at();

alter table public.deletion_request enable row level security;
revoke all on public.deletion_request from anon, authenticated;
grant select on public.deletion_request to authenticated;

create policy "members read their organisation's deletion requests" on public.deletion_request
  for select to authenticated
  using (organisation_id = (select private.current_organisation_id()));

-- A member asks for one candidate's personal data to be removed. Asking again while a request is
-- open returns that request's time rather than queueing a second.
create function public.request_candidate_deletion(target_candidate uuid)
returns timestamptz
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor uuid := (select auth.uid());
  organisation uuid := (select private.current_organisation_id());
  open_since timestamptz;
begin
  if actor is null or organisation is null then
    raise exception 'only a member of an organisation can ask' using errcode = '42501';
  end if;
  perform 1 from public.candidate c
  where c.id = target_candidate and c.organisation_id = organisation;
  if not found then
    raise exception 'no such candidate' using errcode = 'P0002';
  end if;

  select r.requested_at into open_since
  from public.deletion_request r
  where r.candidate_id = target_candidate and r.completed_at is null;
  if found then
    return open_since;
  end if;

  insert into public.deletion_request (organisation_id, candidate_id, requested_by)
  values (organisation, target_candidate, actor)
  returning requested_at into open_since;

  insert into public.activity (organisation_id, actor_id, action, subject_type, subject_id)
  values (organisation, actor, 'candidate.deletion_requested', 'candidate', target_candidate);
  return open_since;
end;
$$;

revoke all on function public.request_candidate_deletion(uuid) from public, anon;
grant execute on function public.request_candidate_deletion(uuid) to authenticated;

-- What the worker has to purge: every open request, then every candidate first seen longer ago
-- than their organisation keeps personal data. A request comes first, so it is never kept waiting
-- behind a long retention backlog.
create function worker.due_for_purge(at_most integer)
returns table (organisation_id uuid, candidate_id uuid, reason text)
language sql
stable
security definer
set search_path = ''
as $$
  (
    select r.organisation_id, r.candidate_id, 'request'
    from public.deletion_request r
    where r.completed_at is null
    order by r.requested_at
  )
  union all
  (
    select c.organisation_id, c.id, 'retention'
    from public.candidate c
    join public.organisation o on o.id = c.organisation_id
    where c.purged_at is null
      and c.created_at < now() - make_interval(months => o.retention_months)
      and not exists (
        select 1 from public.deletion_request r
        where r.candidate_id = c.id and r.completed_at is null
      )
    order by c.created_at
  )
  limit greatest(at_most, 0)
$$;

-- The stored originals of a candidate's files, for the worker to remove before it purges the rows.
create function worker.purge_paths(target_candidate uuid)
returns table (storage_path text)
language sql
stable
security definer
set search_path = ''
as $$
  select f.storage_path from public.cv_file f
  where f.candidate_id = target_candidate and f.purged_at is null
$$;

-- Clears the candidate's personal data, once their originals are gone. Safe to run again.
create function worker.purge_candidate(target_candidate uuid, reason text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  organisation uuid;
  files integer;
begin
  if reason not in ('request', 'retention') then
    raise exception 'unknown purge reason %', reason using errcode = '22023';
  end if;
  select c.organisation_id into organisation
  from public.candidate c where c.id = target_candidate
  for update;
  if not found then
    raise exception 'no such candidate' using errcode = 'P0002';
  end if;

  update public.candidate
  set full_name = null, email = null, phone = null, location = null, name_normalised = null,
      purged_at = coalesce(purged_at, now())
  where id = target_candidate;

  update public.parsed_profile p
  set profile = '{}'::jsonb, field_overrides = '{}'::jsonb
  from public.cv_file f
  where p.cv_file_id = f.id and f.candidate_id = target_candidate;

  update public.cv_file
  set original_filename = 'removed', purged_at = coalesce(purged_at, now())
  where candidate_id = target_candidate;
  get diagnostics files = row_count;

  update public.deletion_request
  set completed_at = now()
  where candidate_id = target_candidate and completed_at is null;

  insert into public.activity (organisation_id, actor_id, action, subject_type, subject_id, metadata)
  values (
    organisation,
    null,
    'candidate.purged',
    'candidate',
    target_candidate,
    jsonb_build_object(
      'reason', reason,
      'files', files,
      'removed', jsonb_build_array('identity', 'profile', 'original')
    )
  );
end;
$$;

revoke execute on function worker.due_for_purge(integer)
  from public, anon, authenticated, service_role;
revoke execute on function worker.purge_paths(uuid)
  from public, anon, authenticated, service_role;
revoke execute on function worker.purge_candidate(uuid, text)
  from public, anon, authenticated, service_role;
grant execute on function worker.due_for_purge(integer) to masirah_worker;
grant execute on function worker.purge_paths(uuid) to masirah_worker;
grant execute on function worker.purge_candidate(uuid, text) to masirah_worker;
