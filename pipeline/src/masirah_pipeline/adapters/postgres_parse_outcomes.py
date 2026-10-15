"""The parse failure figures and the alert claim, through worker.parse_outcomes and
worker.claim_alert (migration 0028, T031)."""

from typing import Any

import psycopg

from masirah_pipeline.domain.parse_failures import ParseOutcomes


class PostgresParseOutcomes:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def __call__(self, window_seconds: int) -> ParseOutcomes:
        row = self._connection.execute(
            "select settled, failed, organisations from worker.parse_outcomes(%s)",
            (window_seconds,),
        ).fetchone()
        if row is None:
            return ParseOutcomes(settled=0, failed=0, organisations=0)
        settled, failed, organisations = row
        return ParseOutcomes(settled=settled, failed=failed, organisations=organisations)


class PostgresAlertClaim:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def __call__(self, kind: str, quiet_seconds: int) -> bool:
        row = self._connection.execute(
            "select worker.claim_alert(%s, %s)", (kind, quiet_seconds)
        ).fetchone()
        return bool(row and row[0])
