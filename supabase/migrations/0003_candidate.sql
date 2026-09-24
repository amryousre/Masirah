-- T014: candidate. Every identity field is nullable: a CV with no contact details is valid,
-- and deletion on request (FR-076) clears them.

create table public.candidate (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  full_name text,
  email text,
  phone text,
  location text,
  name_normalised text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organisation_id, id)
);

create trigger set_updated_at before update on public.candidate
  for each row execute function private.set_updated_at();

alter table public.candidate enable row level security;
revoke all on public.candidate from anon, authenticated;
-- No delete for members. Erasure (FR-076) runs server-side through T100 and T101, which remove
-- the stored original first; a direct delete would leave the CV behind in storage.
grant select, insert, update on public.candidate to authenticated;

create policy "members manage their organisation's candidates" on public.candidate
  for all to authenticated
  using (organisation_id = (select private.current_organisation_id()))
  with check (organisation_id = (select private.current_organisation_id()));
