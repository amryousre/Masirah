"""A person's correction of an extracted field is kept (T074, FR-010, migration 0024).

A member corrects a field through public.correct_profile, which keeps the correction beside the
machine's value rather than over it, says who made it and when, and records it on the audit
trail. A later extraction of the same file adds a new version of the profile, and the correction
carries over to it, so a better extraction never silently undoes what a person fixed.
"""

import uuid
from decimal import Decimal
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from masirah_pipeline.adapters.postgres_worker_store import PostgresWorkerStore
from masirah_pipeline.domain.arabic import name_normalised
from masirah_pipeline.ports.worker_store import CandidateDetails, Extraction
from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database

EXTRACTED = {
    "name": "Mona Abdalla",
    "emails": ["mona@example.com"],
    "phones": [],
    "location": "Cairo",
    "years_of_experience": None,
    "employment": [
        {"employer": "Nile Pharma", "title": "Accountant", "start": "2019", "end": "present"}
    ],
    "education": [],
    "skills": ["Excel"],
    "languages": [],
    "certifications": [],
}

# The corrected name's searchable form, as the web folds it for correct_profile.
FOLDED = name_normalised("Mona Abdallah")


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    alpha, beta = seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")
    cur.execute(
        "update public.parsed_profile set profile = %s where id = %s",
        (Jsonb(EXTRACTED), alpha.row_ids["parsed_profile"]),
    )
    return alpha, beta


def correct(
    cur: Cursor,
    tenant: Tenant,
    file_id: uuid.UUID,
    corrections: dict[str, Any],
    folded: str | None = None,
) -> None:
    act_as(cur, tenant.user_id)
    cur.execute("select public.correct_profile(%s, %s, %s)", (file_id, Jsonb(corrections), folded))
    cur.execute("reset role")


def overrides(cur: Cursor, file_id: uuid.UUID) -> dict[str, Any]:
    cur.execute(
        "select field_overrides from public.parsed_profile where cv_file_id = %s and is_current",
        (file_id,),
    )
    row = cur.fetchone()
    assert row is not None
    value: dict[str, Any] = row[0]
    return value


