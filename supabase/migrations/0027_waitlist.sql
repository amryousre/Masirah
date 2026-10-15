-- The landing page's waitlist: companies ask for an account, and the owner invites them, since
-- sign-ups are closed. A visitor gives a work email and the page's language, nothing else.
--
-- The list lives in the private schema, which the API does not expose, and has no tenant: it is
-- the operator's, read in the dashboard or with the service role. Visitors reach it only through
-- public.join_waitlist, which checks what it is given and keeps one row per address, so asking
-- twice is harmless and says nothing about whether an address was already there. Someone signed
-- in without an organisation may join too: they are the likeliest to want an account.
--
-- The function is public, so anyone with the publishable key can call it directly. It refuses
-- once the past hour holds 100 requests, which bounds what a flood can store on the Free plan's
-- database; a real hour of sign-ups is a fraction of that.

create table private.waitlist (
  email text primary key check (email = lower(email) and length(email) <= 254),
  locale text not null check (locale in ('ar', 'en')),
  created_at timestamptz not null default now()
);

alter table private.waitlist enable row level security;
revoke all on private.waitlist from public, anon, authenticated;
grant select, delete on private.waitlist to service_role;

create function public.join_waitlist(email text, locale text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  address text := lower(btrim(email));
begin
  if address is null or length(address) > 254
     or address !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception 'not an email address' using errcode = '22023';
  end if;
  if locale is null or locale not in ('ar', 'en') then
    raise exception 'locale % is not one the site has', locale using errcode = '22023';
  end if;
  if (select count(*) from private.waitlist w where w.created_at > now() - interval '1 hour')
     >= 100 then
    raise exception 'the waitlist is taking too many requests' using errcode = '53400';
  end if;
  insert into private.waitlist (email, locale)
  values (address, locale)
  on conflict on constraint waitlist_pkey do nothing;
end
$$;

revoke execute on function public.join_waitlist(text, text) from public;
grant execute on function public.join_waitlist(text, text) to anon, authenticated;
