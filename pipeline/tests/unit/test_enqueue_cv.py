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
