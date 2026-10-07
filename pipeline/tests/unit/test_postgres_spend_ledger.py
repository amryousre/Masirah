"""The spend ledger as the worker role uses it (T093, AI-02, AI-06, migration 0025).

Every paid model call is a row, the month's usage is counted from them, and an organisation's
limits are read from it. Like every other worker operation, each acts in one declared
organisation, so another organisation's spend can be neither read nor added to.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import psycopg
import pytest

from masirah_pipeline.adapters.postgres_spend_ledger import PostgresSpendLedger
from masirah_pipeline.domain.budget import Limits, Usage
from masirah_pipeline.ports.spend_ledger import Spend
from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    seeded = seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")
    # Each test counts its own calls from nothing.
    cur.execute(
        "delete from public.model_spend where organisation_id = any(%s)",
        ([tenant.organisation_id for tenant in seeded],),
    )
    return seeded


@pytest.fixture
def ledger(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> PostgresSpendLedger:
    cur.execute("set local role masirah_worker")
    return PostgresSpendLedger(cur.connection)


def spend(tenant: Tenant, kind: str, cost: str, file: uuid.UUID | None = None) -> Spend:
    return Spend(
        tenant.organisation_id,
        file or tenant.row_ids["cv_file"],
        kind,  # type: ignore[arg-type]
        "anthropic",
        "model-x",
        Decimal(cost),
    )


def test_the_months_usage_counts_cvs_read_and_every_call_paid_for(
    ledger: PostgresSpendLedger, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    other = uuid.uuid4()
    for row in [
        spend(alpha, "extraction", "0.40"),
        spend(alpha, "extraction", "0.35"),  # a retry of the same CV is still one CV
        spend(alpha, "scoring", "1.20"),
        spend(alpha, "summary", "0.05"),
        spend(alpha, "extraction", "0.50", other),
    ]:
        ledger.record(row)
    usage = ledger.usage(alpha.organisation_id, datetime.now(UTC) - timedelta(days=1))
    assert usage == Usage(cvs=2, spend_egp=Decimal("2.5000"))


def test_spend_before_the_month_started_is_not_counted(
    cur: Cursor, ledger: PostgresSpendLedger, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    ledger.record(spend(alpha, "extraction", "0.40"))
    later = datetime.now(UTC) + timedelta(minutes=1)
    assert ledger.usage(alpha.organisation_id, later) == Usage(cvs=0, spend_egp=Decimal(0))


def test_another_organisations_spend_is_not_counted(
    ledger: PostgresSpendLedger, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    ledger.record(spend(beta, "extraction", "9.00"))
    usage = ledger.usage(alpha.organisation_id, datetime.now(UTC) - timedelta(days=1))
    assert usage == Usage(cvs=0, spend_egp=Decimal(0))


def test_spend_cannot_be_recorded_against_another_organisation(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    cur.execute("set local role masirah_worker")
    cur.execute(
        "select set_config('masirah.organisation_id', %s, true)", (str(alpha.organisation_id),)
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into public.model_spend (organisation_id, cv_file_id, kind, cost_egp)"
            " values (%s, %s, 'extraction', 1)",
            (beta.organisation_id, beta.row_ids["cv_file"]),
        )


def test_an_organisation_starts_with_the_pilots_limits(
    ledger: PostgresSpendLedger, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    assert ledger.limits(alpha.organisation_id) == Limits(300, Decimal("750.00"))


def test_a_member_reads_their_organisations_spend_and_cannot_write_it(
    cur: Cursor, ledger: PostgresSpendLedger, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    ledger.record(spend(alpha, "extraction", "0.40"))
    ledger.record(spend(beta, "extraction", "0.90"))
    cur.execute("reset role")
    act_as(cur, alpha.user_id)
    cur.execute("select cost_egp from public.model_spend")
    assert cur.fetchall() == [(Decimal("0.4000"),)]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "insert into public.model_spend (organisation_id, cv_file_id, kind, cost_egp)"
            " values (%s, %s, 'extraction', 0)",
            (alpha.organisation_id, alpha.row_ids["cv_file"]),
        )
