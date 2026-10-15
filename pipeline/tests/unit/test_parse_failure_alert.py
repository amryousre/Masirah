"""Alerting when the parse failure rate exceeds five percent (NFR-14, T031).

Every hour the worker counts the CV files that settled in the past hour and how many of them
failed. Above five percent it logs an error, which error tracking picks up, and posts to Slack
when a webhook is configured. Too few files say nothing about a rate, so a quiet hour with one
failure out of three does not wake anyone.
"""

import json
import logging

import httpx2
import pytest

from masirah_pipeline.adapters.slack_webhook import AlertDeliveryError, SlackWebhook
from masirah_pipeline.domain.parse_failures import (
    MINIMUM_SETTLED,
    ParseOutcomes,
    alert_for,
)
from masirah_pipeline.jobs.parse_failures import (
    KIND,
    QUIET_SECONDS,
    WINDOW_SECONDS,
    check_parse_failures,
)

WEBHOOK = "https://hooks.slack.com/services/T000/B000/secret-part"


def test_five_percent_exactly_is_not_above_the_threshold() -> None:
    assert alert_for(ParseOutcomes(settled=100, failed=5, organisations=1)) is None


def test_above_five_percent_alerts_with_the_figures() -> None:
    alert = alert_for(ParseOutcomes(settled=100, failed=6, organisations=2))
    assert alert is not None
    assert "6 of 100" in alert
    assert "6.0%" in alert
    assert "2 organisations" in alert


def test_too_few_files_say_nothing_about_a_rate() -> None:
    few = MINIMUM_SETTLED - 1
    assert alert_for(ParseOutcomes(settled=few, failed=few, organisations=1)) is None


def test_the_minimum_is_enough() -> None:
    assert alert_for(ParseOutcomes(settled=MINIMUM_SETTLED, failed=1, organisations=1)) is not None


def test_one_organisation_is_named_in_the_singular() -> None:
    alert = alert_for(ParseOutcomes(settled=20, failed=20, organisations=1))
    assert alert is not None
    assert "1 organisation)" in alert


def granted(kind: str, quiet_seconds: int) -> bool:
    return True


def refused(kind: str, quiet_seconds: int) -> bool:
    return False


class Recorded:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> None:
        self.sent.append(text)


def test_an_alert_is_logged_as_an_error_and_sent(caplog: pytest.LogCaptureFixture) -> None:
    windows: list[int] = []

    def read(window_seconds: int) -> ParseOutcomes:
        windows.append(window_seconds)
        return ParseOutcomes(settled=40, failed=10, organisations=3)

    claims: list[tuple[str, int]] = []

    def claim(kind: str, quiet_seconds: int) -> bool:
        claims.append((kind, quiet_seconds))
        return True

    alerts = Recorded()
    with caplog.at_level(logging.ERROR):
        assert check_parse_failures(read, claim, alerts) == 1
    assert windows == [WINDOW_SECONDS]
    assert claims == [(KIND, QUIET_SECONDS)]
    assert len(alerts.sent) == 1
    assert alerts.sent[0] in caplog.text


def test_a_healthy_hour_sends_nothing(caplog: pytest.LogCaptureFixture) -> None:
    alerts = Recorded()
    with caplog.at_level(logging.ERROR):
        assert check_parse_failures(lambda _: ParseOutcomes(50, 0, 0), granted, alerts) == 0
    assert alerts.sent == []
    assert caplog.records == []


def test_without_slack_the_alert_is_still_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        assert check_parse_failures(lambda _: ParseOutcomes(40, 10, 1), granted, None) == 1
    assert "parse failure rate" in caplog.text


def test_another_worker_has_already_alerted(caplog: pytest.LogCaptureFixture) -> None:
    """The claim went to another worker, or to this one before a restart, within the hour."""
    alerts = Recorded()
    with caplog.at_level(logging.ERROR):
        assert check_parse_failures(lambda _: ParseOutcomes(40, 10, 1), refused, alerts) == 0
    assert alerts.sent == []
    assert caplog.records == []


def client_answering(status: int, seen: list[httpx2.Request]) -> httpx2.Client:
    def answer(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(status)

    return httpx2.Client(transport=httpx2.MockTransport(answer))


def test_slack_receives_the_text() -> None:
    seen: list[httpx2.Request] = []
    SlackWebhook(WEBHOOK, client=client_answering(200, seen)).send("parse failure rate 7%")
    assert len(seen) == 1
    assert str(seen[0].url) == WEBHOOK
    assert json.loads(seen[0].content) == {"text": "parse failure rate 7%"}


@pytest.mark.parametrize("status", [400, 404, 500])
def test_a_refused_post_fails_without_revealing_the_webhook(status: int) -> None:
    """The webhook URL is the credential: an error carrying it would put it in the logs and in
    error tracking."""
    webhook = SlackWebhook(WEBHOOK, client=client_answering(status, []))
    with pytest.raises(AlertDeliveryError) as raised:
        webhook.send("text")
    assert "secret-part" not in str(raised.value)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__


def test_an_unreachable_slack_fails_without_revealing_the_webhook() -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(f"cannot reach {request.url}")

    webhook = SlackWebhook(WEBHOOK, client=httpx2.Client(transport=httpx2.MockTransport(refuse)))
    with pytest.raises(AlertDeliveryError) as raised:
        webhook.send("text")
    assert "secret-part" not in str(raised.value)
    assert raised.value.__suppress_context__
