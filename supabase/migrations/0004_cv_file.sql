-- T015: cv_file. The original document, retained unchanged (FR-012). content_hash is the
-- AI-03 cache key: the same bytes are never paid for twice within an organisation.

create type public.cv_file_status as enum (
  'queued', 'extracting', 'extracted', 'needs_review', 'failed'
);

create table public.cv_file (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  candidate_id uuid,
  storage_path text not null,
  original_filename text not null,
  mime_type text not null,
  byte_size integer not null check (byte_size >= 0),
  content_hash text not null check (content_hash ~ '^[0-9a-f]{64}$'),
  status public.cv_file_status not null default 'queued',
  failure_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organisation_id, id),
  foreign key (organisation_id, candidate_id) references public.candidate (organisation_id, id),
  constraint storage_path_inside_tenant_folder
    check (storage_path like 'organisations/' || organisation_id || '/cv/' || id || '/%'),
  constraint failure_reason_only_when_failed
    check ((status = 'failed') = (failure_reason is not null))
);

create index cv_file_content_hash_idx on public.cv_file (organisation_id, content_hash);
create index cv_file_candidate_idx on public.cv_file (organisation_id, candidate_id);

create trigger set_updated_at before update on public.cv_file
  for each row execute function private.set_updated_at();

alter table public.cv_file enable row level security;
revoke all on public.cv_file from anon, authenticated;
grant select, insert, update, delete on public.cv_file to authenticated;

create policy "members manage their organisation's CV files" on public.cv_file
  for all to authenticated
  using (organisation_id = (select private.current_organisation_id()))
  with check (organisation_id = (select private.current_organisation_id()));
