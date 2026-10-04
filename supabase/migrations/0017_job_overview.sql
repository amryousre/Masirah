-- T058: the job list. A CV is uploaded against a job (T061), but until extraction creates its
-- application nothing linked the two, so a job could not show the files it is still processing.
-- cv_file.job_id records the job a file was uploaded for; null for a CV uploaded without one.

alter table public.cv_file
  add column job_id uuid,
  add constraint cv_file_job_in_same_organisation
    foreign key (organisation_id, job_id) references public.job (organisation_id, id);

create index cv_file_job_idx on public.cv_file (organisation_id, job_id);

-- One row per job with what the list shows: how many CVs, how many ranked, how many still being
-- read, and how many need a person's decision. security_invoker makes the caller's row level
-- security apply, so a member sees their own organisation's jobs and nothing else (lint 0010).
create view public.job_overview
with (security_invoker = true)
as
select
  j.id,
  j.organisation_id,
  j.title,
  j.location,
  j.minimum_experience_years,
  coalesce(f.cv_count, 0) as cv_count,
  coalesce(s.ranked_count, 0) as ranked_count,
  coalesce(f.processing_count, 0) as processing_count,
  coalesce(f.attention_count, 0) as attention_count,
  greatest(j.updated_at, f.last_change, s.last_change) as updated_at
from public.job j
left join lateral (
  select
    count(*)::integer as cv_count,
    (count(*) filter (where cv.status in ('queued', 'extracting')))::integer as processing_count,
    (count(*) filter (where cv.status in ('needs_review', 'failed')))::integer as attention_count,
    max(cv.updated_at) as last_change
  from public.cv_file cv
  where cv.organisation_id = j.organisation_id and cv.job_id = j.id
) f on true
left join lateral (
  select
    (count(distinct a.id))::integer as ranked_count,
    max(sc.created_at) as last_change
  from public.application a
  join public.score sc on sc.application_id = a.id
  where a.organisation_id = j.organisation_id and a.job_id = j.id
) s on true;

revoke all on public.job_overview from anon, authenticated;
grant select on public.job_overview to authenticated;
