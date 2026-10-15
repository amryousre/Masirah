"""The hourly parse failure check (NFR-14, T031).

The alert is logged as an error first, so error tracking has it even when Slack is not configured
or cannot be reached, and then posted to Slack.
"""

import logging

from masirah_pipeline.domain.parse_failures import alert_for
from masirah_pipeline.ports.alerts import Alerts, ParseOutcomeSource

log = logging.getLogger(__name__)

WINDOW_SECONDS = 60 * 60


def check_parse_failures(read: ParseOutcomeSource, alerts: Alerts | None) -> int:
    """Alerts when the past hour's parse failure rate is above the threshold; returns the number
    of alerts raised, 0 or 1."""
    alert = alert_for(read(WINDOW_SECONDS))
    if alert is None:
        return 0
    log.error(alert)
    if alerts is not None:
        alerts.send(alert)
    return 1
