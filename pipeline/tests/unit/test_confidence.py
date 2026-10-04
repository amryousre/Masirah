"""How far a profile can be trusted, and where a doubtful one goes (T079, FR-011).

Extraction copies values as the CV writes them, so a value the CV's text does not contain was
invented or misread. Confidence is the share of the profile's values that the text contains,
which is what lets the worker flag a doubtful profile rather than present a fabricated one.
"""

import json
from pathlib import Path

import pytest

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.domain.confidence import THRESHOLD, confidence, needs_review
from masirah_pipeline.domain.profile import (
    Certification,
    Education,
    Employment,
    Profile,
    profile_from_output,
)

CORPUS = Path(__file__).parents[1] / "fixtures" / "cvs"
NATIVE_PDFS = sorted(CORPUS.glob("*-native-*.pdf"))

TEXT = """\
محمد أحمد عبد الرحمن
القاهرة | mohamed.a@mail.test | ٠١٠٠ ١٢٣ ٤٥٦٧
Accountant at Nile Pharma, 2019 - present
بكالوريوس تجارة - جامعة عين شمس
Skills: Excel, SAP
Certified Management Accountant (IMA)
"""


def profile(**changes: object) -> Profile:
    values: dict[str, object] = {
        "name": "محمد أحمد عبد الرحمن",
        "emails": ("mohamed.a@mail.test",),
        "phones": ("+201001234567",),
        "location": "القاهرة",
        "years_of_experience": None,
        "employment": (Employment("Nile Pharma", "Accountant", "2019", "present"),),
        "education": (Education("جامعة عين شمس", "بكالوريوس تجارة", None, None),),
        "skills": ("Excel", "SAP"),
        "languages": (),
        "certifications": (Certification("Certified Management Accountant", "IMA"),),
    }
    return Profile(**(values | changes))  # type: ignore[arg-type]


def test_a_profile_the_text_fully_supports_is_fully_trusted() -> None:
    assert confidence(profile(), TEXT) == 1


def test_an_invented_value_lowers_confidence() -> None:
    invented = profile(skills=("Excel", "SAP", "Oracle Financials"))
    assert confidence(invented, TEXT) < 1


def test_spelling_variants_of_arabic_letters_still_match() -> None:
    """Hamza on alef, taa marbuta and alef maqsura vary between a CV and its extraction."""
    assert confidence(profile(name="محمد احمد عبد الرحمن"), TEXT) == 1


def test_case_and_spacing_do_not_matter() -> None:
    assert confidence(profile(skills=("excel", "sap")), TEXT) == 1


def test_a_value_must_match_whole_words() -> None:
    """ "SA" is inside "SAP" but is not a skill the CV lists."""
    assert confidence(profile(skills=("SA",)), TEXT) < 1


def test_a_phone_matches_its_written_form() -> None:
    """Phones come back in E.164, while the CV writes them nationally and in Arabic-Indic digits."""
    assert confidence(profile(phones=("+201001234567",)), TEXT) == 1
    assert confidence(profile(phones=("+201009999999",)), TEXT) < 1


def test_values_the_extraction_rewrites_are_not_checked() -> None:
    """Dates are normalised, so their written form differs; they cannot count against a profile."""
    rewritten = profile(employment=(Employment("Nile Pharma", "Accountant", "2019-01", "present"),))
    assert confidence(rewritten, TEXT) == 1


def test_an_empty_profile_is_not_trusted() -> None:
    empty = profile(
        name=None,
        emails=(),
        phones=(),
        location=None,
        employment=(),
        education=(),
        skills=(),
        certifications=(),
    )
    assert confidence(empty, TEXT) == 0


@pytest.mark.parametrize(
    ("score", "doubtful"),
    [(THRESHOLD, False), (1.0, False), (THRESHOLD - 0.01, True), (0.0, True)],
)
def test_a_profile_below_the_threshold_needs_review(score: float, doubtful: bool) -> None:
    assert needs_review(score) is doubtful


@pytest.mark.parametrize("pdf", NATIVE_PDFS, ids=lambda path: path.stem)
def test_a_correct_profile_of_a_real_document_is_trusted(pdf: Path) -> None:
    """The corpus labels are what a perfect extraction returns, so each must clear the threshold
    against its own document's text: the threshold flags inventions, not how CVs are laid out."""
    label = json.loads(pdf.with_suffix(".json").read_text(encoding="utf-8"))
    truth = profile_from_output(label["profile"])
    assert confidence(truth, read_native_text(pdf.read_bytes())) >= THRESHOLD
