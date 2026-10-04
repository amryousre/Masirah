"""The Supabase queue adapter and the worker's own database role (T053, contracts/queue-message.md).

The worker reads, deletes and archives messages as masirah_worker, a role granted exactly that:
it cannot send a message, so a compromised worker cannot plant work for itself, and it does not
need the service role, which bypasses row level security everywhere.
"""

from typing import Any

import psycopg
import pytest
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
        "insert into pgmq.q_cv_processing (message) values ('{}'::jsonb)",
        "update pgmq.q_cv_processing set message = '{}'::jsonb",
        "select * from pgmq_public.pop('cv_processing')",
        "select message from pgmq.a_cv_processing",
    ],
    ids=["send", "pgmq-send", "insert", "rewrite", "pop", "read-archive"],
)
def test_the_worker_cannot_send_rewrite_or_reread_messages(cur: Cursor, statement: str) -> None:
    as_worker(cur)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(statement)


def test_the_migration_gives_the_worker_role_no_login(cur: Cursor) -> None:
    """Login is granted where the worker is deployed, with a password that never sits in git."""
    cur.execute("select rolcanlogin, rolbypassrls from pg_roles where rolname = %s", (WORKER,))
    assert cur.fetchone() == (False, False)
