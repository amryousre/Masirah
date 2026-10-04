"""The structured profile (T045): the one output schema every provider must satisfy.

The schema has to be accepted by both providers' strict structured output, so it uses only what
both support: every property required, nothing extra allowed, and an empty value written as null.
A model's output is then read into the profile, and anything that does not fit is refused rather
than guessed at (AI-01).
"""

import json
from pathlib import Path
from typing import Any

import pytest

from masirah_pipeline.domain.profile import (
    PROFILE_SCHEMA,
    MalformedProfileError,
    Profile,
    profile_from_output,
)

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"
LABELLED = sorted(CORPUS.glob("*.json"))


def labels(path: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


def objects(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Every object schema inside the profile schema, the profile itself included."""
    found = [schema] if schema.get("type") == "object" else []
    for value in schema.values():
        if isinstance(value, dict):
            found += objects(value)
        elif isinstance(value, list):
            found += [o for item in value if isinstance(item, dict) for o in objects(item)]
    return found


class TestSchema:
    def test_every_object_requires_all_its_properties_and_allows_no_others(self) -> None:
        """Strict structured output on both providers needs exactly this."""
        for schema in objects(PROFILE_SCHEMA):
            assert schema["additionalProperties"] is False
            assert sorted(schema["required"]) == sorted(schema["properties"])

    def test_it_uses_nothing_either_provider_rejects(self) -> None:
        unsupported = {"minimum", "maximum", "minLength", "maxLength", "pattern", "format"}
        text = json.dumps(PROFILE_SCHEMA)
        assert not [word for word in unsupported if f'"{word}"' in text]

    def test_it_describes_the_fields_the_corpus_labels(self) -> None:
        labelled = labels(LABELLED[0])["profile"]
        assert sorted(PROFILE_SCHEMA["properties"]) == sorted(labelled)


class TestReadingOutput:
    @pytest.mark.parametrize("path", LABELLED, ids=lambda path: path.stem)
    def test_every_corpus_label_reads_and_writes_back_unchanged(self, path: Path) -> None:
        """The corpus labels are valid model output, so the format the gate scores is this one."""
        labelled = labels(path)["profile"]
        assert profile_from_output(labelled).as_dict() == labelled

    def test_a_profile_keeps_its_values(self) -> None:
        profile = profile_from_output(labels(CORPUS / "en-native-03.json")["profile"])
        assert isinstance(profile, Profile)
        assert profile.name == "Youssef Samir Nabil"
        assert profile.location is None
        assert profile.employment[0].employer == "AHBS"
        assert profile.employment[0].end == "present"
        assert profile.certifications[0].issuer is None

    @pytest.mark.parametrize(
        "change",
        [
            {"name": 7},
            {"emails": "a@example.com"},
            {"skills": ["SQL", 3]},
            {"years_of_experience": "six"},
            {"years_of_experience": True},
            {"employment": [{"employer": "Acme", "title": "Clerk", "start": "2020"}]},
            {
                "employment": [
                    {"employer": "Acme", "title": "Clerk", "start": None, "end": None, "x": 1}
                ]
            },
            {"languages": [None]},
            {"unexpected": 1},
        ],
        ids=lambda change: next(iter(change)),
    )
    def test_output_that_does_not_fit_is_refused(self, change: dict[str, Any]) -> None:
        output = labels(CORPUS / "en-native-01.json")["profile"] | change
        with pytest.raises(MalformedProfileError):
            profile_from_output(output)

    def test_output_missing_a_field_is_refused(self) -> None:
        output = labels(CORPUS / "en-native-01.json")["profile"]
        del output["location"]
        with pytest.raises(MalformedProfileError, match="location"):
            profile_from_output(output)

    def test_output_that_is_not_an_object_is_refused(self) -> None:
        with pytest.raises(MalformedProfileError):
            profile_from_output(["not", "a", "profile"])
