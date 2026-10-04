-- T054: what the worker may do with tenant data (contracts/queue-message.md, worker obligation 3).
-- The worker handles one message at a time and declares that message's organisation_id for each
-- transaction, with set_config('masirah.organisation_id', ..., true). Every policy below admits
-- only rows of the declared organisation, so a worker query that forgets to filter, or that is
-- handed another tenant's identifier, still reaches nothing outside the message's tenant. With
-- nothing declared, it reaches nothing at all.
--
-- This guards against mistakes, not against a hostile worker: the role can declare any
-- organisation. That is the same trust the service role would carry, minus everything the grants
-- below leave out.

create function private.worker_organisation_id()
returns uuid
language sql
stable
set search_path = ''
as $$
  select nullif(current_setting('masirah.organisation_id', true), '')::uuid
$$;

grant usage on schema private to masirah_worker;
grant execute on function private.worker_organisation_id() to masirah_worker;

-- Reads: the job a CV is scored against, and the rows the worker itself maintains.
grant select on public.job, public.candidate, public.cv_file, public.parsed_profile,
  public.application, public.score to masirah_worker;

-- A CV's progress through extraction, and the person it turned out to describe.
grant update (status, failure_reason, candidate_id) on public.cv_file to masirah_worker;
grant insert (organisation_id, full_name, email, phone, location, name_normalised)
  on public.candidate to masirah_worker;
grant update (full_name, email, phone, location, name_normalised)
  on public.candidate to masirah_worker;

-- Profiles are versioned: the worker adds a version and moves is_current, never edits one, and
-- never touches field_overrides, which hold people's corrections (FR-010).
grant insert (organisation_id, cv_file_id, version, is_current, extraction_source, confidence,
  profile) on public.parsed_profile to masirah_worker;
grant update (is_current) on public.parsed_profile to masirah_worker;

-- An application links the candidate to the job the CV was uploaded against. The worker can
-- create one but cannot decide it: decisions belong to people (AI-07).
grant insert (organisation_id, candidate_id, job_id) on public.application to masirah_worker;

-- Scores are immutable (AI-02); the worker only adds them.
grant insert on public.score to masirah_worker;

create policy "the worker reads the declared organisation's jobs" on public.job
  for select to masirah_worker
  using (organisation_id = (select private.worker_organisation_id()));

create policy "the worker manages the declared organisation's candidates" on public.candidate
  for all to masirah_worker
  using (organisation_id = (select private.worker_organisation_id()))
  with check (organisation_id = (select private.worker_organisation_id()));

create policy "the worker manages the declared organisation's CV files" on public.cv_file
  for all to masirah_worker
  using (organisation_id = (select private.worker_organisation_id()))
  with check (organisation_id = (select private.worker_organisation_id()));

create policy "the worker manages the declared organisation's profiles" on public.parsed_profile
  for all to masirah_worker
  using (organisation_id = (select private.worker_organisation_id()))
  with check (organisation_id = (select private.worker_organisation_id()));

create policy "the worker manages the declared organisation's applications"
  on public.application
  for all to masirah_worker
  using (organisation_id = (select private.worker_organisation_id()))
  with check (organisation_id = (select private.worker_organisation_id()));

create policy "the worker manages the declared organisation's scores" on public.score
  for all to masirah_worker
  using (organisation_id = (select private.worker_organisation_id()))
  with check (organisation_id = (select private.worker_organisation_id()));
