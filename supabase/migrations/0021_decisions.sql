-- T090: a decision carries the person who made it (FR-023). Members no longer write applications
-- at all; a shortlist, a rejection or the undoing of either goes through record_decision, which
-- takes the member from the session and the time from the database, so no request can name
-- someone else as the decider or leave the decider out. A rejection needs one of the listed
-- reasons. Each decision writes an activity row with the reason and what it replaced.
--
-- Nothing in the web application wrote applications directly: the worker makes them (migration
-- 0014) and the e2e helpers use the service role.

revoke insert, update, delete on public.application from authenticated;

create function public.record_decision(
  target_application uuid,
  chosen public.application_decision,
  reason text default null
)
returns table (decision public.application_decision, decided_by_email text, decided_at timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor uuid := (select auth.uid());
  organisation uuid := (select private.current_organisation_id());
  previous public.application_decision;
begin
  if actor is null or organisation is null then
    raise exception 'only a member of an organisation can decide' using errcode = '42501';
  end if;
  if chosen = 'rejected'
     and (reason is null or reason not in ('experience', 'skills', 'location', 'other')) then
    raise exception 'a rejection needs one of the listed reasons' using errcode = '22023';
  end if;
  if chosen <> 'rejected' and reason is not null then
    raise exception 'only a rejection takes a reason' using errcode = '22023';
  end if;

  select a.decision into previous
  from public.application a
  where a.id = target_application and a.organisation_id = organisation
  for update;
  if not found then
    raise exception 'no such application' using errcode = 'P0002';
  end if;

  update public.application a
  set decision = chosen,
      decided_by = case when chosen = 'undecided' then null else actor end,
      decided_at = case when chosen = 'undecided' then null else now() end
  where a.id = target_application;

  insert into public.activity (organisation_id, actor_id, action, subject_type, subject_id, metadata)
  values (
    organisation,
    actor,
    'application.' || chosen::text,
    'application',
    target_application,
    jsonb_strip_nulls(jsonb_build_object('reason', reason, 'previous', previous::text))
  );

  return query
  select a.decision, u.email, a.decided_at
  from public.application a
  left join public.app_user u on u.organisation_id = a.organisation_id and u.id = a.decided_by
  where a.id = target_application;
end;
$$;

revoke all on function public.record_decision(uuid, public.application_decision, text)
  from public, anon;
grant execute on function public.record_decision(uuid, public.application_decision, text)
  to authenticated;

-- When the decision was made, for "Rejected · Nourhan · today 14:32". Added at the end, as create or
-- replace requires.
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
  a.decided_at
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
