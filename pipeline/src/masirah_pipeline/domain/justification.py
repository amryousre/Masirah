"""What the scoring and summary calls ask for, and how their answers are read (T056).

The strong model rates each of the six components from 0 to 100 with the evidence for it, and
writes a justification that cites that CV's specifics (FR-015). The cheap model writes a three to
five line summary (FR-016). Both write in the reader's interface language, whatever the CV's.
Neither sets the total: domain/scoring.py computes it from the ratings and the job's weights.

The schemas are strict-compatible on both providers, like the profile's: every property
required and nothing extra allowed. Bounds are checked here rather than in the schema, so an
out-of-range rating is malformed output with its cost recorded, not a provider-specific refusal.
"""

import json
from dataclasses import dataclass
from typing import Any, Literal

from masirah_pipeline.domain.scoring import (
    COMPONENTS,
    Components,
    InvalidComponentsError,
    Weights,
    components_from,
)

Locale = Literal["ar", "en"]
LANGUAGES: dict[Locale, str] = {"ar": "Arabic", "en": "English"}
SUMMARY_LINES = range(3, 6)


class MalformedAssessmentError(ValueError):
    """An answer that does not hold a usable rating, justification or summary."""


@dataclass(frozen=True)
class JobSpec:
    title: str
    description: str | None
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]
    minimum_experience_years: int | None
    location: str | None
    language_requirement: str | None
    weights: Weights

    def as_dict(self) -> dict[str, Any]:
        """The job as the model reads it. Weights are left out: the model rates each component
        on its own, and the weighting is arithmetic done afterwards."""
        return {
            "title": self.title,
            "description": self.description,
            "required_skills": list(self.required_skills),
            "preferred_skills": list(self.preferred_skills),
            "minimum_experience_years": self.minimum_experience_years,
            "location": self.location,
            "language_requirement": self.language_requirement,
        }


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


SCORE_SCHEMA: dict[str, Any] = _object(
    {
        "components": _object(
            {
                name: _object({"rating": {"type": "integer"}, "evidence": {"type": "string"}})
                for name in COMPONENTS
            }
        ),
        "justification": {"type": "string"},
    }
)
SUMMARY_SCHEMA: dict[str, Any] = _object(
    {"summary": {"type": "array", "items": {"type": "string"}}}
)

SCORE_INSTRUCTIONS = """\
You assess how well a candidate fits a job, for a recruiter who makes the decision. You receive \
the job and the candidate's profile as JSON. The profile has been stripped of the candidate's \
name, contact details and education dates.

Rate each component from 0 to 100, as a whole number, on the evidence in the profile alone:
- skills_match: the job's required skills first, then its preferred skills.
- experience_relevance: how close the candidate's roles are to this job, and whether they meet \
the minimum years of experience.
- education: how well the qualifications suit the job.
- tenure_stability: how long the candidate has stayed in roles.
- language: whether the candidate's languages meet the job's language requirement. Rate 100 when \
the job states none.
- location: whether the candidate is in or near the job's location. Rate 100 when the job states \
none.

For each component give the evidence: the specific employers, titles, skills or other entries \
from the profile that the rating rests on, or what is missing.

Then write the justification: a short paragraph a recruiter can check against the CV, citing \
those specifics. Never write generic praise.

Never let any of these affect a rating: gender, including the grammatical gender of a job title \
(محاسب and محاسبة are the same job), age, religion, nationality, marital status, or anything \
else that suggests them. Never guess at them.

Write every evidence and the justification in {language}, whatever language the CV is in. Keep \
names of employers, institutions, skills and certifications as the profile writes them.
"""

SUMMARY_INSTRUCTIONS = """\
You summarise a candidate for a recruiter scanning a list. You receive the candidate's profile \
as JSON, stripped of their name, contact details and education dates.

Write three to five short lines, one item each: current or most recent role and total \
experience, the strongest skills, notable qualifications or certifications, and anything a \
recruiter would want at a glance. State only what the profile says. Never guess at gender, age, \
religion, nationality or marital status, and never mention them.

Write the lines in {language}, whatever language the CV is in. Keep names of employers, \
institutions, skills and certifications as the profile writes them.
"""


def score_instructions(locale: Locale) -> str:
    return SCORE_INSTRUCTIONS.format(language=LANGUAGES[locale])


def summary_instructions(locale: Locale) -> str:
    return SUMMARY_INSTRUCTIONS.format(language=LANGUAGES[locale])


def score_content(job: JobSpec, redacted_profile: dict[str, Any]) -> str:
    return json.dumps(
        {"job": job.as_dict(), "candidate": redacted_profile}, ensure_ascii=False, indent=1
    )


def summary_content(redacted_profile: dict[str, Any]) -> str:
    return json.dumps(redacted_profile, ensure_ascii=False, indent=1)


@dataclass(frozen=True)
class Rating:
    components: Components
    evidence: dict[str, str]
    justification: str


def rating_from_output(output: dict[str, Any]) -> Rating:
    try:
        parts = output["components"]
        ratings = {name: parts[name]["rating"] for name in COMPONENTS}
        evidence = {name: str(parts[name]["evidence"]) for name in COMPONENTS}
        components = components_from(ratings)
        justification = str(output["justification"]).strip()
    except (KeyError, TypeError, InvalidComponentsError) as error:
        raise MalformedAssessmentError(f"the ratings are not usable: {error}") from error
    if not justification:
        raise MalformedAssessmentError("the justification is empty")
    return Rating(components, evidence, justification)


def summary_from_output(output: dict[str, Any]) -> str:
    lines = output.get("summary")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        raise MalformedAssessmentError("the summary is not a list of lines")
    stripped = [line.strip() for line in lines]
    if len(stripped) not in SUMMARY_LINES or not all(stripped):
        raise MalformedAssessmentError(f"the summary has {len(stripped)} lines, not 3 to 5")
    return "\n".join(stripped)
