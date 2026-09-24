"""The queue message contract, from the consumer's side (T033, contracts/queue-message.md).

The examples file is shared with the web tests, so producer and consumer are held to one
definition. An unrecognised schema_version must be refused rather than guessed at, so the
worker can leave the message in the queue and raise an alert.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from masirah_pipeline.ports.queue_message import (
    CvProcessingMessage,
    CvRescoringMessage,
    MalformedMessageError,
    RejectedMessageError,
    UnsupportedSchemaVersionError,
    parse_queue_message,
)

EXAMPLES_PATH = (
    Path(__file__).resolve().parents[3]
    / "specs/001-phase1-core-screening/contracts/queue-message.examples.json"
)
EXAMPLES: dict[str, list[dict[str, Any]]] = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
ENQUEUED_AT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def examples(group: str) -> list[Any]:
    return [pytest.param(e["message"], id=e["name"]) for e in EXAMPLES[group]]


def test_cv_processing_message_parses_into_typed_fields() -> None:
    raw = EXAMPLES["valid"][0]["message"]
    message = parse_queue_message(raw)
    assert message == CvProcessingMessage(
        organisation_id=UUID(raw["organisation_id"]),
        cv_file_id=UUID(raw["cv_file_id"]),
        job_id=UUID(raw["job_id"]),
        content_hash=raw["content_hash"],
        storage_path=raw["storage_path"],
        locale="ar",
        enqueued_at=ENQUEUED_AT,
    )


def test_cv_processing_without_a_job_parses_with_no_job() -> None:
    message = parse_queue_message(EXAMPLES["valid"][1]["message"])
    assert isinstance(message, CvProcessingMessage)
    assert message.job_id is None


def test_cv_rescoring_message_parses_into_typed_fields() -> None:
    raw = EXAMPLES["valid"][2]["message"]
    assert parse_queue_message(raw) == CvRescoringMessage(
        organisation_id=UUID(raw["organisation_id"]),
        application_id=UUID(raw["application_id"]),
        weights_hash=raw["weights_hash"],
        locale="ar",
        enqueued_at=ENQUEUED_AT,
    )


@pytest.mark.parametrize("raw", examples("valid"))
def test_every_valid_example_parses(raw: Any) -> None:
    parse_queue_message(raw)


@pytest.mark.parametrize("raw", examples("unsupported_version"))
def test_an_unrecognised_schema_version_is_refused_not_guessed(raw: Any) -> None:
    with pytest.raises(UnsupportedSchemaVersionError) as refused:
        parse_queue_message(raw)
    assert refused.value.version == raw["schema_version"]
    assert not isinstance(refused.value, MalformedMessageError)


@pytest.mark.parametrize("raw", examples("malformed"))
def test_malformed_messages_are_refused(raw: Any) -> None:
    with pytest.raises(MalformedMessageError):
        parse_queue_message(raw)


def test_every_refusal_shares_one_type_the_worker_can_catch() -> None:
    assert issubclass(UnsupportedSchemaVersionError, RejectedMessageError)
    assert issubclass(MalformedMessageError, RejectedMessageError)
