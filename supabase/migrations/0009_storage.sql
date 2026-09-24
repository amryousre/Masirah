-- T021: the private bucket for original CV files. No public URLs: access goes through row level
-- security on the path, whose second segment is the owning organisation.
-- Path shape: organisations/{organisation_id}/cv/{cv_file_id}/{filename}

insert into storage.buckets (id, name, public, allowed_mime_types)
values (
  'cv-originals',
  'cv-originals',
  false,
  array[
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'image/jpeg',
    'image/png'
  ]
);

create function private.is_own_cv_object(bucket text, object_name text)
returns boolean
language sql
stable
set search_path = ''
as $$
  select bucket = 'cv-originals'
    and (storage.foldername(object_name))[1] = 'organisations'
    and (storage.foldername(object_name))[2] = (select private.current_organisation_id())::text
$$;
grant execute on function private.is_own_cv_object(text, text) to authenticated;

create policy "members read their organisation's CV files" on storage.objects
  for select to authenticated
  using (private.is_own_cv_object(bucket_id, name));

create policy "members upload into their organisation's CV folder" on storage.objects
  for insert to authenticated
  with check (private.is_own_cv_object(bucket_id, name));

-- No update or delete policy: originals are retained unchanged (FR-012) until erasure (T100,
-- T101) removes them server-side, together with the rows that reference them.
