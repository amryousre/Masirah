-- T093: what a member sees of their organisation's month (FR-026). The month is counted as the
-- worker counts it (pipeline domain/budget.py): from midnight on the first in Cairo, CVs read by
-- a model, and whether either limit has been reached. The spend itself is the operator's cost,
-- not the member's, so only whether it halted processing is shown. Files waiting are those still
-- queued, which is where the worker leaves them at a limit. Runs with the member's own rights, so
-- row level security keeps it to their organisation, and a visitor gets nothing.

create function public.organisation_usage()
returns table (
  cvs integer,
  cv_limit integer,
  at_limit boolean,
  waiting integer,
  renews_at timestamptz
)
language sql
stable
security invoker
set search_path = ''
as $$
  with month as (
    select
      date_trunc('month', now() at time zone 'Africa/Cairo') at time zone 'Africa/Cairo'
        as since,
      (date_trunc('month', now() at time zone 'Africa/Cairo') + interval '1 month')
        at time zone 'Africa/Cairo' as renews
  ),
  own as (
    select o.id, o.monthly_cv_limit, o.monthly_spend_ceiling_egp
    from public.organisation o
    where o.id = (select private.current_organisation_id())
  ),
  spent as (
    select
      count(distinct s.cv_file_id) filter (where s.kind = 'extraction')::integer as cvs,
      coalesce(sum(s.cost_egp), 0) as egp
    from public.model_spend s, own, month
    where s.organisation_id = own.id and s.spent_at >= month.since
  )
  select
    spent.cvs,
    own.monthly_cv_limit,
    spent.egp >= own.monthly_spend_ceiling_egp or spent.cvs >= own.monthly_cv_limit,
    (
      select count(*)::integer from public.cv_file f
      where f.organisation_id = own.id and f.status = 'queued' and f.purged_at is null
    ),
    month.renews
  from own, spent, month
$$;

revoke execute on function public.organisation_usage() from public, anon;
grant execute on function public.organisation_usage() to authenticated;
