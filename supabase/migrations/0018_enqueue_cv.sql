-- T061: uploading a CV queues it for the worker. Signed-in members cannot send queue messages
-- (migration 0011), and the web application holds no secret key. Instead a member asks this
-- function to enqueue one of their organisation's files: it builds the message from the file's
-- row, so the message always describes the stored file, and the organisation is the session's,
-- never the caller's say-so (contracts/web-routes.md).

-- The cv_processing message for a file, built from its row (contracts/queue-message.md). Both the
-- upload path and the reconciliation below send exactly this.
create function private.cv_processing_message(file public.cv_file, locale text)
returns jsonb
language sql
stable
set search_path = ''
as $$
  select jsonb_build_object(
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
$$;
revoke execute on function private.cv_processing_message(public.cv_file, text) from public;

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
    msg := private.cv_processing_message(file, locale)
  );
  return message_id;
end
$$;

revoke execute on function public.enqueue_cv_processing(uuid, text) from public, anon;
grant execute on function public.enqueue_cv_processing(uuid, text) to authenticated;

-- A CV is a few hundred kilobytes; a scan of a long one a few megabytes. Ten is generous and
-- keeps a mistaken upload of a video or an archive out of the bucket.
update storage.buckets set file_size_limit = 10 * 1024 * 1024 where id = 'cv-originals';

-- Reconciliation. If queueing a file fails and recording that failure fails too, as during an
-- outage, the file stays queued with no message, and would wait for ever. The worker calls this
-- every few minutes: any file queued longer than the given age with no message waiting for it is
-- queued again, in its organisation's language. Like the queue functions, it runs as its owner and
-- only the worker may call it.
create function worker.requeue_stranded(older_than_seconds integer)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  stranded record;
  requeued integer := 0;
begin
  if older_than_seconds < 60 then
    raise exception 'older_than_seconds % is under a minute', older_than_seconds
      using errcode = '22023';
  end if;
  for stranded in
    select f as file, o.locale as locale
    from public.cv_file f
    join public.organisation o on o.id = f.organisation_id
    where f.status = 'queued'
      and f.updated_at < now() - make_interval(secs => older_than_seconds)
      and not exists (
        select 1 from pgmq.q_cv_processing q where q.message->>'cv_file_id' = f.id::text
      )
  loop
    perform pgmq.send(
      queue_name := 'cv_processing',
      msg := private.cv_processing_message(stranded.file, stranded.locale)
    );
    requeued := requeued + 1;
  end loop;
  return requeued;
end
$$;

revoke execute on function worker.requeue_stranded(integer)
  from public, anon, authenticated, service_role;
grant execute on function worker.requeue_stranded(integer) to masirah_worker;
