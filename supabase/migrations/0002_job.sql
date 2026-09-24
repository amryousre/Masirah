-- T013: job. Weights are percentages over the six FR-014 components and must total 100,
-- so every score stays comparable with every other.

create function private.weights_are_valid(weights jsonb)
returns boolean
language sql
immutable
set search_path = ''
as $$
  select case
    when jsonb_typeof(weights) is distinct from 'object' then false
    when (select array_agg(k.key order by k.key) from jsonb_object_keys(weights) as k (key))
      is distinct from array[
        'education', 'experience_relevance', 'language',
        'location', 'skills_match', 'tenure_stability'
      ] then false
    when exists (select 1 from jsonb_each(weights) as w where jsonb_typeof(w.value) <> 'number')
      then false
    else (
      select bool_and(w.value::numeric >= 0 and w.value::numeric = trunc(w.value::numeric))
        and sum(w.value::numeric) = 100
      from jsonb_each(weights) as w
    )
  end
$$;
grant execute on function private.weights_are_valid(jsonb) to authenticated, service_role;

create table public.job (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  title text not null check (btrim(title) <> ''),
  description text,
  required_skills text[] not null default '{}',
  preferred_skills text[] not null default '{}',
  minimum_experience_years integer check (minimum_experience_years >= 0),
  location text,
  language_requirement text,
  weights jsonb not null check (private.weights_are_valid(weights)),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organisation_id, id)
);

create trigger set_updated_at before update on public.job
  for each row execute function private.set_updated_at();

alter table public.job enable row level security;
revoke all on public.job from anon, authenticated;
grant select, insert, update, delete on public.job to authenticated;

create policy "members manage their organisation's jobs" on public.job
  for all to authenticated
  using (organisation_id = (select private.current_organisation_id()))
  with check (organisation_id = (select private.current_organisation_id()));
