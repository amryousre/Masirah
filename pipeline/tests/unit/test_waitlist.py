"""The landing page's waitlist (migration 0027): companies ask for an account, the owner invites.

A visitor gives a work email and nothing else. It goes into private.waitlist, which no API role can
read, through one narrow function a visitor may call. Asking twice, in any letter case, is harmless
and keeps one row. What isn't an email, or a language the site doesn't have, is refused.
"""

import psycopg
import pytest

from tests.database import Cursor, act_as, seed_tenant

pytestmark = pytest.mark.database


@pytest.fixture(autouse=True)
def empty_list(cur: Cursor) -> None:
    """Each test starts from an empty list; the transaction is rolled back after it."""
    cur.execute("delete from private.waitlist")


def join(cur: Cursor, email: str, locale: str = "ar") -> None:
    act_as(cur, None)
    cur.execute("select public.join_waitlist(%s, %s)", (email, locale))
    cur.execute("reset role")


def waiting(cur: Cursor) -> list[tuple[str, str]]:
    cur.execute("select email, locale from private.waitlist order by email")
    return [(row[0], row[1]) for row in cur.fetchall()]


def test_a_visitor_joins_with_a_work_email(cur: Cursor) -> None:
    join(cur, "  Nourhan@Delta-Soft.com ", "en")
    assert waiting(cur) == [("nourhan@delta-soft.com", "en")]


def test_asking_again_in_any_case_keeps_one_row(cur: Cursor) -> None:
    join(cur, "nourhan@delta-soft.com")
    join(cur, "NOURHAN@delta-soft.com", "en")
    assert waiting(cur) == [("nourhan@delta-soft.com", "ar")]


@pytest.mark.parametrize(
    ("email", "locale"),
    [
        ("not an email", "ar"),
        ("nourhan@", "ar"),
        ("@delta-soft.com", "ar"),
        ("a" * 250 + "@delta-soft.com", "ar"),
        ("nourhan@delta-soft.com", "fr"),
    ],
    ids=["no-at", "no-domain", "no-name", "too-long", "unknown-locale"],
)
def test_what_is_not_a_request_is_refused(cur: Cursor, email: str, locale: str) -> None:
    act_as(cur, None)
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        cur.execute("select public.join_waitlist(%s, %s)", (email, locale))


def test_someone_signed_in_without_an_organisation_can_join(cur: Cursor) -> None:
    """Signed in with Google but not invited: the people most likely to want an account."""
    tenant = seed_tenant(cur, "alpha")
    act_as(cur, tenant.user_id)
    cur.execute("select public.join_waitlist(%s, %s)", ("someone@new-co.com", "en"))
    cur.execute("reset role")
    assert ("someone@new-co.com", "en") in waiting(cur)


def test_a_flood_is_refused_once_an_hour_holds_a_hundred(cur: Cursor) -> None:
    cur.execute(
        "insert into private.waitlist (email, locale)"
        " select 'flood' || n || '@spam.example', 'en' from generate_series(1, 100) n"
    )
    act_as(cur, None)
    with pytest.raises(psycopg.errors.ConfigurationLimitExceeded):
        cur.execute("select public.join_waitlist(%s, %s)", ("real@delta-soft.com", "ar"))


def test_the_operator_reads_the_list_with_the_service_role(cur: Cursor) -> None:
    join(cur, "nourhan@delta-soft.com")
    cur.execute("set local role service_role")
    cur.execute("select email from private.waitlist")
    assert cur.fetchall() == [("nourhan@delta-soft.com",)]


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_no_api_role_can_read_the_list(cur: Cursor, role: str) -> None:
    join(cur, "nourhan@delta-soft.com")
    if role == "anon":
        act_as(cur, None)
    else:
        act_as(cur, seed_tenant(cur, "alpha").user_id)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        cur.execute("select email from private.waitlist")


def test_the_list_is_not_reachable_through_the_public_api(cur: Cursor) -> None:
    cur.execute(
        "select count(*) from information_schema.tables"
        " where table_schema = 'public' and table_name like '%waitlist%'"
    )
    assert cur.fetchone() == (0,)
