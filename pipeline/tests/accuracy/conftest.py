import pytest

from tests.accuracy.extractors import spend_summary
from tests.accuracy.report_holder import REPORTS


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """The accuracy report, whatever the gate's verdict: a closed gate is read from its numbers."""
    for report in REPORTS:
        terminalreporter.section("accuracy report")
        terminalreporter.write_line(report)
    if spend := spend_summary():
        terminalreporter.write_line(spend)
