-- T017: application. AI-07 is enforced here rather than only in the interface: a shortlist or
-- rejection with no human actor cannot be stored, and a member can only record themselves.

create type public.application_decision as enum ('undecided', 'shortlisted', 'rejected');

create table public.application (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  candidate_id uuid not null,
  job_id uuid not null,
  decision public.application_decision not null default 'undecided',
  decided_by uuid,
  decided_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organisation_id, id),
  unique (job_id, candidate_id),
  foreign key (organisation_id, candidate_id) references public.candidate (organisation_id, id),
  foreign key (organisation_id, job_id) references public.job (organisation_id, id),
  foreign key (organisation_id, decided_by) references public.app_user (organisation_id, id),
  constraint decision_has_human_actor check (
    (decision = 'undecided' and decided_by is null and decided_at is null)
    or (decision <> 'undecided' and decided_by is not null and decided_at is not null)
  )
);

create index application_candidate_idx on public.application (organisation_id, candidate_id);

create trigger set_updated_at before update on public.application
  for each row execute function private.set_updated_at();

alter table public.application enable row level security;
revoke all on public.application from anon, authenticated;
grant select, insert, update, delete on public.application to authenticated;

create policy "members manage their organisation's applications" on public.application
  for all to authenticated
  using (organisation_id = (select private.current_organisation_id()))
  with check (
    organisation_id = (select private.current_organisation_id())
    and (decided_by is null or decided_by = (select auth.uid()))
  );
