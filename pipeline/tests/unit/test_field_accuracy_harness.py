"""The accuracy harness (T029) measures what it claims to.

The gate is only as trustworthy as its arithmetic, so these run in CI with the unit suite: a
perfect extractor scores 100 percent, nothing extracted scores only what the labels leave empty,
and each kind of mistake costs exactly the fields it should.
"""

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.accuracy.field_accuracy import (
    EXTRACTOR_VARIABLE,
    Document,
    Extraction,
    Profile,
    Unsupported,
    compare_profile,
    configured_extractor,
    evaluate,
    load_corpus,
    normalise_text,
    oracle,
    run,
    same_text,
)

CORPUS = load_corpus()


def document(name: str) -> Document:
    return next(d for d in CORPUS if d.name == name)


def score(expected: Profile, extracted: Profile) -> tuple[int, int]:
    fields = compare_profile(expected, extracted)
    return sum(f.correct for f in fields), len(fields)


PROFILE: dict[str, Any] = {
    "name": "Omar Hassan",
    "emails": ["omar@example.com"],
    "phones": ["+201000000205"],
    "location": "Cairo",
    "years_of_experience": 6,
    "employment": [
        {
            "employer": "Nile Pharma",
            "title": "Sales Executive",
            "start": "2020-02",
            "end": "present",
        },
        {
            "employer": "Delta Medical",
            "title": "Representative",
            "start": "2017-08",
            "end": "2020-01",
        },
    ],
    "education": [
        {"institution": "Cairo University", "qualification": "BSc", "start": "2012", "end": "2016"}
    ],
    "skills": ["Salesforce CRM", "Microsoft Excel"],
    "languages": [{"language": "English", "level": "Very good"}],
    "certifications": [{"name": "Professional Selling Skills", "issuer": None}],
}
# 3 scalars + 1 email + 1 phone + 2 skills + 2 jobs x 4 + 1 degree x 4 + 1 language x 2 + 1 x 2.
FIELDS = 3 + 1 + 1 + 2 + 8 + 4 + 2 + 2


def changed(**changes: Any) -> dict[str, Any]:
    profile = copy.deepcopy(PROFILE)
    profile.update(changes)
    return profile


class TestTheWholeCorpus:
    def test_a_perfect_extractor_opens_the_native_gate(self) -> None:
        report = run(oracle)
        assert report.native.accuracy == 1.0
        assert report.native_passes
        everything = report.group(captured=False, real_only=False) + report.group(
            captured=True, real_only=False
        )
        assert everything.correct == everything.total > 0

    def test_the_captured_gate_stays_closed_without_real_scans(self) -> None:
        """SC-003 cannot pass on synthetic or simulated captures alone, however well they score."""
        without_real_captures = [d for d in CORPUS if not (d.captured and d.real)]
        assert any(d.captured for d in without_real_captures)
        report = run(oracle, without_real_captures)
        assert report.captured.accuracy is None
        assert not report.captured_passes
        assert "not measured: no real documents yet" in report.render()

    def test_a_real_capture_is_measured_for_the_captured_gate(self) -> None:
        real_captures = [d for d in CORPUS if d.captured and d.real]
        assert real_captures, "the corpus holds at least one real scan or photo"
        report = run(oracle, real_captures)
        assert report.captured.accuracy == 1.0
        assert report.captured_passes

    def test_only_real_documents_decide_the_gate(self) -> None:
        def wrong_unless_real(path: Path) -> Extraction:
            labelled = oracle(path)
            return labelled if document(path.stem).real else {}

        report = run(wrong_unless_real)
        assert report.native.accuracy == 1.0
        whole = report.group(captured=False, real_only=False)
        assert whole.accuracy is not None
        assert whole.accuracy < 1.0

    def test_extracting_nothing_scores_only_what_the_labels_leave_empty(self) -> None:
        report = run(lambda _: {})
        assert report.native.accuracy is not None
        assert report.native.accuracy < 0.1
        assert not report.native_passes

    def test_an_extractor_that_fails_is_measured_not_fatal(self) -> None:
        def broken(_: Path) -> Extraction:
            raise RuntimeError("model timed out")

        report = run(broken)
        assert report.native.correct == 0
        assert report.native.total > 0
        assert all(r.error == "RuntimeError: model timed out" for r in report.results)
        assert "RuntimeError: model timed out" in report.render()


class TestLanguage:
    def test_an_unsupported_document_holds_no_fields(self) -> None:
        french = document("syn-fr-native-01")
        assert not french.supported
        result = evaluate(french, Unsupported())
        assert result.flagged_unsupported
        assert result.tally.total == 0

    def test_a_supported_cv_turned_away_loses_every_field(self) -> None:
        result = evaluate(document("en-native-01"), Unsupported())
        assert result.tally.correct == 0
        assert result.tally.total > 0

    def test_the_report_names_a_missed_unsupported_document(self) -> None:
        report = run(lambda _: {})
        assert "syn-fr-native-01" in report.render()
        assert "NOT flagged unsupported" in report.render()


