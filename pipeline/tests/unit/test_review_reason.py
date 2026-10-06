"""Why a CV waits in the review queue (T080, FR-011).

A file with nothing to read and a CV in a language version 1.0 does not read call for different
actions from the recruiter, so the queue must tell them apart, and say which language it found.
"""

from pathlib import Path

import pytest

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.domain.review_reason import Review, after_extraction, before_extraction

CORPUS = Path(__file__).parents[1] / "fixtures" / "cvs"


@pytest.mark.parametrize("text", [None, "", "  \n\t "], ids=["no-text-layer", "empty", "blank"])
def test_a_file_with_nothing_to_read_waits_as_no_text(text: str | None) -> None:
    assert before_extraction(text) == Review("no_text")


def test_a_cv_in_an_unsupported_language_names_the_language() -> None:
    text = read_native_text((CORPUS / "syn-fr-native-01.pdf").read_bytes())
    assert before_extraction(text) == Review("unsupported_language", "fr")


@pytest.mark.parametrize("name", ["en-native-02.pdf", "ar-native-01.pdf"])
def test_a_readable_cv_in_arabic_or_english_goes_on_to_extraction(name: str) -> None:
    assert before_extraction(read_native_text((CORPUS / name).read_bytes())) is None


def test_a_profile_the_text_does_not_support_waits_as_low_confidence() -> None:
    assert after_extraction(0.5) == Review("low_confidence")


def test_a_profile_the_text_supports_does_not_wait() -> None:
    assert after_extraction(0.95) is None


def test_only_an_unsupported_language_carries_a_language() -> None:
    with pytest.raises(ValueError, match="language"):
        Review("no_text", "fr")
    with pytest.raises(ValueError, match="language"):
        Review("unsupported_language")
