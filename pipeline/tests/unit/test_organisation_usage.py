"""What a member sees of their organisation's month (T093, FR-026, migration 0026).

public.organisation_usage counts the month as the worker does: CVs read by a model since
midnight on the first in Cairo, and whether either limit, CVs or spend, has been reached. The
spend itself is the operator's cost, not the member's, so only whether it halted is shown. Files
waiting are the ones still queued, which is where the worker leaves them at a limit.
"""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import psycopg
import pytest

from masirah_pipeline.domain.budget import next_month_start
from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def usage(cur: Cursor, tenant: Tenant) -> tuple[int, int, bool, int, datetime]:
    act_as(cur, tenant.user_id)
    cur.execute(
        "select cvs, cv_limit, at_limit, waiting, renews_at from public.organisation_usage()"
    )
    row = cur.fetchone()
    cur.execute("reset role")
    assert row is not None
    return row[0], row[1], row[2], row[3], row[4]


def spend(cur: Cursor, tenant: Tenant, kind: str, cost: str) -> None:
    cur.execute(
        "insert into public.model_spend (organisation_id, cv_file_id, kind, cost_egp)"
        " values (%s, gen_random_uuid(), %s, %s)",
        (tenant.organisation_id, kind, Decimal(cost)),
    )


def test_a_member_sees_the_cvs_read_this_month_against_the_limit(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    spend(cur, alpha, "extraction", "0.4")
    spend(cur, alpha, "scoring", "1.2")
    spend(cur, beta, "extraction", "0.4")
    cvs, limit, at_limit, _, renews = usage(cur, alpha)
    # The seeded call and the one above: two CVs read, the other organisation's not counted.
    assert (cvs, limit, at_limit) == (2, 300, False)
    cur.execute("select now()")
    now = cur.fetchone()[0]  # type: ignore[index]
    assert renews == next_month_start(now)
    assert renews.astimezone(ZoneInfo("Africa/Cairo")).day == 1


def test_the_spend_ceiling_halts_while_cvs_are_left(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    cur.execute(
        "update public.organisation set monthly_spend_ceiling_egp = 1 where id = %s",
        (alpha.organisation_id,),
    )
    spend(cur, alpha, "scoring", "0.6")
    assert usage(cur, alpha)[2] is True


def test_the_cv_limit_halts_too(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    cur.execute(
        "update public.organisation set monthly_cv_limit = 1 where id = %s",
        (alpha.organisation_id,),
    )
    assert usage(cur, alpha)[:3] == (1, 1, True)


def test_waiting_files_are_the_ones_still_queued(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    cur.execute(
        "update public.cv_file set status = 'queued' where id = %s", (alpha.row_ids["cv_file"],)
    )
    assert usage(cur, alpha)[3] == 1


def test_spend_before_this_month_is_not_counted(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    cur.execute(
        "update public.model_spend set spent_at = now() - interval '40 days'"
        " where organisation_id = %s",
        (alpha.organisation_id,),
    )
    assert usage(cur, alpha)[0] == 0


def test_a_visitor_who_has_not_signed_in_cannot_ask(cur: Cursor) -> None:
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select count(*) from public.organisation_usage()")