class TestFields:
    def test_a_perfect_profile(self) -> None:
        assert score(PROFILE, PROFILE) == (FIELDS, FIELDS)

    def test_a_wrong_name_costs_one_field(self) -> None:
        assert score(PROFILE, changed(name="Karim Fouad")) == (FIELDS - 1, FIELDS)

    def test_an_invented_value_for_an_empty_label_is_wrong(self) -> None:
        expected = changed(location=None)
        assert score(expected, changed(location=None)) == (FIELDS, FIELDS)
        assert score(expected, changed(location="Giza")) == (FIELDS - 1, FIELDS)

    def test_a_missed_skill_and_an_invented_one_each_cost_a_field(self) -> None:
        extracted = changed(skills=["Salesforce CRM", "Leadership"])
        assert score(PROFILE, extracted) == (FIELDS - 1, FIELDS + 1)

    def test_jobs_are_paired_whatever_their_order(self) -> None:
        extracted = changed(employment=list(reversed(PROFILE["employment"])))
        assert score(PROFILE, extracted) == (FIELDS, FIELDS)

    def test_a_wrong_date_costs_one_field_of_its_job(self) -> None:
        jobs = copy.deepcopy(PROFILE["employment"])
        jobs[1]["end"] = "2019-12"
        assert score(PROFILE, changed(employment=jobs)) == (FIELDS - 1, FIELDS)

    def test_an_invented_job_costs_all_four_of_its_fields(self) -> None:
        extra = {"employer": "Acme", "title": "Manager", "start": "2015", "end": "2016"}
        extracted = changed(employment=[*PROFILE["employment"], extra])
        assert score(PROFILE, extracted) == (FIELDS, FIELDS + 4)

    def test_a_missed_job_costs_all_four_of_its_fields(self) -> None:
        extracted = changed(employment=PROFILE["employment"][:1])
        assert score(PROFILE, extracted) == (FIELDS - 4, FIELDS)

    def test_records_are_not_paired_by_what_both_leave_empty(self) -> None:
        """A missed certificate and an invented one, neither with an issuer, stay two mistakes."""
        labelled = [{"name": "PMP", "issuer": None}, {"name": "ITIL Foundation", "issuer": None}]
        found = [{"name": "PMP", "issuer": None}, {"name": "Six Sigma Green Belt", "issuer": None}]
        expected = changed(certifications=labelled)
        # PMP pairs (2 right); ITIL is missed and Six Sigma invented (2 wrong each). Paired on
        # their empty issuers instead, they would score 24 of 25.
        assert score(expected, changed(certifications=found)) == (FIELDS, FIELDS + 4)

    def test_a_year_is_not_a_month(self) -> None:
        """A CV giving only a year must not come back with an invented month."""
        degree = [{**PROFILE["education"][0], "start": "2012-09"}]
        assert score(PROFILE, changed(education=degree)) == (FIELDS - 1, FIELDS)

    def test_years_of_experience_compare_as_numbers(self) -> None:
        assert score(PROFILE, changed(years_of_experience="6")) == (FIELDS, FIELDS)
        assert score(PROFILE, changed(years_of_experience=6.5)) == (FIELDS - 1, FIELDS)

    def test_phones_are_compared_digit_for_digit(self) -> None:
        assert score(PROFILE, changed(phones=["+20 100 000 0205"])) == (FIELDS, FIELDS)
        assert score(PROFILE, changed(phones=["+٢٠١٠٠٠٠٠٠٢٠٥"])) == (FIELDS, FIELDS)
        # Local format is not the labelled E.164 form: normalising it is extraction's job.
        assert score(PROFILE, changed(phones=["01000000205"]))[0] == FIELDS - 1

    def test_missing_and_malformed_output_is_wrong_not_a_crash(self) -> None:
        correct, total = score(PROFILE, {"name": 7, "skills": "Excel", "employment": [None]})
        assert correct == 0
        assert total >= FIELDS


class TestText:
    @pytest.mark.parametrize(
        ("written", "extracted"),
        [
            ("Microsoft Excel", "microsoft  excel"),
            ("Sofware Developer", "Software Developer"),  # a corrected typo
            ("Nile Pharma Academy", "Nile Pharrna Academy"),  # an OCR slip
            ("جامعة القاهرة", "جامعه القاهره"),  # ta marbuta written as ha
            ("أحمد", "احمد"),  # hamza on alef
            ("مُحَمَّد", "محمد"),  # diacritics
            ("مـحـمـد", "محمد"),  # tatweel
            ("ﻣﺤﻤﺪ", "محمد"),  # presentation forms, as PDF text layers store them
            ("2019", "٢٠١٩"),  # Arabic-Indic digits
            ("(Cairo)", "Cairo"),
        ],
    )
    def test_the_same_value_written_differently(self, written: str, extracted: str) -> None:
        assert same_text(written, extracted)

    @pytest.mark.parametrize(
        ("written", "extracted"),
        [
            ("AHBS", "AHBC"),  # short values must match exactly
            ("C++", "C#"),
            ("Java", "JavaScript"),
            ("Sales Executive", "Sales Manager"),
            ("محمد", "دمحم"),  # reversed visual order is extraction's to repair
            ("Cairo", None),
        ],
    )
    def test_different_values(self, written: str, extracted: str | None) -> None:
        assert not same_text(written, extracted)

    def test_normalising_keeps_inner_punctuation(self) -> None:
        assert normalise_text("  C++ / .NET  ") == "c++ / .net"


class TestConfiguration:
    def test_nothing_named_means_no_extractor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(EXTRACTOR_VARIABLE, raising=False)
        assert configured_extractor() is None

    def test_the_named_extractor_is_loaded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(EXTRACTOR_VARIABLE, "tests.accuracy.field_accuracy:oracle")
        assert configured_extractor() is oracle

    def test_a_name_without_a_function_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(EXTRACTOR_VARIABLE, "tests.accuracy.field_accuracy")
        with pytest.raises(ValueError, match=r"package\.module:function"):
            configured_extractor()
