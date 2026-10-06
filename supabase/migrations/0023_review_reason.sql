-- T080: why a CV waits in the review queue. A file with nothing to read, a CV in a language
-- version 1.0 does not read, and a profile too little of which is in the text call for different
-- actions from the recruiter, so the queue shows them apart (FR-011). For an unsupported language
-- the language found is kept, so the queue can name it.

create type public.review_reason as enum ('no_text', 'unsupported_language', 'low_confidence');

alter table public.cv_file
  add column review_reason public.review_reason,
  add column review_language text;

-- A file in review before this migration has no recorded reason. One with a current profile was
-- extracted and doubted; one without may have had no text or an unsupported language, which can
-- no longer be told apart, so it keeps no reason and the queue says only that it needs a look.
update public.cv_file f
set review_reason = 'low_confidence'
where f.status = 'needs_review'
  and exists (
    select 1 from public.parsed_profile p where p.cv_file_id = f.id and p.is_current
  );

alter table public.cv_file
  add constraint review_reason_only_in_review
    check (review_reason is null or status = 'needs_review'),
  add constraint review_language_only_for_unsupported
    check ((review_language is not null) = coalesce(review_reason = 'unsupported_language', false));

grant update (review_reason, review_language) on public.cv_file to masirah_worker;
