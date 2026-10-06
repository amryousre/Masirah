-- T097, T100, T101: personal data removed on request (FR-076) and once the organisation's retention
-- period passes (NFR-10). Both paths share one purge, run by the worker, which holds the Storage
-- key the web application does not: it removes the stored originals first, then calls
-- worker.purge_candidate, which clears the candidate's identity, empties the profile content and
-- the corrections, deletes the scores and their reasons, renames the file to nothing personal and
-- writes an activity row saying what went. As the approved settings design lists it, what stays is
-- that the data was deleted, when and at whose request, and the screening decisions with who made
-- them, without personal data. A purged file never feeds the content-hash cache again.
--
-- Retention follows the same design: data goes the chosen number of months after the candidate's
-- last activity, unless they are shortlisted somewhere; an organisation may choose never to delete
-- automatically (a null period); and shortening the period deletes nobody for seven days.

alter table public.candidate add column purged_at timestamptz;
alter table public.cv_file add column purged_at timestamptz;

alter table public.organisation alter column retention_months drop not null;
alter table public.organisation add column retention_changed_at timestamptz;

-- The period changes only through set_retention, which records who changed it.
revoke update (retention_months) on public.organisation from authenticated;

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

  -- Two members asking at once meet at the unique open request: the second returns the first.
  insert into public.deletion_request (organisation_id, candidate_id, requested_by)
  values (organisation, target_candidate, actor)
  on conflict (candidate_id) where completed_at is null do nothing
  returning requested_at into open_since;
  if open_since is null then
    select r.requested_at into open_since
    from public.deletion_request r
    where r.candidate_id = target_candidate and r.completed_at is null;
    return open_since;
  end if;

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
    cross join lateral (
      select greatest(
        c.updated_at,
        (select max(f.created_at) from public.cv_file f where f.candidate_id = c.id),
        (select max(a.updated_at) from public.application a where a.candidate_id = c.id)
      ) as last_active
    ) seen
    where c.purged_at is null
      and o.retention_months is not null
      and seen.last_active < now() - make_interval(months => o.retention_months)
      and (o.retention_changed_at is null or o.retention_changed_at < now() - interval '7 days')
      and not exists (
        select 1 from public.application a
        where a.candidate_id = c.id and a.decision = 'shortlisted'
      )
      and not exists (
        select 1 from public.deletion_request r
        where r.candidate_id = c.id and r.completed_at is null
      )
    order by seen.last_active
  )
  limit greatest(at_most, 0)
$$;

-- The stored originals of a candidate's files, for the worker to remove before it purges the rows.
-- The worker passes the ids back to purge_candidate, which stamps only those files: one linked in
-- between still has its object in storage.
create function worker.purge_paths(target_candidate uuid)
returns table (cv_file_id uuid, storage_path text)
language sql
stable
security definer
set search_path = ''
as $$
  select f.id, f.storage_path from public.cv_file f
  where f.candidate_id = target_candidate and f.purged_at is null
$$;

-- Clears the candidate's personal data, once the originals of removed_files are gone. Safe to run
-- again. A file linked to the candidate after the worker listed the originals still has its object
-- in storage, so it is never stamped here:
--   * on request, everything else is cleared and the request stays open, so the next sweep removes
--     that object and completes it;
--   * by retention, the late file means the candidate has just been active again, so only the
--     files whose originals went are cleared and the candidate keeps what they sent since.
create function worker.purge_candidate(target_candidate uuid, reason text, removed_files uuid[])
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  organisation uuid;
  files integer;
  late integer;
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

  select count(*) into late
  from public.cv_file f
  where f.candidate_id = target_candidate
    and f.purged_at is null
    and not (f.id = any(coalesce(removed_files, '{}')));

  update public.parsed_profile p
  set profile = '{}'::jsonb, field_overrides = '{}'::jsonb
  from public.cv_file f
  where p.cv_file_id = f.id and f.candidate_id = target_candidate
    and f.id = any(coalesce(removed_files, '{}'));

  update public.cv_file
  set original_filename = 'removed', purged_at = coalesce(purged_at, now())
  where candidate_id = target_candidate and id = any(coalesce(removed_files, '{}'));
  get diagnostics files = row_count;

  if late > 0 and reason = 'retention' then
    insert into public.activity
      (organisation_id, actor_id, action, subject_type, subject_id, metadata)
    values (
      organisation, null, 'candidate.purged', 'candidate', target_candidate,
      jsonb_build_object(
        'reason', reason, 'files', files, 'removed', jsonb_build_array('original', 'profile'),
        'kept', 'active again during the sweep'
      )
    );
    return;
  end if;

  update public.candidate
  set full_name = null, email = null, phone = null, location = null, name_normalised = null,
      purged_at = case when late = 0 then coalesce(purged_at, now()) end
  where id = target_candidate;

  update public.parsed_profile p
  set profile = '{}'::jsonb, field_overrides = '{}'::jsonb
  from public.cv_file f
  where p.cv_file_id = f.id and f.candidate_id = target_candidate;

  delete from public.score s
  using public.application a
  where s.application_id = a.id and a.candidate_id = target_candidate;

  if late = 0 then
    update public.deletion_request
    set completed_at = now()
    where candidate_id = target_candidate and completed_at is null;
  end if;

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
      'removed', jsonb_build_array('identity', 'profile', 'original', 'scores')
    )
  );
end;
$$;

revoke execute on function worker.due_for_purge(integer)
  from public, anon, authenticated, service_role;
revoke execute on function worker.purge_paths(uuid)
  from public, anon, authenticated, service_role;
