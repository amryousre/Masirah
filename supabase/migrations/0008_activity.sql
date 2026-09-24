-- T019: activity. Insert-only for every API role, the service role included: that is what
-- makes it an audit trail rather than a log. actor_id carries no foreign key on purpose, so
-- removing a user can never rewrite or block the record of what they did.

create table public.activity (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.organisation (id),
  actor_id uuid,
  action text not null check (action ~ '^[a-z_]+[.][a-z_]+$'),
  subject_type text not null,
  subject_id uuid not null,
  metadata jsonb not null default '{}',
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index activity_timeline_idx on public.activity (organisation_id, occurred_at desc);

alter table public.activity enable row level security;
revoke all on public.activity from anon, authenticated;
revoke update, delete, truncate on public.activity from service_role;
grant select, insert on public.activity to authenticated;

create policy "members read their organisation's activity" on public.activity
  for select to authenticated
  using (organisation_id = (select private.current_organisation_id()));

create policy "members record their own actions" on public.activity
  for insert to authenticated
  with check (
    organisation_id = (select private.current_organisation_id())
    and actor_id = (select auth.uid())
  );
