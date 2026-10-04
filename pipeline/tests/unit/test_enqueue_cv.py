"""Enqueueing an uploaded CV for processing (T061, contracts/queue-message.md).

A signed-in member does not send queue messages themselves: they ask enqueue_cv_processing to
send one for a file of their own organisation, and the database builds the message from the
file's row. So the message always describes the stored file, and the worker's strict parser
accepts it.
"""

import uuid

import psycopg
import pytest

from masirah_pipeline.ports.queue_message import CvProcessingMessage, parse_queue_message
from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    cur.execute("delete from pgmq.q_cv_processing")
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def enqueue(cur: Cursor, file_id: uuid.UUID, locale: str = "ar") -> int:
    cur.execute("select public.enqueue_cv_processing(%s, %s)", (file_id, locale))
    row = cur.fetchone()
    assert row is not None
    message_id: int = row[0]
    return message_id


def queued(cur: Cursor, message_id: int) -> object:
    cur.execute("reset role")
    cur.execute("select message from pgmq.q_cv_processing where msg_id = %s", (message_id,))
    row = cur.fetchone()
    assert row is not None
    return row[0]


def test_a_member_enqueues_their_file_and_the_worker_accepts_the_message(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    cur.execute(
        "update public.cv_file set job_id = %s where id = %s",
        (alpha.row_ids["job"], alpha.row_ids["cv_file"]),
    )
    act_as(cur, alpha.user_id)
    message = parse_queue_message(queued(cur, enqueue(cur, alpha.row_ids["cv_file"], "en")))
    assert isinstance(message, CvProcessingMessage)
    assert (message.organisation_id, message.cv_file_id, message.job_id) == (
        alpha.organisation_id,
        alpha.row_ids["cv_file"],
        alpha.row_ids["job"],
    )
    assert (message.storage_path, message.content_hash, message.locale) == (
        alpha.storage_path,
        "a" * 64,
        "en",
    )


def test_a_file_uploaded_without_a_job_is_enqueued_without_one(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    message = parse_queue_message(queued(cur, enqueue(cur, alpha.row_ids["cv_file"])))
    assert isinstance(message, CvProcessingMessage)
    assert message.job_id is None


def test_another_organisations_file_cannot_be_enqueued(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.NoDataFound):
        enqueue(cur, beta.row_ids["cv_file"])


def test_a_locale_outside_the_contract_is_refused(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        enqueue(cur, alpha.row_ids["cv_file"], "fr")


def test_a_visitor_who_has_not_signed_in_cannot_enqueue(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        enqueue(cur, alpha.row_ids["cv_file"])


def test_a_member_still_cannot_send_queue_messages_directly(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select * from pgmq_public.send('cv_processing', '{}'::jsonb)")


def test_the_cv_bucket_holds_files_of_ten_megabytes_at_most(cur: Cursor) -> None:
    cur.execute("select file_size_limit from storage.buckets where id = 'cv-originals'")
    assert cur.fetchone() == (10 * 1024 * 1024,)


class TestStrandedFiles:
    """A file left queued with no message, as when queueing and recording the failure both failed
    during an outage, is queued again by the worker's reconciliation (SC-006)."""

    def strand(self, cur: Cursor, tenant: Tenant, minutes: int) -> None:
        cur.execute("alter table public.cv_file disable trigger set_updated_at")
        cur.execute(
            "update public.cv_file set status = 'queued', updated_at = now() - make_interval("
            "mins => %s) where id = %s",
            (minutes, tenant.row_ids["cv_file"]),
        )
        cur.execute("alter table public.cv_file enable trigger set_updated_at")

    def requeue(self, cur: Cursor) -> int:
        cur.execute("set local role masirah_worker")
        cur.execute("select worker.requeue_stranded(600)")
        row = cur.fetchone()
        cur.execute("reset role")
        assert row is not None
        count: int = row[0]
        return count

    def messages_for(self, cur: Cursor, tenant: Tenant) -> list[object]:
        cur.execute(
            "select message from pgmq.q_cv_processing where message->>'cv_file_id' = %s",
            (str(tenant.row_ids["cv_file"]),),
        )
        return [row[0] for row in cur.fetchall()]

    def test_a_stranded_file_is_queued_again_with_its_organisations_language(
        self, cur: Cursor, tenants: tuple[Tenant, Tenant]
    ) -> None:
        alpha, _ = tenants
        self.strand(cur, alpha, 30)
        assert self.requeue(cur) == 1
        [body] = self.messages_for(cur, alpha)
        message = parse_queue_message(body)
        assert isinstance(message, CvProcessingMessage)
        assert (message.cv_file_id, message.locale) == (alpha.row_ids["cv_file"], "ar")

    def test_a_file_queued_moments_ago_is_left_alone(
        self, cur: Cursor, tenants: tuple[Tenant, Tenant]
    ) -> None:
        alpha, _ = tenants
        self.strand(cur, alpha, 2)
        assert self.requeue(cur) == 0

    def test_a_file_whose_message_is_waiting_is_not_queued_twice(
        self, cur: Cursor, tenants: tuple[Tenant, Tenant]
    ) -> None:
        alpha, _ = tenants
        self.strand(cur, alpha, 30)
        act_as(cur, alpha.user_id)
        enqueue(cur, alpha.row_ids["cv_file"])
        cur.execute("reset role")
        assert self.requeue(cur) == 0
        assert len(self.messages_for(cur, alpha)) == 1

    @pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
    def test_only_the_worker_reconciles(self, cur: Cursor, role: str) -> None:
        cur.execute(f"set local role {role}")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            cur.execute("select worker.requeue_stranded(600)")
