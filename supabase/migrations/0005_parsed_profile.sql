-- T016: parsed_profile. Versioned so reprocessing never destroys earlier results. People
-- correct fields through field_overrides, never by editing profile (FR-010), and only the
-- worker creates versions.

create type public.extraction_source as enum (
  'native_text', 'vision_ocr', 'tesseract_ocr', 'manual'
);

create table public.parsed_profile (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  cv_file_id uuid not null,
  version integer not null check (version > 0),
  is_current boolean not null default false,
  extraction_source public.extraction_source not null,
  confidence numeric(4, 3) not null check (confidence between 0 and 1),
  profile jsonb not null,
  field_overrides jsonb not null default '{}',
  extracted_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (cv_file_id, version),
  foreign key (organisation_id, cv_file_id) references public.cv_file (organisation_id, id)
);

create unique index parsed_profile_one_current_idx on public.parsed_profile (cv_file_id)
  where is_current;

create trigger set_updated_at before update on public.parsed_profile
  for each row execute function private.set_updated_at();

alter table public.parsed_profile enable row level security;
revoke all on public.parsed_profile from anon, authenticated;
grant select on public.parsed_profile to authenticated;
grant update (field_overrides) on public.parsed_profile to authenticated;

create policy "members read their organisation's profiles" on public.parsed_profile
  for select to authenticated
  using (organisation_id = (select private.current_organisation_id()));

create policy "members correct their organisation's profiles" on public.parsed_profile
  for update to authenticated
  using (organisation_id = (select private.current_organisation_id()))
  with check (organisation_id = (select private.current_organisation_id()));
