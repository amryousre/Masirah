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
    seeded = seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")
    # The seeded candidate is already scored, so their file has been read.
    cur.execute("update public.cv_file set status = 'extracted'")
    return seeded


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
    # The seeded candidate's file, from before cv_file.job_id, is ranked and counts as a sixth CV.
    assert figures(cur, alpha) == (6, 1, 2, 2)


def test_a_file_uploaded_without_a_job_counts_for_none(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    add_file(cur, alpha, "queued", job=False)
    # One CV: the seeded ranked candidate's. The file uploaded without a job adds nothing.
    assert figures(cur, alpha) == (1, 1, 0, 0)


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


def test_a_job_never_shows_fewer_cvs_than_it_has_ranked(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    """The seeded CV file predates cv_file.job_id: its scored application still counts as a CV."""
    alpha, _ = tenants
    cur.execute(
        "update public.cv_file set job_id = null where id = %s", (alpha.row_ids["cv_file"],)
    )
    cv_count, ranked, _, _ = figures(cur, alpha)
    assert (cv_count, ranked) == (1, 1)


def test_new_files_and_older_ranked_candidates_are_counted_together(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    """One file still waiting, linked to the job, and one ranked candidate whose older file is
    not: two CVs, not the larger of one and one."""
    alpha, _ = tenants
    cur.execute(
        "update public.cv_file set job_id = null where id = %s", (alpha.row_ids["cv_file"],)
    )
    add_file(cur, alpha, "queued")
    cv_count, ranked, processing, _ = figures(cur, alpha)
    assert (cv_count, ranked, processing) == (2, 1, 1)


def test_a_decision_on_an_application_counts_as_activity(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    # The updated_at triggers would stamp these rows with now(); this test needs them old.
    cur.execute("alter table public.job disable trigger set_updated_at")
    cur.execute(
        "update public.job set updated_at = now() - interval '3 days' where id = %s",
        (alpha.row_ids["job"],),
    )
    cur.execute("alter table public.job enable trigger set_updated_at")
    cur.execute(
        "update public.score set created_at = now() - interval '3 days' where application_id = %s",
        (alpha.row_ids["application"],),
    )
    cur.execute("alter table public.cv_file disable trigger set_updated_at")
    cur.execute("update public.cv_file set updated_at = now() - interval '3 days'")
    cur.execute("alter table public.cv_file enable trigger set_updated_at")
    cur.execute(
        "update public.application set updated_at = now() where id = %s",
        (alpha.row_ids["application"],),
    )
    act_as(cur, alpha.user_id)
    cur.execute(
        "select updated_at > now() - interval '1 minute' from public.job_overview where id = %s",
        (alpha.row_ids["job"],),
    )
    assert cur.fetchone() == (True,)
