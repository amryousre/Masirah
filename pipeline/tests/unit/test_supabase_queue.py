"""The Supabase queue adapter and the worker's own database role (T053, contracts/queue-message.md).

The worker reads, deletes and archives messages as masirah_worker, a role granted exactly that,
through three functions and no queue table: it cannot send a message, hide one for good or forge
an archived one, and it does not need the service role, which bypasses row level security
everywhere.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

from masirah_pipeline.adapters.supabase_queue import SupabaseQueue, UnknownQueueError
from masirah_pipeline.ports.job_queue import ReceivedMessage
from masirah_pipeline.ports.queue_message import CV_PROCESSING, CV_RESCORING
from tests.database import Cursor

pytestmark = pytest.mark.database

WORKER = "masirah_worker"
BODY: dict[str, Any] = {"schema_version": 1, "job_type": CV_PROCESSING, "probe": "t053"}


def send(cur: Cursor, queue: str, body: dict[str, Any]) -> int:
    """Send as the web application does, through the service role, then return to the owner."""
    cur.execute("set local role service_role")
    cur.execute("select * from pgmq_public.send(%s, %s)", (queue, Jsonb(body)))
    row = cur.fetchone()
    assert row is not None
    cur.execute("reset role")
    message_id: int = row[0]
    return message_id


@pytest.fixture
def queue(cur: Cursor) -> SupabaseQueue:
    """The adapter on a connection acting as the worker role, inside the rolled-back test."""
    cur.execute("delete from pgmq.q_cv_processing")
    cur.execute("delete from pgmq.q_cv_rescoring")
    return SupabaseQueue(cur.connection)


def as_worker(cur: Cursor) -> None:
    cur.execute(f"set local role {WORKER}")


def test_reads_a_waiting_message(cur: Cursor, queue: SupabaseQueue) -> None:
    message_id = send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    [message] = queue.read(CV_PROCESSING, visibility_seconds=30, quantity=5)
    assert isinstance(message, ReceivedMessage)
    assert (message.message_id, message.read_count, message.body) == (message_id, 1, BODY)
    assert message.enqueued_at.tzinfo is not None


def test_an_empty_queue_reads_nothing(cur: Cursor, queue: SupabaseQueue) -> None:
    as_worker(cur)
    assert queue.read(CV_PROCESSING, visibility_seconds=30, quantity=5) == []


def test_reads_no_more_than_asked(cur: Cursor, queue: SupabaseQueue) -> None:
    for n in range(3):
        send(cur, CV_PROCESSING, BODY | {"n": n})
    as_worker(cur)
    read = queue.read(CV_PROCESSING, visibility_seconds=30, quantity=2)
    assert [message.body["n"] for message in read] == [0, 1]


def test_a_read_message_is_hidden_until_its_visibility_timeout(
    cur: Cursor, queue: SupabaseQueue
) -> None:
    send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    assert len(queue.read(CV_PROCESSING, visibility_seconds=30, quantity=5)) == 1
    assert queue.read(CV_PROCESSING, visibility_seconds=30, quantity=5) == []


def test_an_undeleted_message_returns_with_its_read_count(
    cur: Cursor, queue: SupabaseQueue
) -> None:
    """The retry mechanism, and the count the worker's retry limit is measured against."""
    send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    counts = [
        message.read_count
        for _ in range(2)
        for message in queue.read(CV_PROCESSING, visibility_seconds=0, quantity=5)
    ]
    assert counts == [1, 2]


def test_a_deleted_message_does_not_return(cur: Cursor, queue: SupabaseQueue) -> None:
    message_id = send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    queue.read(CV_PROCESSING, visibility_seconds=0, quantity=5)
    assert queue.delete(CV_PROCESSING, message_id) is True
    assert queue.read(CV_PROCESSING, visibility_seconds=0, quantity=5) == []


def test_deleting_a_message_that_is_gone_says_so(cur: Cursor, queue: SupabaseQueue) -> None:
    message_id = send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    assert queue.delete(CV_PROCESSING, message_id) is True
    assert queue.delete(CV_PROCESSING, message_id) is False


def test_an_archived_message_leaves_the_queue_and_is_kept(
    cur: Cursor, queue: SupabaseQueue
) -> None:
    """A terminal failure is archived, not deleted, so the message itself is never lost."""
    message_id = send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    assert queue.archive(CV_PROCESSING, message_id) is True
    assert queue.read(CV_PROCESSING, visibility_seconds=0, quantity=5) == []
    cur.execute("reset role")
    cur.execute("select message from pgmq.a_cv_processing where msg_id = %s", (message_id,))
    assert cur.fetchone() == (BODY,)


