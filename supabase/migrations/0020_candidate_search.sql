-- T069: what candidate search compares, on each row of job_candidates. name_normalised is the
-- worker's folded name (pipeline domain/arabic.py), so a search for Mohamed finds Mohammed and
-- محمد. search_text gathers the extracted fields a recruiter searches by: location, skills,
-- employers and titles, institutions and qualifications, languages and certifications. The web
-- folds both sides the same way, so it searches without reading any profile.
--
-- create or replace keeps the existing columns in order and adds the new ones at the end.

create or replace function private.profile_search_text(profile jsonb)
returns text
language sql
immutable
set search_path = ''
as $$
  select concat_ws(' ',
    profile ->> 'location',
    (select string_agg(item, ' ')
       from jsonb_array_elements_text(
         case when jsonb_typeof(profile -> 'skills') = 'array' then profile -> 'skills' end
       ) as item),
    (select string_agg(concat_ws(' ', entry ->> 'employer', entry ->> 'title'), ' ')
       from jsonb_array_elements(
         case when jsonb_typeof(profile -> 'employment') = 'array' then profile -> 'employment' end
       ) as entry),
    (select string_agg(concat_ws(' ', entry ->> 'institution', entry ->> 'qualification'), ' ')
       from jsonb_array_elements(
         case when jsonb_typeof(profile -> 'education') = 'array' then profile -> 'education' end
       ) as entry),
    (select string_agg(entry ->> 'language', ' ')
       from jsonb_array_elements(
         case when jsonb_typeof(profile -> 'languages') = 'array' then profile -> 'languages' end
       ) as entry),
    (select string_agg(concat_ws(' ', entry ->> 'name', entry ->> 'issuer'), ' ')
       from jsonb_array_elements(
         case
           when jsonb_typeof(profile -> 'certifications') = 'array'
           then profile -> 'certifications'
         end
       ) as entry)
  )
$$;

revoke all on function private.profile_search_text(jsonb) from public, anon, authenticated;
grant execute on function private.profile_search_text(jsonb) to authenticated;

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
  coalesce(private.profile_search_text(p.profile), '') as search_text
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
