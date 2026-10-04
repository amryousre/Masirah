"""The worker's heartbeat and the service health figures (T030).

The worker records that it is alive; /api/health reads three aggregate figures that say whether
work is flowing. Anyone may read them, since a monitor calls the endpoint without signing in,
so they carry nothing about any organisation: no identifiers, no file names, no content.
"""

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

from masirah_pipeline.adapters.heartbeat import PostgresHeartbeat
from tests.database import Cursor

pytestmark = pytest.mark.database


def health(cur: Cursor, role: str = "anon") -> tuple[int, float | None, float | None]:
    cur.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
    cur.execute(
        "select queue_depth, oldest_message_seconds, heartbeat_age_seconds"
        " from public.service_health()"
    )
    row = cur.fetchone()
    assert row is not None
    cur.execute("reset role")
    depth, oldest, beat = row
    return depth, oldest, beat


@pytest.fixture(autouse=True)
def empty(cur: Cursor) -> None:
    cur.execute("delete from pgmq.q_cv_processing")
    cur.execute("delete from private.worker_heartbeat")


def test_an_idle_service_with_no_worker_reports_so(cur: Cursor) -> None:
    assert health(cur) == (0, None, None)


def test_the_worker_beat_is_seen(cur: Cursor) -> None:
    cur.execute("set local role masirah_worker")
    PostgresHeartbeat(cur.connection, "worker-1")()
    cur.execute("reset role")
    _, _, beat = health(cur)
    assert beat is not None
    assert 0 <= beat < 5


def test_the_latest_of_several_workers_counts(cur: Cursor) -> None:
    cur.execute(
        "insert into private.worker_heartbeat (worker, seen_at) values"
        " ('old', now() - interval '1 hour'), ('new', now() - interval '10 seconds')"
    )
    _, _, beat = health(cur)
    assert beat is not None
    assert 9 <= beat < 15


def test_waiting_messages_and_the_oldest_wait_are_counted(cur: Cursor) -> None:
    cur.execute("set local role service_role")
    for _ in range(3):
        cur.execute("select * from pgmq_public.send('cv_processing', %s)", (Jsonb({}),))
    cur.execute("reset role")
    cur.execute("update pgmq.q_cv_processing set enqueued_at = now() - interval '2 minutes'")
    depth, oldest, _ = health(cur)
    assert depth == 3
    assert oldest is not None
    assert 119 <= oldest < 125


def test_a_message_being_worked_on_is_not_waiting(cur: Cursor) -> None:
    """A message a worker has read is hidden until its visibility timeout. It counts towards the
    queue's depth, but it is in hand, not waiting, so it does not make the queue look stuck."""
    cur.execute("set local role service_role")
    cur.execute("select * from pgmq_public.send('cv_processing', %s)", (Jsonb({}),))
    cur.execute("reset role")
    cur.execute(
        "update pgmq.q_cv_processing set enqueued_at = now() - interval '2 hours',"
        " vt = now() + interval '5 minutes'"
    )
    depth, oldest, _ = health(cur)
    assert (depth, oldest) == (1, None)


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_a_caller_who_has_not_signed_in_may_read_the_figures(cur: Cursor, role: str) -> None:
    assert health(cur, role)[0] == 0


def test_the_figures_name_nothing(cur: Cursor) -> None:
    cur.execute(
        "select string_agg(name, ',' order by name) from ("
        "  select unnest(proargnames) as name from pg_proc"
        "  where oid = 'public.service_health'::regproc) names"
    )
    assert cur.fetchone() == ("heartbeat_age_seconds,oldest_message_seconds,queue_depth",)


@pytest.mark.parametrize("role", ["anon", "authenticated", "service_role"])
def test_only_the_worker_beats(cur: Cursor, role: str) -> None:
    cur.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select worker.beat('impostor')")
