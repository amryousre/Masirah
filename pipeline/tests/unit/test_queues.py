"""The processing queues (T022, contracts/queue-message.md).

Messages carry organisation identifiers and storage paths, so the queues belong to the server
alone: the service role sends, reads and deletes, while anonymous and signed-in sessions cannot
touch them by any route. An undeleted message comes back, which is the retry mechanism.
"""

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

from tests.database import Cursor

pytestmark = pytest.mark.database

QUEUES = ["cv_processing", "cv_rescoring"]


def send(cur: Cursor, queue: str, payload: dict[str, str]) -> int:
    cur.execute("select * from pgmq_public.send(%s, %s)", (queue, Jsonb(payload)))
    row = cur.fetchone()
    assert row is not None
    msg_id: int = row[0]
    return msg_id


def test_both_contract_queues_exist(cur: Cursor) -> None:
    cur.execute("select queue_name from pgmq.list_queues()")
    assert {row[0] for row in cur.fetchall()} >= set(QUEUES)


@pytest.mark.parametrize("queue", QUEUES)
def test_the_server_sends_reads_and_deletes(cur: Cursor, queue: str) -> None:
    cur.execute("set local role service_role")
    msg_id = send(cur, queue, {"probe": queue})
    cur.execute("select msg_id, message from pgmq_public.read(%s, 30, 1000)", (queue,))
    assert (msg_id, {"probe": queue}) in cur.fetchall()
    cur.execute("select pgmq_public.delete(%s, %s)", (queue, msg_id))
    assert cur.fetchone() == (True,)


def test_an_undeleted_message_returns_for_retry(cur: Cursor) -> None:
    cur.execute("set local role service_role")
    msg_id = send(cur, "cv_processing", {"probe": "retry"})
    read_counts = []
    for _ in range(2):
        cur.execute("select msg_id, read_ct from pgmq_public.read('cv_processing', 0, 1000)")
        read_counts += [read_ct for mid, read_ct in cur.fetchall() if mid == msg_id]
    assert read_counts == [1, 2]


@pytest.mark.parametrize("role", ["anon", "authenticated"])
@pytest.mark.parametrize(
    "statement",
    [
        "select * from pgmq_public.send('cv_processing', '{}'::jsonb)",
        "select * from pgmq_public.read('cv_processing', 30, 1)",
        "select * from pgmq_public.pop('cv_processing')",
        "select pgmq_public.delete('cv_processing', 1)",
        "select * from pgmq.q_cv_processing",
        "select * from pgmq.a_cv_processing",
    ],
    ids=["send", "read", "pop", "delete", "queue-table", "archive-table"],
)
def test_api_roles_cannot_touch_the_queues(cur: Cursor, role: str, statement: str) -> None:
    cur.execute(sql.SQL("set local role {}").format(sql.Identifier(role)))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(statement)


def test_every_queue_table_has_row_level_security(cur: Cursor) -> None:
    """Supabase lint 0019: an exposed queue without RLS is readable by anyone with the URL."""
    cur.execute(
        "select relname, relrowsecurity from pg_class"
        " where relnamespace = 'pgmq'::regnamespace and relkind = 'r'"
        " and relname ~ '^[qa]_'"
    )
    tables: dict[str, bool] = dict(cur.fetchall())
    assert set(tables) >= {f"{prefix}_{queue}" for prefix in "qa" for queue in QUEUES}
    assert [name for name, rls in tables.items() if not rls] == []
