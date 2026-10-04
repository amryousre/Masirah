"""The scoring input: a profile with its protected attributes removed (T088, FR-017).

FR-017 excludes name, gender, age, photograph, nationality and marital status from scoring. A
profile holds no photograph, gender, nationality or marital status field, so what remains to
remove is what identifies the person or betrays those attributes indirectly:

- the name, which suggests gender and often religion or origin;
- emails and phones, which identify the person and can carry a birth year;
- education dates, because a graduation year is a close proxy for age.

Employment dates stay, since experience and tenure are scored from them. The input is an allow
list: a field added to the profile later stays out until someone decides it is safe to score.

What redaction cannot remove is grammatical gender: Arabic job titles agree with the person who
holds them (محاسب, محاسبة). The scoring instructions tell the model to disregard it, and the
bias suite (T084) checks that a rating does not move with it.
"""

from typing import Any

from masirah_pipeline.domain.profile import Profile

EDUCATION_PARTS = ("institution", "qualification")


def scoring_input(profile: Profile) -> dict[str, Any]:
    whole = profile.as_dict()
    return {
        "location": whole["location"],
        "years_of_experience": whole["years_of_experience"],
        "employment": whole["employment"],
        "education": [
            {part: degree[part] for part in EDUCATION_PARTS} for degree in whole["education"]
        ],
        "skills": whole["skills"],
        "languages": whole["languages"],
        "certifications": whole["certifications"],
    }
