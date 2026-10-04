"""The structured profile extracted from a CV (T045, FR-008).

PROFILE_SCHEMA is the one output schema both model providers are asked to fill. It keeps to what
strict structured output accepts on both: every property required, nothing extra allowed, and a
value the CV does not give written as null, never left out. profile_from_output reads a model's
output into a Profile and refuses anything that does not fit (AI-01).

The conventions for each field, such as dates written YYYY-MM or YYYY and phones in E.164, are the
corpus labels' (tests/fixtures/cvs/README.md), so the accuracy gate scores exactly this shape.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


class MalformedProfileError(ValueError):
    """Model output that is not a profile."""


@dataclass(frozen=True)
class Employment:
    employer: str | None
    title: str | None
    start: str | None
    end: str | None


@dataclass(frozen=True)
class Education:
    institution: str | None
    qualification: str | None
    start: str | None
    end: str | None


@dataclass(frozen=True)
class Language:
    language: str | None
    level: str | None


@dataclass(frozen=True)
class Certification:
    name: str | None
    issuer: str | None


Record = Employment | Education | Language | Certification

# Each list of records, with the type of its items and their fields in order.
RECORDS: dict[str, tuple[type[Record], tuple[str, ...]]] = {
    "employment": (Employment, ("employer", "title", "start", "end")),
    "education": (Education, ("institution", "qualification", "start", "end")),
    "languages": (Language, ("language", "level")),
    "certifications": (Certification, ("name", "issuer")),
}
TEXT_LISTS = ("emails", "phones", "skills")
FIELDS = ("name", "location", "years_of_experience", *TEXT_LISTS, *RECORDS)


@dataclass(frozen=True)
class Profile:
    name: str | None
    emails: tuple[str, ...]
    phones: tuple[str, ...]
    location: str | None
    years_of_experience: float | None
    employment: tuple[Employment, ...]
    education: tuple[Education, ...]
    skills: tuple[str, ...]
    languages: tuple[Language, ...]
    certifications: tuple[Certification, ...]

    def as_dict(self) -> dict[str, Any]:
        """The profile in the corpus labels' format."""
        output: dict[str, Any] = {
            "name": self.name,
            "location": self.location,
            "years_of_experience": self.years_of_experience,
        }
        for field in TEXT_LISTS:
            output[field] = list(getattr(self, field))
        for field, (_, parts) in RECORDS.items():
            output[field] = [
                {part: getattr(r, part) for part in parts} for r in getattr(self, field)
            ]
        return output


def _nullable(kind: str) -> dict[str, Any]:
    return {"anyOf": [{"type": kind}, {"type": "null"}]}


def _object(properties: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(properties),
        "additionalProperties": False,
    }


def _record_schema(parts: Sequence[str]) -> dict[str, Any]:
    return {"type": "array", "items": _object({part: _nullable("string") for part in parts})}


PROFILE_SCHEMA: dict[str, Any] = _object(
    {
        "name": _nullable("string"),
        "emails": {"type": "array", "items": {"type": "string"}},
        "phones": {"type": "array", "items": {"type": "string"}},
        "location": _nullable("string"),
        "years_of_experience": _nullable("number"),
        "employment": _record_schema(RECORDS["employment"][1]),
        "education": _record_schema(RECORDS["education"][1]),
        "skills": {"type": "array", "items": {"type": "string"}},
        "languages": _record_schema(RECORDS["languages"][1]),
        "certifications": _record_schema(RECORDS["certifications"][1]),
    }
)


def profile_from_output(output: object) -> Profile:
    data = _exact_object(output, FIELDS, "the profile")
    years = data["years_of_experience"]
    if years is not None and (isinstance(years, bool) or not isinstance(years, int | float)):
        raise MalformedProfileError("years_of_experience is not a number")
    return Profile(
        name=_optional_text(data["name"], "name"),
        location=_optional_text(data["location"], "location"),
        years_of_experience=years,
        emails=_texts(data["emails"], "emails"),
        phones=_texts(data["phones"], "phones"),
        skills=_texts(data["skills"], "skills"),
        employment=_records(data, "employment", Employment),
        education=_records(data, "education", Education),
        languages=_records(data, "languages", Language),
        certifications=_records(data, "certifications", Certification),
    )


def _exact_object(value: object, fields: Sequence[str], what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MalformedProfileError(f"{what} is not an object")
    if missing := [field for field in fields if field not in value]:
        raise MalformedProfileError(f"{what} is missing {missing}")
    if extra := sorted(set(value) - set(fields)):
        raise MalformedProfileError(f"{what} has unexpected {extra}")
    return value


def _optional_text(value: object, field: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise MalformedProfileError(f"{field} is not text")
    return value


def _texts(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise MalformedProfileError(f"{field} is not a list of text")
    return tuple(value)


def _records[R: Record](data: Mapping[str, Any], field: str, kind: type[R]) -> tuple[R, ...]:
    value, parts = data[field], RECORDS[field][1]
    if not isinstance(value, list):
        raise MalformedProfileError(f"{field} is not a list")
    records = []
    for item in value:
        entry = _exact_object(item, parts, f"an entry of {field}")
        records.append(
            kind(**{part: _optional_text(entry[part], f"{field}.{part}") for part in parts})
        )
    return tuple(records)
