-- T061: uploading a CV queues it for the worker. Signed-in members cannot send queue messages
-- (migration 0011), and the web application holds no secret key. Instead a member asks this
-- function to enqueue one of their organisation's files: it builds the message from the file's
-- row, so the message always describes the stored file, and the organisation is the session's,
-- never the caller's say-so (contracts/web-routes.md).

create function public.enqueue_cv_processing(cv_file_id uuid, locale text)
returns bigint
language plpgsql
security definer
set search_path = ''
as $$
declare
  file public.cv_file;
  message_id bigint;
begin
  if locale is distinct from 'ar' and locale is distinct from 'en' then
    raise exception 'locale % is not supported', locale using errcode = '22023';
  end if;
  select * into file from public.cv_file f
  where f.id = enqueue_cv_processing.cv_file_id
    and f.organisation_id = (select private.current_organisation_id());
  if not found then
    raise exception 'no such CV file in your organisation' using errcode = 'P0002';
  end if;
  select * into message_id from pgmq.send(
    queue_name := 'cv_processing',
    msg := jsonb_build_object(
      'schema_version', 1,
      'job_type', 'cv_processing',
      'organisation_id', file.organisation_id,
      'cv_file_id', file.id,
      'job_id', file.job_id,
      'content_hash', file.content_hash,
      'storage_path', file.storage_path,
      'locale', locale,
      'enqueued_at', to_char(now() at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"')
    )
  );
  return message_id;
end
$$;

revoke execute on function public.enqueue_cv_processing(uuid, text) from public, anon;
grant execute on function public.enqueue_cv_processing(uuid, text) to authenticated;

-- A CV is a few hundred kilobytes; a scan of a long one a few megabytes. Ten is generous and
-- keeps a mistaken upload of a video or an archive out of the bucket.
update storage.buckets set file_size_limit = 10 * 1024 * 1024 where id = 'cv-originals';
