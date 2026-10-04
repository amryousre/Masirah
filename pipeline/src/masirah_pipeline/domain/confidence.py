"""How far an extracted profile can be trusted, and whether it needs review (T079, FR-011).

Extraction copies every value as the CV writes it, so a value the CV's text does not contain was
invented or misread. Confidence is the share of the profile's checkable values that the text
contains, matched as whole words after folding case, spacing and the Arabic letters whose
spelling varies. Phones come back in E.164 and are matched by their digits. Dates, years of
experience and language levels are rewritten by extraction or too short to prove anything, so
they are not checked.

A profile with nothing checkable is not trusted: an empty extraction from a text that has one
is a failure, not a success.
"""

import re
import unicodedata
from collections.abc import Iterator

from masirah_pipeline.domain.arabic import ARABIC_LETTERS, ARABIC_MARKS
from masirah_pipeline.domain.dates import interpret_numerals
from masirah_pipeline.domain.profile import Profile

# Below this share of values found in the text, a profile goes to the review queue.
THRESHOLD = 0.8
# A national number's significant digits: an Egyptian mobile's ten after the leading zero or +20.
PHONE_DIGITS = 9
NON_WORD = re.compile(r"[\W_]+")
# Spaces, hyphens, the en dash, dots, slashes and brackets that CVs put inside phone numbers.
DIGIT_SEPARATORS = re.compile(r"(?<=\d)[\s\-\u2013./()]+(?=\d)")


def confidence(profile: Profile, text: str) -> float:
    words = f" {_folded(text)} "
    digits = DIGIT_SEPARATORS.sub("", interpret_numerals(text))
    found = [f" {_folded(value)} " in words for value in _words(profile) if _folded(value)]
    found += [phone[-PHONE_DIGITS:] in digits for phone in _phone_digits(profile)]
    return sum(found) / len(found) if found else 0.0


def needs_review(score: float) -> bool:
    return score < THRESHOLD


def _words(profile: Profile) -> Iterator[str]:
    if profile.name:
        yield profile.name
    if profile.location:
        yield profile.location
    yield from profile.emails
    yield from profile.skills
    for job in profile.employment:
        yield from (value for value in (job.employer, job.title) if value)
    for degree in profile.education:
        yield from (value for value in (degree.institution, degree.qualification) if value)
    for certificate in profile.certifications:
        yield from (value for value in (certificate.name, certificate.issuer) if value)


def _phone_digits(profile: Profile) -> Iterator[str]:
    for phone in profile.phones:
        digits = "".join(char for char in interpret_numerals(phone) if char.isdigit())
        if len(digits) >= PHONE_DIGITS:
            yield digits


def _folded(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = ARABIC_MARKS.sub("", text).translate(ARABIC_LETTERS).casefold()
    return " ".join(NON_WORD.sub(" ", text).split())