def test_the_queues_are_kept_apart(cur: Cursor, queue: SupabaseQueue) -> None:
    send(cur, CV_RESCORING, BODY | {"job_type": CV_RESCORING})
    as_worker(cur)
    assert queue.read(CV_PROCESSING, visibility_seconds=0, quantity=5) == []
    [message] = queue.read(CV_RESCORING, visibility_seconds=0, quantity=5)
    assert message.body["job_type"] == CV_RESCORING


def test_a_queue_outside_the_contract_is_refused(queue: SupabaseQueue) -> None:
    with pytest.raises(UnknownQueueError):
        queue.read("cv_everything", visibility_seconds=0, quantity=1)


@pytest.mark.parametrize(
    "statement",
    [
        "select * from pgmq_public.send('cv_processing', '{}'::jsonb)",
        "select * from pgmq.send('cv_processing', '{}'::jsonb)",
        "select * from pgmq_public.read('cv_processing', 30, 1)",
        "select * from pgmq.q_cv_processing",
        "insert into pgmq.q_cv_processing (message) values ('{}'::jsonb)",
        "update pgmq.q_cv_processing set message = '{}'::jsonb",
        "update pgmq.q_cv_processing set vt = 'infinity'",
        "update pgmq.q_cv_processing set read_ct = 0",
        "insert into pgmq.a_cv_processing (msg_id, message) values (1, '{}'::jsonb)",
        "select message from pgmq.a_cv_processing",
    ],
    ids=[
        "send",
        "pgmq-send",
        "pgmq-read",
        "read-table",
        "insert",
        "rewrite",
        "hide-forever",
        "reset-read-count",
        "forge-archive",
        "read-archive",
    ],
)
def test_the_worker_touches_no_queue_table(cur: Cursor, statement: str) -> None:
    """Everything goes through worker.read, worker.delete and worker.archive, so a compromised
    worker cannot plant work, hide a message for good, reset its retries or forge an archive."""
    as_worker(cur)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(statement)


@pytest.mark.parametrize(
    ("visibility_seconds", "quantity"),
    [(-1, 1), (3601, 1), (30, 0), (30, 101)],
    ids=["negative-timeout", "timeout-past-an-hour", "no-messages", "too-many-messages"],
)
def test_a_read_outside_its_bounds_is_refused(
    cur: Cursor, queue: SupabaseQueue, visibility_seconds: int, quantity: int
) -> None:
    as_worker(cur)
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        queue.read(CV_PROCESSING, visibility_seconds=visibility_seconds, quantity=quantity)


def test_the_database_refuses_a_queue_outside_the_contract(cur: Cursor) -> None:
    """The functions run as their owner, so they check the queue themselves."""
    cur.execute("select pgmq.create('not_in_the_contract')")
    as_worker(cur)
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        cur.execute("select * from worker.read('not_in_the_contract', 30, 1)")


@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
def test_only_the_worker_calls_the_worker_functions(cur: Cursor, role: str) -> None:
    cur.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select * from worker.read('cv_processing', 30, 1)")


def test_the_migration_gives_the_worker_role_no_login(cur: Cursor) -> None:
    """Login is granted where the worker is deployed, with a password that never sits in git."""
    cur.execute("select rolcanlogin, rolbypassrls from pg_roles where rolname = %s", (WORKER,))
    assert cur.fetchone() == (False, False)


def test_a_deferred_message_waits_until_then_and_comes_back_as_new(
    cur: Cursor, queue: SupabaseQueue
) -> None:
    """Work waiting for its organisation's limits to renew uses none of its attempts (T093)."""
    message_id = send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    queue.read(CV_PROCESSING, visibility_seconds=0, quantity=5)
    queue.defer(CV_PROCESSING, message_id, datetime.now(UTC) + timedelta(hours=2))
    assert queue.read(CV_PROCESSING, visibility_seconds=0, quantity=5) == []
    cur.execute("reset role")
    cur.execute(
        "select msg_id, read_ct, message, vt > now() + interval '119 minutes'"
        " from pgmq.q_cv_processing"
    )
    [(new_id, read_count, body, hidden)] = cur.fetchall()
    assert (new_id != message_id, read_count, body, hidden) == (True, 0, BODY, True)


def test_deferring_a_message_that_is_gone_changes_nothing(
    cur: Cursor, queue: SupabaseQueue
) -> None:
    message_id = send(cur, CV_PROCESSING, BODY)
    as_worker(cur)
    queue.delete(CV_PROCESSING, message_id)
    queue.defer(CV_PROCESSING, message_id, datetime.now(UTC) + timedelta(hours=2))
    cur.execute("reset role")
    cur.execute("select count(*) from pgmq.q_cv_processing")
    assert cur.fetchone() == (0,)
