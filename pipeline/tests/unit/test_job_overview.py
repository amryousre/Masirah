"""The job list's figures (T058, migration 0017).

job_overview gives each job what the list shows: CVs uploaded for it, how many are ranked, how
many are still being read, and how many need a person. It runs with the caller's row level
security, so a member sees only their own organisation's jobs.
"""

import uuid

import psycopg
import pytest

from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def add_file(cur: Cursor, tenant: Tenant, status: str, *, job: bool = True) -> None:
    file_id = uuid.uuid4()
    path = f"organisations/{tenant.organisation_id}/cv/{file_id}/cv.pdf"
    reason = "unreadable" if status == "failed" else None
    cur.execute(
        "insert into public.cv_file (id, organisation_id, job_id, storage_path,"
        " original_filename, mime_type, byte_size, content_hash, status, failure_reason)"
        " values (%s, %s, %s, %s, 'cv.pdf', 'application/pdf', 1, %s, %s, %s)",
        (
            file_id,
            tenant.organisation_id,
            tenant.row_ids["job"] if job else None,
            path,
            "e" * 64,
            status,
            reason,
        ),
    )


def figures(cur: Cursor, tenant: Tenant) -> tuple[int, ...]:
    act_as(cur, tenant.user_id)
    cur.execute(
        "select cv_count, ranked_count, processing_count, attention_count"
        " from public.job_overview where id = %s",
        (tenant.row_ids["job"],),
    )
    row = cur.fetchone()
    assert row is not None
    cur.execute("reset role")
    return tuple(row)


def test_a_job_counts_its_files_by_state(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    for status in ("queued", "extracting", "extracted", "needs_review", "failed"):
        add_file(cur, alpha, status)
    # The seeded application already carries a score, so one candidate is ranked.
    assert figures(cur, alpha) == (5, 1, 2, 2)


def test_a_file_uploaded_without_a_job_counts_for_none(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    add_file(cur, alpha, "queued", job=False)
    assert figures(cur, alpha) == (0, 1, 0, 0)


def test_a_member_sees_only_their_organisations_jobs(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    cur.execute("select organisation_id from public.job_overview")
    assert {row[0] for row in cur.fetchall()} == {alpha.organisation_id}
    cur.execute("select count(*) from public.job_overview where id = %s", (beta.row_ids["job"],))
    assert cur.fetchone() == (0,)


def test_a_visitor_who_has_not_signed_in_sees_nothing(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select * from public.job_overview")


def test_a_file_cannot_be_filed_under_another_organisations_job(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    file_id = uuid.uuid4()
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        cur.execute(
            "insert into public.cv_file (id, organisation_id, job_id, storage_path,"
            " original_filename, mime_type, byte_size, content_hash)"
            " values (%s, %s, %s, %s, 'cv.pdf', 'application/pdf', 1, %s)",
            (
                file_id,
                alpha.organisation_id,
                beta.row_ids["job"],
                f"organisations/{alpha.organisation_id}/cv/{file_id}/cv.pdf",
                "e" * 64,
            ),
        )
