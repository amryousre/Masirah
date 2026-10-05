"""Decisions carry the person who made them (T090, FR-023, migration 0021).

A shortlist or a rejection is recorded only through public.record_decision, which takes the
member from the session and the time from the database: no request can name someone else as the
decider, or leave the decider out. A rejection needs a reason. Every decision, and every undoing
of one, writes an activity row, so the audit trail says who decided what and why.
"""

import psycopg
import pytest

from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def decide(
    cur: Cursor, tenant: Tenant, decision: str, reason: str | None = None
) -> tuple[object, ...]:
    act_as(cur, tenant.user_id)
    cur.execute(
        "select decision::text, decided_by_email, decided_at is not null"
        " from public.record_decision(%s, %s::public.application_decision, %s)",
        (tenant.row_ids["application"], decision, reason),
    )
    row = cur.fetchone()
    cur.execute("reset role")
    assert row is not None
    return row


def stored(cur: Cursor, tenant: Tenant) -> tuple[object, ...]:
    cur.execute(
        "select decision::text, decided_by, decided_at is not null from public.application"
        " where id = %s",
        (tenant.row_ids["application"],),
    )
    row = cur.fetchone()
    assert row is not None
    return row


def activity(cur: Cursor, tenant: Tenant) -> list[tuple[object, ...]]:
    cur.execute(
        "select action, actor_id, subject_id, metadata from public.activity"
        " where organisation_id = %s and subject_type = 'application' order by occurred_at, id",
        (tenant.organisation_id,),
    )
    return cur.fetchall()


def test_a_shortlist_records_the_member_who_made_it(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    assert decide(cur, alpha, "shortlisted") == ("shortlisted", "alpha@example.test", True)
    assert stored(cur, alpha) == ("shortlisted", alpha.user_id, True)


def test_a_rejection_records_its_reason_in_the_audit_trail(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    decide(cur, alpha, "rejected", "experience")
    [(action, actor, subject, metadata)] = activity(cur, alpha)
    assert (action, actor, subject) == (
        "application.rejected",
        alpha.user_id,
        alpha.row_ids["application"],
    )
    assert metadata == {"reason": "experience", "previous": "undecided"}


def test_a_rejection_without_a_reason_is_refused(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        decide(cur, alpha, "rejected")


def test_a_reason_outside_the_list_is_refused(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        decide(cur, alpha, "rejected", "too old")


def test_undoing_a_decision_clears_the_decider_and_is_recorded(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    decide(cur, alpha, "rejected", "skills")
    assert decide(cur, alpha, "undecided") == ("undecided", None, False)
    assert stored(cur, alpha) == ("undecided", None, False)
    actions = [(row[0], row[3]) for row in activity(cur, alpha)]
    assert actions == [
        ("application.rejected", {"reason": "skills", "previous": "undecided"}),
        ("application.undecided", {"previous": "rejected"}),
    ]


def test_another_organisations_application_is_not_found(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.NoDataFound):
        cur.execute(
            "select * from public.record_decision(%s, 'shortlisted', null)",
            (beta.row_ids["application"],),
        )


def test_a_visitor_who_has_not_signed_in_cannot_decide(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "select * from public.record_decision(%s, 'shortlisted', null)",
            (alpha.row_ids["application"],),
        )


def test_a_member_cannot_write_a_decision_directly(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    """Even naming themselves: the only way in is the function, so the time is the database's."""
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "update public.application set decision = 'shortlisted', decided_by = %s,"
            " decided_at = now() where id = %s",
            (alpha.user_id, alpha.row_ids["application"]),
        )


def test_a_member_cannot_add_an_application_already_decided(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into public.application (organisation_id, candidate_id, job_id, decision,"
            " decided_by, decided_at) values (%s, %s, %s, 'rejected', %s, now())",
            (
                alpha.organisation_id,
                alpha.row_ids["candidate"],
                alpha.row_ids["job"],
                alpha.user_id,
            ),
        )


def test_the_list_shows_when_a_decision_was_made(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    decide(cur, alpha, "shortlisted")
    act_as(cur, alpha.user_id)
    cur.execute(
        "select decided_at is not null from public.job_candidates where application_id = %s",
        (alpha.row_ids["application"],),
    )
    assert cur.fetchone() == (True,)
