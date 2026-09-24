-- Every foreign key gets a covering index. Every policy filters by organisation, and deleting or
-- updating a referenced row scans the rows that reference it. These four close the gaps the
-- Supabase performance advisor found; the organisation-only keys on parsed_profile and score are
-- covered by the leading column of the composite indexes below.

create index application_job_idx on public.application (organisation_id, job_id);
create index application_decided_by_idx on public.application (organisation_id, decided_by);
create index parsed_profile_cv_file_idx on public.parsed_profile (organisation_id, cv_file_id);
create index score_application_idx on public.score (organisation_id, application_id);
