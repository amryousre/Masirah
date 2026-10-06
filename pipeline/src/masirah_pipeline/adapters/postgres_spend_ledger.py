"""The spend ledger in Postgres, as the masirah_worker role (T093, migration 0025).

Each operation acts in the one organisation it names, like every other worker operation, so row
level security keeps one organisation's spend out of another's. A call's cost is committed as
soon as it is recorded: it was paid for whether or not the rest of the CV's work succeeds.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import psycopg

from masirah_pipeline.adapters.tenant_transaction import acting_for
from masirah_pipeline.domain.budget import Limits, Usage
from masirah_pipeline.ports.spend_ledger import Spend


class PostgresSpendLedger:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def record(self, spend: Spend) -> None:
        with acting_for(self._connection, spend.organisation_id) as cur:
            cur.execute(
                "insert into public.model_spend"
                " (organisation_id, cv_file_id, kind, provider, model, cost_egp)"
                " values (%s, %s, %s, %s, %s, %s)",
                (
                    spend.organisation_id,
                    spend.cv_file_id,
                    spend.kind,
                    spend.provider,
                    spend.model,
                    spend.cost_egp,
                ),
            )

    def usage(self, organisation_id: UUID, since: datetime) -> Usage:
        with acting_for(self._connection, organisation_id) as cur:
            row = cur.execute(
                "select count(distinct cv_file_id) filter (where kind = 'extraction'),"
                " coalesce(sum(cost_egp), 0)"
                " from public.model_spend where organisation_id = %s and spent_at >= %s",
                (organisation_id, since),
            ).fetchone()
        if row is None:
            return Usage(0, Decimal(0))
        return Usage(cvs=int(row[0]), spend_egp=cast(Decimal, row[1]))

    def limits(self, organisation_id: UUID) -> Limits:
        with acting_for(self._connection, organisation_id) as cur:
            row = cur.execute(
                "select monthly_cv_limit, monthly_spend_ceiling_egp from public.organisation"
                " where id = %s",
                (organisation_id,),
            ).fetchone()
        if row is None:
            raise LookupError(f"organisation {organisation_id} has no limits to read")
        return Limits(cvs_per_month=int(row[0]), spend_ceiling_egp=cast(Decimal, row[1]))
