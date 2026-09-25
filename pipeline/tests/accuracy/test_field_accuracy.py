"""The accuracy gate (T029): SC-002 and SC-003 measured on the labelled corpus.

A gate, not a test. Phase 1 does not exit until both pass on real documents. Run it on its own,
naming the extractor to measure:

    MASIRAH_EXTRACTOR=package.module:function uv run pytest tests/accuracy

The full report, per group, per field and per document, prints at the end of the run.
`tests.accuracy.field_accuracy:oracle` answers with the labels themselves, which checks the
harness rather than extraction.
"""

import pytest

from tests.accuracy import report_holder
from tests.accuracy.field_accuracy import (
    CAPTURED_GATE,
    EXTRACTOR_VARIABLE,
    NATIVE_GATE,
    Report,
    configured_extractor,
    run,
)


@pytest.fixture(scope="module")
def report() -> Report:
    extractor = configured_extractor()
    if extractor is None:
        pytest.fail(
            f"No extractor to measure. Set {EXTRACTOR_VARIABLE} to package.module:function; "
            "extraction itself arrives with T048 to T052."
        )
    measured = run(extractor)
    report_holder.REPORTS.append(measured.render())
    return measured


def test_native_pdfs_meet_sc002(report: Report) -> None:
    assert report.native.accuracy is not None, "no real native PDFs in the corpus"
    assert report.native_passes, (
        f"native PDF field accuracy is {report.native.describe()}, below {NATIVE_GATE:.0%}"
    )


def test_scanned_and_photographed_cvs_meet_sc003(report: Report) -> None:
    assert report.captured.accuracy is not None, (
        "no real scanned or photographed CVs in the corpus yet, so SC-003 cannot be measured"
    )
    assert report.captured_passes, (
        f"scanned and photographed field accuracy is {report.captured.describe()}, "
        f"below {CAPTURED_GATE:.0%}"
    )
