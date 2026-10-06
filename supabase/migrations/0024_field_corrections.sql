-- T074, T082: a person's correction of an extracted field (FR-010). A correction is kept in
-- parsed_profile.field_overrides beside the machine's value, never over it, with who made it and
-- when: { "<field>": { "value": <corrected>, "by": <user>, "at": <time> } }. A member corrects
-- only through public.correct_profile, which checks the correction's shape, records it on the
-- audit trail and keeps the candidate's details in step. A later extraction adds a new version of
-- the profile, which inherits the corrections, so a better extraction never undoes them.

-- Whether a corrected value has the shape the extraction gives that field (pipeline
-- domain/profile.py): text, a number, a list of text, or a list of entries of known parts.
create function private.profile_value_ok(field text, value jsonb)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select case
    when field in ('name', 'location') then jsonb_typeof(value) in ('string', 'null')
    when field = 'years_of_experience' then jsonb_typeof(value) in ('number', 'null')
    when field in ('emails', 'phones', 'skills') then
      jsonb_typeof(value) = 'array'
      and not exists (
        select 1 from jsonb_array_elements(value) item where jsonb_typeof(item) <> 'string'
      )
    when field in ('employment', 'education', 'languages', 'certifications') then
      jsonb_typeof(value) = 'array'
      and not exists (
        select 1
        from jsonb_array_elements(value) entry
        where case
          when jsonb_typeof(entry) <> 'object' then true
          else exists (
            select 1
            from jsonb_each(entry) part
            where jsonb_typeof(part.value) not in ('string', 'null')
              or part.key <> all (
                case field
                  when 'employment' then array['employer', 'title', 'start', 'end']
                  when 'education' then array['institution', 'qualification', 'start', 'end']
                  when 'languages' then array['language', 'level']
                  else array['name', 'issuer']
                end
              )
          )
        end
      )
    else false
  end
$$;

-- A new version of a file's profile starts with the corrections of the version before it.
create function private.carry_field_overrides()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.field_overrides = '{}'::jsonb then
    new.field_overrides := coalesce(
      (
        select p.field_overrides
        from public.parsed_profile p
        where p.cv_file_id = new.cv_file_id
        order by p.version desc
        limit 1
      ),
      '{}'::jsonb
    );
  end if;
  return new;
end;
$$;

create trigger carry_field_overrides
  before insert on public.parsed_profile
  for each row execute function private.carry_field_overrides();

-- Corrects fields of the current profile of one of the member's files. Each key of corrections is
-- a field and its corrected value; a value equal to the extracted one removes that correction,
-- and an unchanged correction keeps who first made it. The candidate's name, first email, first
-- phone and location follow the profile as corrected; a corrected or restored name comes with its
-- searchable form, folded by the caller as the worker folds names (web lib/domain/names.ts).
-- Returns the corrections now kept.
create function public.correct_profile(
  target_file uuid,
  corrections jsonb,
  corrected_name_normalised text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  actor uuid := (select auth.uid());
  own uuid := (select private.current_organisation_id());
  target record;
  field text;
  value jsonb;
  kept jsonb;
  changed text[] := '{}'::text[];
  effective jsonb;
begin
  if actor is null or own is null then
    raise exception 'only a member can correct a profile';
  end if;
  if jsonb_typeof(corrections) is distinct from 'object' then
    raise exception 'corrections must name each field corrected';
  end if;

  select p.id, p.profile, p.field_overrides, f.candidate_id
  into target
  from public.parsed_profile p
  join public.cv_file f on f.id = p.cv_file_id
  where p.cv_file_id = target_file
    and p.is_current
    and p.organisation_id = own
    and f.purged_at is null
  for update of p;
  if not found then
    raise exception 'no profile to correct for this file';
  end if;

  kept := target.field_overrides;
  for field, value in select c.key, c.value from jsonb_each(corrections) c loop
    if not private.profile_value_ok(field, value) then
      raise exception 'a correction of % has the wrong shape', field;
    end if;
    if value = coalesce(target.profile -> field, 'null'::jsonb) then
      if kept ? field then
        kept := kept - field;
        changed := changed || field;
      end if;
    elsif not (kept ? field and kept -> field -> 'value' = value) then
      kept := kept || jsonb_build_object(
        field, jsonb_build_object('value', value, 'by', actor, 'at', now())
      );
      changed := changed || field;
    end if;
  end loop;
  if cardinality(changed) = 0 then
    return kept;
  end if;
  if 'name' = any (changed) and corrected_name_normalised is null then
    raise exception 'a corrected name needs its searchable form';
  end if;

  update public.parsed_profile set field_overrides = kept where id = target.id;

  if target.candidate_id is not null then
    effective := target.profile || (
      select coalesce(jsonb_object_agg(k.key, k.value -> 'value'), '{}'::jsonb)
      from jsonb_each(kept) k
    );
    update public.candidate c
    set
      full_name = case when 'name' = any (changed) then effective ->> 'name' else c.full_name end,
      name_normalised = case
        when 'name' = any (changed) then corrected_name_normalised else c.name_normalised
      end,
      email = case when 'emails' = any (changed) then effective -> 'emails' ->> 0 else c.email end,
      phone = case when 'phones' = any (changed) then effective -> 'phones' ->> 0 else c.phone end,
      location = case
        when 'location' = any (changed) then effective ->> 'location' else c.location
      end
    where c.id = target.candidate_id and c.purged_at is null;
  end if;

  insert into public.activity (organisation_id, actor_id, action, subject_type, subject_id, metadata)
  values (
    own,
    actor,
    'candidate.corrected',
    case when target.candidate_id is null then 'cv_file' else 'candidate' end,
    coalesce(target.candidate_id, target_file),
    jsonb_build_object('cv_file_id', target_file, 'fields', to_jsonb(changed))
  );
  return kept;
end;
$$;

revoke execute on function public.correct_profile(uuid, jsonb, text) from public, anon;
grant execute on function public.correct_profile(uuid, jsonb, text) to authenticated;
revoke execute on function private.profile_value_ok(text, jsonb) from public, anon, authenticated;

-- Corrections go through correct_profile, which checks and records them.
revoke update (field_overrides) on public.parsed_profile from authenticated;
