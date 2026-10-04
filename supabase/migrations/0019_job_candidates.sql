-- T063: a job's ranked candidates. One row per application with what the ranked list shows: the
-- candidate's name, the latest score and its justification, how far the extraction behind it can
-- be trusted, and the decision with who made it. security_invoker makes the caller's row level
-- security apply (lint 0010), so a member reads their own organisation's candidates only.
--
-- Phase 1 has one set of weights per job, so the latest score is the score; weight adjustment
-- (FR-025) will choose the score for the job's current weights instead.

create view public.job_candidates
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
  decider.email as decided_by_email
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
  select pp.confidence
  from public.cv_file f
  join public.parsed_profile pp on pp.cv_file_id = f.id and pp.is_current
  where f.organisation_id = a.organisation_id and f.candidate_id = a.candidate_id
  order by pp.extracted_at desc
  limit 1
) p on true
left join public.app_user decider
  on decider.organisation_id = a.organisation_id and decider.id = a.decided_by;

revoke all on public.job_candidates from anon, authenticated;
grant select on public.job_candidates to authenticated;
