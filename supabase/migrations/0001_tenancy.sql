-- T012: tenancy. Every other table hangs off organisation, and every policy asks one question:
-- which organisation does the signed-in user belong to?

create schema private;
grant usage on schema private to authenticated, service_role;

create function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create table public.organisation (
  id uuid primary key default gen_random_uuid(),
  name text not null check (btrim(name) <> ''),
  retention_months integer not null default 24 check (retention_months > 0),
  locale text not null check (locale in ('ar', 'en')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Named app_user rather than user, which is a reserved word in PostgreSQL.
create table public.app_user (
  id uuid primary key references auth.users (id) on delete cascade,
  organisation_id uuid not null references public.organisation (id),
  email text not null,
  locale text check (locale in ('ar', 'en')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organisation_id, id)
);

-- Security definer so the policy on app_user can call it without recursing into itself.
create function private.current_organisation_id()
returns uuid
language sql
stable
security definer
set search_path = ''
as $$
  select organisation_id from public.app_user where id = (select auth.uid())
$$;
revoke all on function private.current_organisation_id() from public, anon;
grant execute on function private.current_organisation_id() to authenticated, service_role;

create trigger set_updated_at before update on public.organisation
  for each row execute function private.set_updated_at();
create trigger set_updated_at before update on public.app_user
  for each row execute function private.set_updated_at();

alter table public.organisation enable row level security;
alter table public.app_user enable row level security;

revoke all on public.organisation, public.app_user from anon, authenticated;
grant select on public.organisation, public.app_user to authenticated;
grant update (name, retention_months, locale) on public.organisation to authenticated;
grant update (locale) on public.app_user to authenticated;

create policy "members read their organisation" on public.organisation
  for select to authenticated
  using (id = (select private.current_organisation_id()));

create policy "members update their organisation" on public.organisation
  for update to authenticated
  using (id = (select private.current_organisation_id()))
  with check (id = (select private.current_organisation_id()));

create policy "members read their organisation's users" on public.app_user
  for select to authenticated
  using (organisation_id = (select private.current_organisation_id()));

create policy "users update their own settings" on public.app_user
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));
