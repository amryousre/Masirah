-- T018: score. Immutable: rescoring inserts a new row, so every past ranking stays reproducible
-- (AI-02). Only the worker writes scores; members read them.

create type public.model_provider as enum ('anthropic', 'openai');

create table public.score (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  application_id uuid not null,
  total integer not null check (total between 0 and 100),
  components jsonb not null,
  justification text not null,
  summary text not null,
  model_id text not null,
  provider public.model_provider not null,
  prompt_version text not null,
  input_hash text not null check (input_hash ~ '^[0-9a-f]{64}$'),
  weights_hash text not null check (weights_hash ~ '^[0-9a-f]{64}$'),
  cost_egp numeric(10, 4) not null check (cost_egp >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (application_id, weights_hash),
  foreign key (organisation_id, application_id)
    references public.application (organisation_id, id)
);

alter table public.score enable row level security;
revoke all on public.score from anon, authenticated;
revoke update on public.score from service_role;
grant select on public.score to authenticated;

create policy "members read their organisation's scores" on public.score
  for select to authenticated
  using (organisation_id = (select private.current_organisation_id()));
