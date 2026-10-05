"""A job's ranked candidates (T063, migration 0019).

job_candidates gives one row per application: the candidate, the latest score with its
justification, the extraction's confidence and the decision. It runs with the caller's row level
security, so a member reads only their own organisation's candidates.
"""

from decimal import Decimal

import psycopg
import pytest
from psycopg.types.json import Jsonb

from tests.database import Cursor, Tenant, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture
def tenants(cur: Cursor) -> tuple[Tenant, Tenant]:
    return seed_tenant(cur, "alpha"), seed_tenant(cur, "beta")


def rows(cur: Cursor, tenant: Tenant) -> list[tuple[object, ...]]:
    act_as(cur, tenant.user_id)
    cur.execute(
        "select full_name, total, justification, confidence, decision::text, decided_by_email"
        " from public.job_candidates where job_id = %s",
        (tenant.row_ids["job"],),
    )
    found = cur.fetchall()
    cur.execute("reset role")
    return found


def test_a_ranked_candidate_comes_with_score_reason_and_confidence(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, _ = tenants
    assert rows(cur, alpha) == [
        ("alpha candidate", 72, "Cites evidence.", Decimal("0.970"), "undecided", None)
    ]


def test_the_latest_score_is_the_one_shown(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    cur.execute(
        "insert into public.score (organisation_id, application_id, total, components,"
        " justification, summary, model_id, provider, prompt_version, input_hash, weights_hash,"
        " cost_egp, created_at) values (%s, %s, 85, %s, 'Rescored.', 'x', 'm', 'anthropic', 'v',"
        " %s, %s, 1, now() + interval '1 minute')",
        (alpha.organisation_id, alpha.row_ids["application"], Jsonb({}), "d" * 64, "e" * 64),
    )
    [row] = rows(cur, alpha)
    assert row[1:3] == (85, "Rescored.")


def test_a_decision_names_who_made_it(cur: Cursor, tenants: tuple[Tenant, Tenant]) -> None:
    alpha, _ = tenants
    cur.execute(
        "update public.application set decision = 'shortlisted', decided_by = %s,"
        " decided_at = now() where id = %s",
        (alpha.user_id, alpha.row_ids["application"]),
    )
    [row] = rows(cur, alpha)
    assert row[4:] == ("shortlisted", "alpha@example.test")


def test_a_member_reads_only_their_organisations_candidates(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    alpha, beta = tenants
    act_as(cur, alpha.user_id)
    cur.execute("select organisation_id from public.job_candidates")
    assert {row[0] for row in cur.fetchall()} == {alpha.organisation_id}
    cur.execute(
        "select count(*) from public.job_candidates where job_id = %s", (beta.row_ids["job"],)
    )
    assert cur.fetchone() == (0,)


def test_a_visitor_who_has_not_signed_in_reads_nothing(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select * from public.job_candidates")


def test_search_reads_the_folded_name_and_the_extracted_fields(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    """T069: what candidate search compares, so the web needs no profile to search."""
    alpha, _ = tenants
    cur.execute(
        "update public.candidate set name_normalised = 'محمد حسن' where id = %s",
        (alpha.row_ids["candidate"],),
    )
    cur.execute(
        "update public.parsed_profile set profile = %s where id = %s",
        (
            Jsonb(
                {
                    "location": "Nasr City, Cairo",
                    "skills": ["React", "SAP"],
                    "employment": [{"employer": "Vodafone Egypt", "title": "Engineer"}],
                    "education": [{"institution": "جامعة القاهرة", "qualification": "B.Sc."}],
                    "languages": [{"language": "English", "level": "fluent"}],
                    "certifications": [{"name": "CPA", "issuer": "AICPA"}],
                }
            ),
            alpha.row_ids["parsed_profile"],
        ),
    )
    act_as(cur, alpha.user_id)
    cur.execute(
        "select name_normalised, search_text from public.job_candidates where job_id = %s",
        (alpha.row_ids["job"],),
    )
    [(name, text)] = cur.fetchall()
    cur.execute("reset role")
    assert name == "محمد حسن"
    for value in ("Nasr City, Cairo", "React", "SAP", "Vodafone Egypt", "Engineer"):
        assert value in text
    for value in ("جامعة القاهرة", "B.Sc.", "English", "CPA", "AICPA"):
        assert value in text


def test_a_profile_without_its_lists_still_reads(
    cur: Cursor, tenants: tuple[Tenant, Tenant]
) -> None:
    """The seed's profile has none of the lists; search text is then empty, not an error."""
    alpha, _ = tenants
    act_as(cur, alpha.user_id)
    cur.execute(
        "select search_text from public.job_candidates where job_id = %s",
        (alpha.row_ids["job"],),
    )
    assert cur.fetchone() == ("",)
    cur.execute("reset role")
