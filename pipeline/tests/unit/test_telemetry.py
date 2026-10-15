"""Structured logs and error tracking for the worker (NFR-14, T031).

Every log line is one JSON object, carrying the organisation and CV file being processed when
there is one, so a host's log search can follow one tenant's work. Errors go to Sentry when
SENTRY_DSN is set, and nothing a candidate wrote may go with them: no local variables, no
request, no user, and only the identifiers the logs carry.
"""

import json
import logging
import sys
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from masirah_pipeline.adapters.telemetry import JsonFormatter, configure, scrub
from masirah_pipeline.metering import spending_for

ORGANISATION = uuid.UUID("11111111-1111-4111-8111-111111111111")
CV_FILE = uuid.UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture(autouse=True)
def root_logging_restored() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


def line_for(message: str, *args: object, exc: bool = False) -> dict[str, Any]:
    record = logging.LogRecord("masirah.worker", logging.ERROR, __file__, 1, message, args, None)
    if exc:
        try:
            raise ValueError("boom")
        except ValueError:
            record.exc_info = sys.exc_info()
    parsed: dict[str, Any] = json.loads(JsonFormatter().format(record))
    return parsed


def test_a_line_is_one_json_object() -> None:
    line = line_for("CV file %s failed: %s", "abc", "unreadable")
    assert line["level"] == "ERROR"
    assert line["logger"] == "masirah.worker"
    assert line["message"] == "CV file abc failed: unreadable"
    assert "time" in line
    assert "organisation_id" not in line


def test_arabic_stays_readable() -> None:
    formatted = JsonFormatter().format(
        logging.LogRecord("x", logging.INFO, __file__, 1, "ملف", None, None)
    )
    assert "ملف" in formatted
    assert "\n" not in formatted


def test_the_tenant_being_processed_is_on_every_line() -> None:
    with spending_for(ORGANISATION, CV_FILE):
        line = line_for("calling the model")
    assert line["organisation_id"] == str(ORGANISATION)
    assert line["cv_file_id"] == str(CV_FILE)


def test_an_exception_is_kept_on_the_same_line() -> None:
    line = line_for("failed", exc=True)
    assert "ValueError: boom" in line["exception"]


def test_without_a_dsn_logs_are_structured_and_nothing_is_sent() -> None:
    calls: list[dict[str, Any]] = []
    assert configure({}, init=lambda **options: calls.append(options)) is False
    assert calls == []
    root = logging.getLogger()
    assert any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers)
    assert root.level == logging.INFO


def test_with_a_dsn_sentry_starts_without_personal_data() -> None:
    calls: list[dict[str, Any]] = []
    started = configure(
        {"SENTRY_DSN": " https://key@o1.ingest.de.sentry.io/2 ", "SENTRY_ENVIRONMENT": "staging"},
        init=lambda **options: calls.append(options),
    )
    assert started is True
    [options] = calls
    assert options["dsn"] == "https://key@o1.ingest.de.sentry.io/2"
    assert options["environment"] == "staging"
    assert options["send_default_pii"] is False
    assert options["include_local_variables"] is False
    assert options["traces_sample_rate"] == 0
    assert options["before_send"] is scrub


def test_the_environment_defaults_to_production() -> None:
    calls: list[dict[str, Any]] = []
    configure(
        {"SENTRY_DSN": "https://key@o1.ingest.de.sentry.io/2"},
        init=lambda **options: calls.append(options),
    )
    assert calls[0]["environment"] == "production"


def event_with_everything() -> dict[str, Any]:
    return {
        "message": "CV file failed",
        "user": {"email": "someone@example.com"},
        "request": {"data": "body"},
        "extra": {"sys.argv": ["python"]},
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "stacktrace": {
                        "frames": [
                            {"function": "extract", "vars": {"text": "محمد، محاسب أول"}},
                            {"function": "read"},
                        ]
                    },
                }
            ]
        },
    }


def test_scrub_removes_what_could_carry_a_candidates_words() -> None:
    event = scrub(event_with_everything(), {})
    assert event is not None
    assert "user" not in event
    assert "request" not in event
    frames = event["exception"]["values"][0]["stacktrace"]["frames"]
    assert all("vars" not in frame for frame in frames)
    assert event["message"] == "CV file failed"


def test_scrub_tags_the_tenant_being_processed() -> None:
    with spending_for(ORGANISATION, CV_FILE):
        event = scrub({"message": "x"}, {})
    assert event is not None
    assert event["tags"]["organisation_id"] == str(ORGANISATION)
    assert event["tags"]["cv_file_id"] == str(CV_FILE)


def test_scrub_outside_any_work_adds_no_tenant() -> None:
    event = scrub({"message": "x", "tags": {"kept": "yes"}}, {})
    assert event is not None
    assert event["tags"] == {"kept": "yes"}
