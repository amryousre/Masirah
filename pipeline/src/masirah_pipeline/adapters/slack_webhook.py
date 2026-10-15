"""Alerts posted to a Slack channel through an incoming webhook (T031).

The webhook URL is the credential: anyone holding it can post to the channel. So no error raised
here carries it, nor chains an error that does, since either would put it in the logs and in
error tracking.
"""

import httpx2

TIMEOUT = 10.0


class AlertDeliveryError(Exception):
    """Slack refused the alert or could not be reached."""


class SlackWebhook:
    def __init__(self, url: str, *, client: httpx2.Client | None = None) -> None:
        self._url = url
        self._client = client or httpx2.Client(timeout=TIMEOUT)

    def send(self, text: str) -> None:
        failure: str | None = None
        try:
            response = self._client.post(self._url, json={"text": text})
        except httpx2.HTTPError as error:
            failure = f"Slack could not be reached ({type(error).__name__})"
        else:
            if response.is_error:
                failure = f"Slack refused the alert with status {response.status_code}"
        if failure is not None:
            # Raised outside the except block, and with no cause, so the original error and the
            # URL it names stay out of every traceback.
            raise AlertDeliveryError(failure) from None
