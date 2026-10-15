"""Structured logs and error tracking for the worker (NFR-14, T031).

Every log line is one JSON object on stdout, which a host's log search can filter by field. While
a CV is being processed, each line carries its organisation and file, so one tenant's work can be
followed and counted.

With SENTRY_DSN set, errors and error logs also go to Sentry (EU region), named by
SENTRY_ENVIRONMENT. Nothing a candidate wrote may go with them: local variables are never
captured, and scrub removes the request, the user and any frame variables that get through. The
log messages themselves carry identifiers and reasons, never a CV's text.
"""

import json
import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

import sentry_sdk

from masirah_pipeline.work_context import current_work

Event = dict[str, Any]

# The HTTP client logs every request with its full URL at INFO. The Slack webhook's URL is its
# credential, so those records must never be made: not on stdout, and not as Sentry breadcrumbs.
QUIETED = ("httpx2", "httpcore2")


def _tenant() -> dict[str, str]:
    work = current_work()
    if work is None:
        return {}
    organisation_id, cv_file_id = work
    return {"organisation_id": str(organisation_id), "cv_file_id": str(cv_file_id)}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line: dict[str, str] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_tenant(),
        }
        if record.exc_info:
            line["exception"] = self.formatException(record.exc_info)
        return json.dumps(line, ensure_ascii=False)


def scrub(event: Event, hint: Mapping[str, Any]) -> Event | None:
    """Sentry's before_send: drops whatever could carry a candidate's words, and tags the tenant
    being processed."""
    event.pop("user", None)
    event.pop("request", None)
    for value in event.get("exception", {}).get("values", []):
        for frame in (value.get("stacktrace") or {}).get("frames", []):
            frame.pop("vars", None)
    tenant = _tenant()
    if tenant:
        event["tags"] = {**event.get("tags", {}), **tenant}
    return event


def configure(
    environment: Mapping[str, str], *, init: Callable[..., object] = sentry_sdk.init
) -> bool:
    """Sets up structured logging, and Sentry when SENTRY_DSN is set; returns whether it was."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    for name in QUIETED:
        logging.getLogger(name).setLevel(logging.WARNING)
    dsn = environment.get("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    init(
        dsn=dsn,
        environment=environment.get("SENTRY_ENVIRONMENT", "").strip() or "production",
        send_default_pii=False,
        include_local_variables=False,
        # Errors only: tracing would send every model call's timings and adds nothing NFR-14 asks.
        traces_sample_rate=0,
        before_send=scrub,
    )
    return True
