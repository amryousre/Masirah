"""The queue message contract (specs/001-phase1-core-screening/contracts/queue-message.md).

The only runtime coupling between the web application and this worker. Parsing is strict: a
message is refused rather than guessed at, and an unrecognised schema_version is refused with its
own error so the worker can leave the message in the queue and raise an alert.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast
from uuid import UUID

SCHEMA_VERSION = 1
CV_PROCESSING = "cv_processing"
CV_RESCORING = "cv_rescoring"

Locale = Literal["ar", "en"]

_SHA256 = re.compile("[0-9a-f]{64}")
_FIELDS = {
    CV_PROCESSING: {
        "schema_version",
        "job_type",
        "organisation_id",
        "cv_file_id",
        "job_id",
        "content_hash",
        "storage_path",
        "locale",
        "enqueued_at",
    },
    CV_RESCORING: {
        "schema_version",
        "job_type",
        "organisation_id",
        "application_id",
        "weights_hash",
        "locale",
        "enqueued_at",
    },
}


class RejectedMessageError(ValueError):
    """A message the worker must not process. It stays in the queue and raises an alert."""


class UnsupportedSchemaVersionError(RejectedMessageError):
    def __init__(self, version: int) -> None:
        super().__init__(f"schema_version {version} is not supported (this worker reads 1)")
        self.version = version


class MalformedMessageError(RejectedMessageError):
    pass


@dataclass(frozen=True)
class CvProcessingMessage:
    organisation_id: UUID
    cv_file_id: UUID
    job_id: UUID | None
    content_hash: str
    storage_path: str
    locale: Locale
    enqueued_at: datetime


@dataclass(frozen=True)
class CvRescoringMessage:
    organisation_id: UUID
    application_id: UUID
    weights_hash: str
    locale: Locale
    enqueued_at: datetime


QueueMessage = CvProcessingMessage | CvRescoringMessage


def parse_queue_message(raw: object) -> QueueMessage:
    if not isinstance(raw, dict):
        raise MalformedMessageError("message is not a JSON object")
    version = raw.get("schema_version")
    if type(version) is not int:
        raise MalformedMessageError("schema_version is missing or not an integer")
    if version != SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(version)
    job_type = raw.get("job_type")
    if job_type == CV_PROCESSING:
        return _cv_processing(_exact_fields(raw, CV_PROCESSING))
    if job_type == CV_RESCORING:
        return _cv_rescoring(_exact_fields(raw, CV_RESCORING))
    raise MalformedMessageError(f"job_type {job_type!r} is not in the contract")


def _exact_fields(raw: dict[Any, Any], job_type: str) -> dict[Any, Any]:
    expected = _FIELDS[job_type]
    if missing := expected - raw.keys():
        raise MalformedMessageError(f"{job_type} message is missing {sorted(missing)}")
    if unexpected := raw.keys() - expected:
        raise MalformedMessageError(f"{job_type} message has unexpected {sorted(unexpected)}")
    return raw


def _cv_processing(raw: dict[Any, Any]) -> CvProcessingMessage:
    organisation_id = _uuid(raw, "organisation_id")
    cv_file_id = _uuid(raw, "cv_file_id")
    storage_path = _text(raw, "storage_path")
    folder = f"organisations/{organisation_id}/cv/{cv_file_id}/"
    if not _is_file_inside(storage_path, folder):
        raise MalformedMessageError(f"storage_path is not a file inside {folder}")
    return CvProcessingMessage(
        organisation_id=organisation_id,
        cv_file_id=cv_file_id,
        job_id=None if raw["job_id"] is None else _uuid(raw, "job_id"),
        content_hash=_sha256(raw, "content_hash"),
        storage_path=storage_path,
        locale=_locale(raw),
        enqueued_at=_timestamp(raw),
    )


def _cv_rescoring(raw: dict[Any, Any]) -> CvRescoringMessage:
    return CvRescoringMessage(
        organisation_id=_uuid(raw, "organisation_id"),
        application_id=_uuid(raw, "application_id"),
        weights_hash=_sha256(raw, "weights_hash"),
        locale=_locale(raw),
        enqueued_at=_timestamp(raw),
    )


def _is_file_inside(path: str, folder: str) -> bool:
    """Every segment below the folder must name something: no empty, "." or ".." segment."""
    if not path.startswith(folder) or "\\" in path:
        return False
    return all(segment not in ("", ".", "..") for segment in path[len(folder) :].split("/"))


def _text(raw: dict[Any, Any], field: str) -> str:
    value = raw[field]
    if not isinstance(value, str):
        raise MalformedMessageError(f"{field} is not a string")
    return value


def _uuid(raw: dict[Any, Any], field: str) -> UUID:
    value = _text(raw, field)
    try:
        parsed = UUID(value)
    except ValueError as error:
        raise MalformedMessageError(f"{field} is not a UUID") from error
    if str(parsed) != value:
        raise MalformedMessageError(f"{field} is not a canonical lowercase UUID")
    return parsed


def _sha256(raw: dict[Any, Any], field: str) -> str:
    value = _text(raw, field)
    if not _SHA256.fullmatch(value):
        raise MalformedMessageError(f"{field} is not a lowercase SHA-256 hex digest")
    return value


def _locale(raw: dict[Any, Any]) -> Locale:
    value = _text(raw, "locale")
    if value not in ("ar", "en"):
        raise MalformedMessageError(f"locale {value!r} is not supported")
    return cast(Locale, value)


def _timestamp(raw: dict[Any, Any]) -> datetime:
    value = _text(raw, "enqueued_at")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise MalformedMessageError("enqueued_at is not an ISO 8601 timestamp") from error
    if parsed.tzinfo is None:
        raise MalformedMessageError("enqueued_at has no time zone")
    return parsed
