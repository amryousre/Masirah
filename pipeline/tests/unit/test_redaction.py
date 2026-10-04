"""Protected attributes never reach the scoring model (T085, FR-017, worker obligation 6).

FR-017 requires the exclusion to be demonstrable by an automated test. These tests build the
scoring input from a profile carrying distinctive values in every identifying field and check
that none survives, while everything a score is based on does.
"""

import json

from masirah_pipeline.domain.profile import (
    Certification,
    Education,
    Employment,
    Language,
    Profile,
)
from masirah_pipeline.domain.redaction import scoring_input

NAME = "Zeinab Fathy Abdelaziz"
EMAIL = "zeinab.fathy.1994@mail.test"
PHONE = "+201001234567"
GRADUATED = "2016"

PROFILE = Profile(
    name=NAME,
    emails=(EMAIL,),
    phones=(PHONE,),
    location="Alexandria",
    years_of_experience=7.0,
    employment=(Employment("Nile Pharma", "Senior Accountant", "2019-03", "present"),),
    education=(Education("Alexandria University", "BCom Accounting", "2012", GRADUATED),),
    skills=("SAP", "IFRS"),
    languages=(Language("English", "Fluent"),),
    certifications=(Certification("CMA", "IMA"),),
)


def serialised() -> str:
    return json.dumps(scoring_input(PROFILE), ensure_ascii=False)


def test_the_name_is_removed() -> None:
    assert "Zeinab" not in serialised()
    assert "Fathy" not in serialised()


def test_contact_details_are_removed() -> None:
    """They identify the person and say nothing about fit; an email can carry a birth year."""
    assert EMAIL not in serialised()
    assert "1994" not in serialised()
    assert PHONE not in serialised()


def test_education_dates_are_removed() -> None:
    """A graduation year is a close proxy for age."""
    text = serialised()
    assert "2012" not in text
    assert GRADUATED not in text


def test_what_a_score_rests_on_is_kept() -> None:
    redacted = scoring_input(PROFILE)
    assert redacted["location"] == "Alexandria"
    assert redacted["years_of_experience"] == 7.0
    assert redacted["employment"] == [
        {"employer": "Nile Pharma", "title": "Senior Accountant", "start": "2019-03",
         "end": "present"}
    ]  # fmt: skip
    assert redacted["education"] == [
        {"institution": "Alexandria University", "qualification": "BCom Accounting"}
    ]
    assert redacted["skills"] == ["SAP", "IFRS"]
    assert redacted["languages"] == [{"language": "English", "level": "Fluent"}]
    assert redacted["certifications"] == [{"name": "CMA", "issuer": "IMA"}]


def test_only_known_fields_pass() -> None:
    """Gender, age, photograph, nationality and marital status have no field to pass through, and
    a field added to the profile later stays out until someone decides it is safe to score."""
    assert set(scoring_input(PROFILE)) == {
        "location",
        "years_of_experience",
        "employment",
        "education",
        "skills",
        "languages",
        "certifications",
    }
