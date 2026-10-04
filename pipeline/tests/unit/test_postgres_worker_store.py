"""The worker's tenant data in Postgres (T054).

Every test acts as masirah_worker, so the adapter works under the same row level security it will
meet in production: each operation declares its organisation, and another tenant's rows are out
of reach even by identifier.
"""

import uuid
from decimal import Decimal

import pytest

from masirah_pipeline.adapters.postgres_worker_store import PostgresWorkerStore
from masirah_pipeline.ports.worker_store import CandidateDetails, Extraction
from tests.database import Cursor, Tenant, seed_tenant

pytestmark = pytest.mark.database

DETAILS = CandidateDetails(
    "Mona Abdallah", "mona@mail.test", "+201001234567", "Cairo", "منى عبدالله"
)


def extraction(status: str = "extracted") -> Extraction:
    return Extraction(
        source="native_text",
        confidence=Decimal("0.95"),
        profile={"name": "Mona Abdallah"},
        candidate=DETAILS,
        status=status,  # type: ignore[arg-type]
    )


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


@pytest.fixture
def store(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> PostgresWorkerStore:
    cur.execute("set local role masirah_worker")
    return PostgresWorkerStore(cur.connection)


def new_file(cur: Cursor, tenant: Tenant) -> uuid.UUID:
    """A freshly uploaded CV file with no candidate and no profile yet."""
    file_id = uuid.uuid4()
    cur.execute("reset role")
    cur.execute(
        "insert into public.cv_file (id, organisation_id, storage_path, original_filename,"
        " mime_type, byte_size, content_hash) values (%s, %s, %s, 'cv.pdf', 'application/pdf',"
        " 10, %s)",
        (
            file_id,
            tenant.organisation_id,
            tenant.storage_path.replace(str(tenant.row_ids["cv_file"]), str(file_id)),
            "d" * 64,
        ),
    )
    cur.execute("set local role masirah_worker")
    return file_id


def test_it_reads_a_cv_file(store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    cv_file = store.cv_file(alpha.organisation_id, alpha.row_ids["cv_file"])
    assert cv_file is not None
    assert (cv_file.id, cv_file.storage_path, cv_file.status) == (
        alpha.row_ids["cv_file"],
        alpha.storage_path,
        "queued",
    )
    assert cv_file.candidate_id == alpha.row_ids["candidate"]


def test_another_tenants_file_is_not_there(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    assert store.cv_file(alpha.organisation_id, beta.row_ids["cv_file"]) is None


def test_it_reads_the_current_profile(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    stored = store.current_profile(alpha.organisation_id, alpha.row_ids["cv_file"])
    assert stored is not None
    assert (stored.version, stored.profile) == (1, {"full_name": "alpha"})


def test_an_extraction_becomes_the_current_version(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant], cur: Cursor
) -> None:
    alpha, _ = tenants
    store.record_extraction(alpha.organisation_id, alpha.row_ids["cv_file"], extraction())
    stored = store.current_profile(alpha.organisation_id, alpha.row_ids["cv_file"])
    assert stored is not None
    assert (stored.version, stored.confidence, stored.profile) == (
        2,
        Decimal("0.950"),
        {"name": "Mona Abdallah"},
    )
    cur.execute(
        "select count(*) from public.parsed_profile where cv_file_id = %s",
        (alpha.row_ids["cv_file"],),
    )
    assert cur.fetchone() == (2,)


def test_an_extraction_creates_the_candidate_of_a_new_file(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant], cur: Cursor
) -> None:
    alpha, _ = tenants
    file_id = new_file(cur, alpha)
    candidate_id = store.record_extraction(alpha.organisation_id, file_id, extraction())
    cur.execute(
        "select full_name, email, phone, location, name_normalised from public.candidate"
        " where id = %s",
        (candidate_id,),
    )
    assert cur.fetchone() == (
        "Mona Abdallah",
        "mona@mail.test",
        "+201001234567",
        "Cairo",
        "منى عبدالله",
    )
    cv_file = store.cv_file(alpha.organisation_id, file_id)
    assert cv_file is not None
    assert (cv_file.candidate_id, cv_file.status) == (candidate_id, "extracted")


def test_an_extraction_updates_the_candidate_the_file_already_has(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    candidate_id = store.record_extraction(
        alpha.organisation_id, alpha.row_ids["cv_file"], extraction()
    )
    assert candidate_id == alpha.row_ids["candidate"]


def test_a_doubtful_extraction_is_recorded_for_review(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    store.record_extraction(
        alpha.organisation_id, alpha.row_ids["cv_file"], extraction("needs_review")
    )
    cv_file = store.cv_file(alpha.organisation_id, alpha.row_ids["cv_file"])
    assert cv_file is not None
    assert cv_file.status == "needs_review"


def test_an_extraction_cannot_land_in_another_tenant(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    with pytest.raises(LookupError):
        store.record_extraction(alpha.organisation_id, beta.row_ids["cv_file"], extraction())


def test_a_file_moves_through_its_statuses(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant], cur: Cursor
) -> None:
    alpha, _ = tenants
    file_id = alpha.row_ids["cv_file"]
    store.mark_extracting(alpha.organisation_id, file_id)
    cur.execute("select status, failure_reason from public.cv_file where id = %s", (file_id,))
    assert cur.fetchone() == ("extracting", None)
    store.mark_failed(alpha.organisation_id, file_id, "the PDF is encrypted")
    cur.execute("select status, failure_reason from public.cv_file where id = %s", (file_id,))
    assert cur.fetchone() == ("failed", "the PDF is encrypted")
    store.mark_needs_review(alpha.organisation_id, file_id)
    cur.execute("select status, failure_reason from public.cv_file where id = %s", (file_id,))
    assert cur.fetchone() == ("needs_review", None)


def test_another_tenants_file_cannot_be_failed(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    with pytest.raises(LookupError):
        store.mark_failed(alpha.organisation_id, beta.row_ids["cv_file"], "planted")


def test_an_existing_application_is_reused(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    application_id = store.ensure_application(
        alpha.organisation_id, alpha.row_ids["candidate"], alpha.row_ids["job"]
    )
    assert application_id == alpha.row_ids["application"]


def test_a_new_application_is_created_once(
    store: PostgresWorkerStore, tenants: tuple[Tenant, Tenant], cur: Cursor
) -> None:
    alpha, _ = tenants
    file_id = new_file(cur, alpha)
    candidate_id = store.record_extraction(alpha.organisation_id, file_id, extraction())
    first = store.ensure_application(alpha.organisation_id, candidate_id, alpha.row_ids["job"])
    second = store.ensure_application(alpha.organisation_id, candidate_id, alpha.row_ids["job"])
    assert first == second
    cur.execute("select decision from public.application where id = %s", (first,))
    assert cur.fetchone() == ("undecided",)
