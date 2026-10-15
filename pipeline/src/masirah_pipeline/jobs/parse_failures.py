"""The hourly parse failure check (NFR-14, T031).

The alert is logged as an error first, so error tracking has it even when Slack is not configured
or cannot be reached, and then posted to Slack. Only the worker that claims it sends it, once per
QUIET_SECONDS, so several workers, or one restarted, do not repeat it.
"""

import logging

from masirah_pipeline.domain.parse_failures import alert_for
from masirah_pipeline.ports.alerts import AlertClaim, Alerts, ParseOutcomeSource

log = logging.getLogger(__name__)

WINDOW_SECONDS = 60 * 60
QUIET_SECONDS = 60 * 60
KIND = "parse_failures"


def check_parse_failures(read: ParseOutcomeSource, claim: AlertClaim, alerts: Alerts | None) -> int:
    """Alerts when the past hour's parse failure rate is above the threshold and no worker has
    alerted within the quiet period; returns the number of alerts raised, 0 or 1."""
    alert = alert_for(read(WINDOW_SECONDS))
    if alert is None or not claim(KIND, QUIET_SECONDS):
        return 0
    log.error(alert)
    if alerts is not None:
        alerts.send(alert)
    return 1