def test_a_correction_is_kept_beside_the_extraction_with_who_made_it(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    file_id = alpha.row_ids["cv_file"]
    correct(cur, alpha, file_id, {"name": "Mona Abdallah"}, FOLDED)
    kept = overrides(cur, file_id)
    assert kept["name"]["value"] == "Mona Abdallah"
    assert kept["name"]["by"] == str(alpha.user_id)
    assert kept["name"]["at"]
    cur.execute(
        "select profile->>'name' from public.parsed_profile where cv_file_id = %s", (file_id,)
    )
    assert cur.fetchone() == ("Mona Abdalla",)


def test_the_correction_is_on_the_audit_trail(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    file_id = alpha.row_ids["cv_file"]
    correct(cur, alpha, file_id, {"name": "Mona Abdallah", "skills": ["Excel", "SAP"]}, FOLDED)
    cur.execute(
        "select actor_id, subject_type, subject_id, metadata from public.activity"
        " where action = 'candidate.corrected'"
    )
    [(actor, kind, subject, metadata)] = cur.fetchall()
    assert (actor, kind, subject) == (alpha.user_id, "candidate", alpha.row_ids["candidate"])
    assert metadata == {"cv_file_id": str(file_id), "fields": ["name", "skills"]}


def test_correcting_back_to_the_extracted_value_restores_it(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    file_id = alpha.row_ids["cv_file"]
    correct(cur, alpha, file_id, {"location": "Giza"})
    correct(cur, alpha, file_id, {"location": "Cairo"})
    assert overrides(cur, file_id) == {}


def test_an_unchanged_correction_keeps_who_first_made_it(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    file_id = alpha.row_ids["cv_file"]
    correct(cur, alpha, file_id, {"location": "Giza"})
    first = overrides(cur, file_id)["location"]
    correct(cur, alpha, file_id, {"location": "Giza", "skills": ["Excel", "SAP"]})
    assert overrides(cur, file_id)["location"] == first


def test_a_corrected_name_is_the_candidates_name(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    correct(cur, alpha, alpha.row_ids["cv_file"], {"name": "Mona Abdallah"}, FOLDED)
    cur.execute(
        "select full_name, name_normalised from public.candidate where id = %s",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchone() == ("Mona Abdallah", FOLDED)


def test_a_correction_survives_reprocessing(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    """The worker adds a new version, which keeps the correction, and the candidate keeps the
    corrected name rather than taking the machine's again."""
    alpha, _ = tenants
    file_id = alpha.row_ids["cv_file"]
    correct(cur, alpha, file_id, {"name": "Mona Abdallah"}, FOLDED)
    before = overrides(cur, file_id)

    cur.execute("set local role masirah_worker")
    PostgresWorkerStore(cur.connection).record_extraction(
        alpha.organisation_id,
        file_id,
        Extraction(
            source="native_text",
            confidence=Decimal("0.96"),
            profile=EXTRACTED | {"skills": ["Excel", "Oracle"]},
            candidate=CandidateDetails(
                "Mona Abdalla", "mona@example.com", None, "Cairo", "mona abdalla"
            ),
            review=None,
        ),
    )
    cur.execute("reset role")

    cur.execute(
        "select version, profile->'skills', field_overrides from public.parsed_profile"
        " where cv_file_id = %s and is_current",
        (file_id,),
    )
    assert cur.fetchone() == (2, ["Excel", "Oracle"], before)
    cur.execute(
        "select full_name, name_normalised from public.candidate where id = %s",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchone() == ("Mona Abdallah", FOLDED)


def test_a_name_cleared_by_a_person_stays_cleared(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    """A name a person removed is not searchable under the old name, and a new extraction does
    not bring the machine's name back."""
    alpha, _ = tenants
    file_id = alpha.row_ids["cv_file"]
    correct(cur, alpha, file_id, {"name": None}, "")
    cur.execute(
        "select full_name, name_normalised from public.candidate where id = %s",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchone() == (None, None)

    cur.execute("set local role masirah_worker")
    PostgresWorkerStore(cur.connection).record_extraction(
        alpha.organisation_id,
        file_id,
        Extraction(
            source="native_text",
            confidence=Decimal("0.96"),
            profile=EXTRACTED,
            candidate=CandidateDetails(
                "Mona Abdalla", "mona@example.com", None, "Cairo", "mona abdalla"
            ),
            review=None,
        ),
    )
    cur.execute("reset role")
    cur.execute(
        "select full_name, name_normalised from public.candidate where id = %s",
        (alpha.row_ids["candidate"],),
    )
    assert cur.fetchone() == (None, None)


@pytest.mark.parametrize(
    "corrections",
    [
        {"salary": 20000},
        {"emails": "mona@example.com"},
        {"name": ["Mona"]},
        {"years_of_experience": "six"},
        {"employment": [{"employer": "Nile Pharma", "salary": 1}]},
        {"employment": ["Nile Pharma"]},
    ],
    ids=[
        "unknown-field",
        "list-as-text",
        "text-as-list",
        "years-as-text",
        "unknown-part",
        "entry-as-text",
    ],
)
def test_a_correction_of_the_wrong_shape_is_refused(
    cur: Cursor, tenants: tuple[Tenant, Tenant], corrections: dict[str, Any]
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.RaiseException):
        cur.execute(
            "select public.correct_profile(%s, %s, null)",
            (alpha.row_ids["cv_file"], Jsonb(corrections)),
        )


def test_another_organisations_file_cannot_be_corrected(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, beta.user_id)
    with pytest.raises(psycopg.errors.RaiseException, match="no profile"):
        cur.execute(
            "select public.correct_profile(%s, %s, null)",
            (alpha.row_ids["cv_file"], Jsonb({"location": "Giza"})),
        )


def test_a_member_corrects_only_through_the_function(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute(
            "update public.parsed_profile set field_overrides = '{}' where cv_file_id = %s",
            (alpha.row_ids["cv_file"],),
        )