revoke execute on function worker.purge_candidate(uuid, text, uuid[])
  from public, anon, authenticated, service_role;
grant execute on function worker.due_for_purge(integer) to masirah_worker;
grant execute on function worker.purge_paths(uuid) to masirah_worker;
grant execute on function worker.purge_candidate(uuid, text, uuid[]) to masirah_worker;

-- The organisation's retention period, set by a member (T102): 6, 12 or 24 months, or null for
-- never deleting automatically. The change is recorded under the member, and starts the seven days
-- in which a shorter period deletes nobody. Returns how many candidates the new period will remove
-- once those seven days pass, for the page to say so.
create function public.set_retention(months integer default null)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor uuid := (select auth.uid());
  own uuid := (select private.current_organisation_id());
  previous integer;
  affected integer;
begin
  if actor is null or own is null then
    raise exception 'only a member of an organisation can change this' using errcode = '42501';
  end if;
  if months is not null and months not in (6, 12, 24) then
    raise exception 'retention is 6, 12 or 24 months, or none' using errcode = '22023';
  end if;

  select o.retention_months into previous from public.organisation o where o.id = own;
  update public.organisation
  set retention_months = months, retention_changed_at = now()
  where id = own;

  insert into public.activity (organisation_id, actor_id, action, subject_type, subject_id, metadata)
  values (
    own, actor, 'organisation.retention_changed', 'organisation', own,
    jsonb_build_object('from', previous, 'to', months)
  );

  if months is null then
    return 0;
  end if;
  select count(*) into affected
  from public.candidate c
  where c.organisation_id = own
    and c.purged_at is null
    and greatest(
      c.updated_at,
      (select max(f.created_at) from public.cv_file f where f.candidate_id = c.id),
      (select max(a.updated_at) from public.application a where a.candidate_id = c.id)
    ) < now() + interval '7 days' - make_interval(months => months)
    and not exists (
      select 1 from public.application a
      where a.candidate_id = c.id and a.decision = 'shortlisted'
    );
  return affected;
end;
$$;

revoke all on function public.set_retention(integer) from public, anon;
grant execute on function public.set_retention(integer) to authenticated;

-- The ranked list shows a deleted candidate as such rather than as one still being scored.
create or replace view public.job_candidates
with (security_invoker = true)
as
select
  a.id as application_id,
  a.organisation_id,
  a.job_id,
  a.candidate_id,
  c.full_name,
  sc.total,
  sc.justification,
  sc.created_at as scored_at,
  p.confidence,
  a.decision,
  decider.email as decided_by_email,
  c.name_normalised,
  coalesce(private.profile_search_text(p.profile), '') as search_text,
  a.decided_at,
  c.purged_at
from public.application a
join public.candidate c
  on c.organisation_id = a.organisation_id and c.id = a.candidate_id
left join lateral (
  select s.total, s.justification, s.created_at
  from public.score s
  where s.application_id = a.id
  order by s.created_at desc
  limit 1
) sc on true
left join lateral (
  select pp.confidence, pp.profile
  from public.cv_file f
  join public.parsed_profile pp on pp.cv_file_id = f.id and pp.is_current
  where f.organisation_id = a.organisation_id and f.candidate_id = a.candidate_id
  order by pp.extracted_at desc
  limit 1
) p on true
left join public.app_user decider
  on decider.organisation_id = a.organisation_id and decider.id = a.decided_by;

-- A CV that never became a candidate (unreadable, or waiting for review) holds personal data too:
-- its stored file, its name and any profile read from it. Retention reaches it on its own, by the
-- same period and the same seven days' grace; the candidate purge covers every other file.
create function worker.files_due_for_purge(at_most integer)
returns table (organisation_id uuid, cv_file_id uuid, storage_path text)
language sql
stable
security definer
set search_path = ''
as $$
  select f.organisation_id, f.id, f.storage_path
  from public.cv_file f
  join public.organisation o on o.id = f.organisation_id
  where f.candidate_id is null
    and f.purged_at is null
    and o.retention_months is not null
    and greatest(f.created_at, f.updated_at) < now() - make_interval(months => o.retention_months)
    and (o.retention_changed_at is null or o.retention_changed_at < now() - interval '7 days')
  order by f.created_at
  limit greatest(at_most, 0)
$$;

-- Empties what was read from the file and names it nothing personal, once its original is gone.
create function worker.purge_file(target_file uuid)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  organisation uuid;
begin
  select f.organisation_id into organisation
  from public.cv_file f where f.id = target_file and f.candidate_id is null
  for update;
  if not found then
    raise exception 'no such file without a candidate' using errcode = 'P0002';
  end if;

  update public.parsed_profile
  set profile = '{}'::jsonb, field_overrides = '{}'::jsonb
  where cv_file_id = target_file;
  update public.cv_file
  set original_filename = 'removed', purged_at = coalesce(purged_at, now())
  where id = target_file;

  insert into public.activity (organisation_id, actor_id, action, subject_type, subject_id, metadata)
  values (
    organisation, null, 'cv_file.purged', 'cv_file', target_file,
    jsonb_build_object('reason', 'retention', 'removed', jsonb_build_array('original', 'profile'))
  );
end;
$$;

revoke execute on function worker.files_due_for_purge(integer)
  from public, anon, authenticated, service_role;
revoke execute on function worker.purge_file(uuid)
  from public, anon, authenticated, service_role;
grant execute on function worker.files_due_for_purge(integer) to masirah_worker;
grant execute on function worker.purge_file(uuid) to masirah_worker;
