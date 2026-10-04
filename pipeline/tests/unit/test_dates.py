"""Hijri and Gregorian dates and Arabic-Indic numerals (T038, FR-009).

A CV may write a job's start as "Jan 2021", "01/2021", "يناير ٢٠٢١" or "جمادى الأولى 1442 هـ".
They all become one comparable form, the one the corpus labels use: YYYY-MM, or YYYY when only a
year is given, or "present" for a role still held.
"""

import pytest

from masirah_pipeline.domain.dates import interpret_numerals, normalise_date


@pytest.mark.parametrize(
    ("written", "normalised"),
    [
        ("Jan 2021", "2021-01"),
        ("January 2021", "2021-01"),
        ("Sept. 2017", "2017-09"),
        ("sep 2017", "2017-09"),
        ("2021-01", "2021-01"),
        ("2021/1", "2021-01"),
        ("01/2021", "2021-01"),
        ("1-2021", "2021-01"),
        ("2005", "2005"),
        # Egypt writes day before month, so 13/01/2021 is 13 January.
        ("13/01/2021", "2021-01"),
        ("03/07/2019", "2019-07"),
        ("07.03.2019", "2019-03"),
    ],
)
def test_gregorian_dates_in_latin(written: str, normalised: str) -> None:
    assert normalise_date(written) == normalised


@pytest.mark.parametrize(
    ("written", "normalised"),
    [
        ("يناير ٢٠٢٢", "2022-01"),
        ("مارس 2023", "2023-03"),
        ("أبريل 2020", "2020-04"),
        ("ابريل 2020", "2020-04"),
        ("يونيه 2019", "2019-06"),
        ("يوليو 2018", "2018-07"),
        ("أغسطس ٢٠١٧", "2017-08"),
        ("ديسمبر 2016", "2016-12"),
        # The Levantine month names, which Arabic CVs from Syria, Lebanon and Jordan use.
        ("كانون الثاني 2020", "2020-01"),
        ("شباط 2020", "2020-02"),
        ("تشرين الأول 2019", "2019-10"),
        ("٢٠١٣", "2013"),
        ("۲۰۱۳", "2013"),
    ],
)
def test_gregorian_dates_in_arabic(written: str, normalised: str) -> None:
    assert normalise_date(written) == normalised


@pytest.mark.parametrize(
    ("written", "normalised"),
    [
        # Ramadan 1440 ran from 6 May to 3 June 2019.
        ("رمضان 1440 هـ", "2019-05"),
        ("رمضان ١٤٤٠هـ", "2019-05"),
        # Muharram 1445 ran from 19 July to 17 August 2023, mostly in August.
        ("محرم 1445", "2023-08"),
        ("ذو الحجة 1443 هـ", "2022-07"),
        # Rabi al-Awwal 1442 began on 18 October 2020; its middle is in November.
        ("ربيع الأول 1442", "2020-11"),
        # A Hijri year alone is the Gregorian year its middle falls in: 1440 ran Sep 2018 to Aug
        # 2019.
        ("1440 هـ", "2019"),
        ("١٤٤٠ه", "2019"),
    ],
)
def test_hijri_dates_become_gregorian(written: str, normalised: str) -> None:
    assert normalise_date(written) == normalised


@pytest.mark.parametrize(
    "written",
    [
        "Present",
        "present",
        "Current",
        "Now",
        "till now",
        "to date",
        "Ongoing",
        "حتى الآن",
        "الآن",
        "حاليا",
        "حتى تاريخه",
    ],
)
def test_a_role_still_held(written: str) -> None:
    assert normalise_date(written) == "present"


@pytest.mark.parametrize("written", ["", "soon", "Spring", "13/2021", "2021-13", "1850", "3000"])
def test_what_is_not_a_date_is_none(written: str) -> None:
    assert normalise_date(written) is None


@pytest.mark.parametrize(
    ("written", "read"),
    [
        ("٠١٠٠ ٠٠٠ ٠٢٠٢", "0100 000 0202"),
        ("۱۲۳", "123"),
        ("٣\N{ARABIC DECIMAL SEPARATOR}\N{ARABIC-INDIC DIGIT FIVE} سنوات", "3.5 سنوات"),
        ("١٬٢٠٠", "1,200"),
        ("2021", "2021"),
    ],
)
def test_arabic_indic_numerals_are_read_as_digits(written: str, read: str) -> None:
    assert interpret_numerals(written) == read


@pytest.mark.parametrize(
    ("written", "normalised"),
    [("15 March 2021", "2021-03"), ("١٥ مارس ٢٠٢١", "2021-03"), ("1st Jan 2020", "2020-01")],
)
def test_a_day_beside_a_named_month(written: str, normalised: str) -> None:
    assert normalise_date(written) == normalised


def test_a_number_beside_a_named_month_that_is_no_day_is_refused() -> None:
    assert normalise_date("45 March 2021") is None


@pytest.mark.parametrize(
    "written", ["31 February 2024", "30 فبراير 2023", "31/04/2021", "29/02/2023"]
)
def test_a_day_the_month_does_not_have_makes_the_date_invalid(written: str) -> None:
    assert normalise_date(written) is None


def test_a_leap_day_is_a_real_day() -> None:
    assert normalise_date("29 February 2024") == "2024-02"
