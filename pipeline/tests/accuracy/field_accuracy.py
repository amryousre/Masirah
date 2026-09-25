"""The accuracy harness (T029): how well an extractor reads the labelled CV corpus.

SC-002 and SC-003 require key fields to be extracted correctly from 95 percent of native PDF CVs
and 85 percent of scanned and photographed ones. This module turns that into a number. It runs an
extractor over every corpus document, compares each field with the labels beside it and reports
field accuracy per group, for real documents alone and for the whole corpus. Only real documents
(`origin` real, `simulated` false) decide the gate.

What counts as one field, and when a field is correct, is written up in
`tests/fixtures/cvs/README.md` under "How extraction is scored". In short: every labelled value is
one field, lists are matched item by item so that a missed item and an invented one both count
against the extractor, and text is compared after folding case, spacing, Arabic letter variants,
diacritics and digits, with a small allowance for spelling slips.

An extractor is any function from a document path to either a profile in the labels' format or
`Unsupported`. The harness knows nothing about how extraction works, so the same measurement holds
whether extraction is PyMuPDF, a vision model or both.
"""

import importlib
import json
import os
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, cast

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"

# SC-002 and SC-003.
NATIVE_GATE = 0.95
CAPTURED_GATE = 0.85

# How close two normalised strings must be to count as the same, as difflib's ratio. At 0.9 a
# ten-letter value may differ by one letter: an OCR slip or a corrected typo passes, a different
# word does not. Short values therefore have to match exactly.
SIMILARITY = 0.9

# The environment variable naming the extractor to measure, as "package.module:function".
EXTRACTOR_VARIABLE = "MASIRAH_EXTRACTOR"


@dataclass(frozen=True)
class Unsupported:
    """An extractor's answer for a document in a language version 1.0 does not support."""


Profile = Mapping[str, Any]
Extraction = Profile | Unsupported
Extractor = Callable[[Path], Extraction]


@dataclass(frozen=True)
class Document:
    """A corpus document and its labels."""

    name: str
    path: Path
    capture: str
    language: str
    layout: str
    origin: str
    simulated: bool
    expected: str
    profile: Profile

    @property
    def real(self) -> bool:
        """Only these decide the gate: a real CV, scanned or photographed for real if at all."""
        return self.origin == "real" and not self.simulated

    @property
    def captured(self) -> bool:
        """Scanned or photographed, so measured against SC-003 rather than SC-002."""
        return self.capture != "native"

    @property
    def supported(self) -> bool:
        return self.expected == "parsed"


def load_corpus(folder: Path = CORPUS) -> list[Document]:
    documents = []
    for path in sorted([*folder.glob("*.pdf"), *folder.glob("*.jpg")]):
        labels = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        about = labels["document"]
        documents.append(
            Document(
                name=path.stem,
                path=path,
                capture=about["capture"],
                language=about["language"],
                layout=about["layout"],
                origin=about["origin"],
                simulated=about["simulated"],
                expected=labels["expected"],
                profile=labels["profile"],
            )
        )
    return documents


def oracle(path: Path) -> Extraction:
    """Answers with the labels themselves: a perfect extractor, for checking the harness."""
    labels = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if labels["expected"] == "unsupported_language":
        return Unsupported()
    return cast(Profile, labels["profile"])


def configured_extractor() -> Extractor | None:
    """The extractor named by MASIRAH_EXTRACTOR, or None when nothing is named."""
    spec = os.environ.get(EXTRACTOR_VARIABLE, "").strip()
    if not spec:
        return None
    module_name, _, attribute = spec.partition(":")
    if not attribute:
        raise ValueError(f"{EXTRACTOR_VARIABLE} must look like package.module:function")
    return cast(Extractor, getattr(importlib.import_module(module_name), attribute))


# Normalisation ---------------------------------------------------------------------------------

DIGITS = {base + n: str(n) for base in (0x0660, 0x06F0) for n in range(10)}
# Arabic spelling that varies without changing the word: hamza on alef, alef maqsura for ya, ta
# marbuta for ha. Folding them is the usual first step in Arabic search and costs no precision here.
ARABIC_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})
TATWEEL = "ـ"
SPACE = re.compile(r"\s+")
# Spaces, Latin and Arabic punctuation, en and em dashes, brackets and quotation marks.
EDGE_PUNCTUATION = " .,;:،؛-\N{EN DASH}\N{EM DASH}()[]\"'“”«»"
PHONE_SEPARATORS = re.compile(r"[\s()./-]")


def normalise_text(value: str) -> str:
    """Folds what varies in how a value is written, not what it says.

    NFKC turns Arabic presentation forms, which PDF text layers often store, back into letters.
    Diacritics and tatweel are dropped, Arabic letter variants folded, digits read as ASCII, case
    folded, runs of spaces collapsed and punctuation trimmed from the ends. Punctuation inside a
    value stays, so "C++" and "C#" remain different skills.
    """
    text = unicodedata.normalize("NFKC", value)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").replace(TATWEEL, "")
    text = text.translate(ARABIC_LETTERS).translate(DIGITS).casefold()
    return SPACE.sub(" ", text).strip(EDGE_PUNCTUATION)


def same_text(expected: object, extracted: object) -> bool:
    if expected is None or extracted is None:
        return expected is None and extracted is None
    if not isinstance(expected, str) or not isinstance(extracted, str):
        return False
    left, right = normalise_text(expected), normalise_text(extracted)
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= SIMILARITY


def same_exact(expected: object, extracted: object) -> bool:
    """Dates and emails: equal after trimming and folding case, with no spelling allowance."""
    if isinstance(expected, str) and isinstance(extracted, str):
        return normalise_text(expected) == normalise_text(extracted)
    return expected == extracted


def same_phone(expected: object, extracted: object) -> bool:
    if not isinstance(expected, str) or not isinstance(extracted, str):
        return expected == extracted
    return PHONE_SEPARATORS.sub("", extracted.translate(DIGITS)) == expected


def same_number(expected: object, extracted: object) -> bool:
    if expected is None or extracted is None:
        return expected is None and extracted is None
    try:
        return float(cast(Any, expected)) == float(cast(Any, extracted))
    except (TypeError, ValueError):
        return False


# Comparison ------------------------------------------------------------------------------------

Same = Callable[[object, object], bool]


@dataclass(frozen=True)
class Field:
    """One labelled value and what the extractor gave for it."""

    name: str
    expected: object
    extracted: object
    correct: bool


# The record lists: each sub-field and how it is compared. The first two sub-fields pair an
# extracted record with a labelled one.
RECORDS: dict[str, tuple[tuple[str, Same], ...]] = {
    "employment": (
        ("employer", same_text),
        ("title", same_text),
        ("start", same_exact),
        ("end", same_exact),
    ),
    "education": (
        ("institution", same_text),
        ("qualification", same_text),
        ("start", same_exact),
        ("end", same_exact),
    ),
    "languages": (("language", same_text), ("level", same_text)),
    "certifications": (("name", same_text), ("issuer", same_text)),
}
ITEMS: dict[str, Same] = {"emails": same_exact, "phones": same_phone, "skills": same_text}
SCALARS: dict[str, Same] = {
    "name": same_text,
    "location": same_text,
    "years_of_experience": same_number,
}


def as_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def as_record(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def compare_items(
    name: str, expected: Sequence[Any], extracted: Sequence[Any], same: Same
) -> list[Field]:
    """A list of values. Each labelled value found is one correct field; each one missed, and each
    extracted value that matches no label, is one wrong field."""
    remaining = list(extracted)
    fields = []
    for value in expected:
        match = next((i for i, candidate in enumerate(remaining) if same(value, candidate)), None)
        if match is None:
            fields.append(Field(name, value, None, correct=False))
        else:
            fields.append(Field(name, value, remaining.pop(match), correct=True))
    fields.extend(Field(name, None, value, correct=False) for value in remaining)
    return fields


def compare_records(name: str, expected: Sequence[Any], extracted: Sequence[Any]) -> list[Field]:
    """A list of records, such as jobs. Records are paired by their first two sub-fields, best
    agreement first; a paired record counts each sub-field on its own, and an unpaired one, labelled
    or extracted, counts every sub-field as wrong."""
    parts = RECORDS[name]
    labelled = [as_record(record) for record in expected]
    found = [as_record(record) for record in extracted]

    def agreement(left: Mapping[str, Any], right: Mapping[str, Any]) -> int:
        return sum(same(left.get(key), right.get(key)) for key, same in parts)

    def identified(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        """The same record, by a value both actually give. Two certificates that both lack an
        issuer are not thereby one certificate."""
        return any(
            left.get(key) is not None and same(left.get(key), right.get(key))
            for key, same in parts[:2]
        )

    candidates = sorted(
        (
            (agreement(left, right), i, j)
            for i, left in enumerate(labelled)
            for j, right in enumerate(found)
            if identified(left, right)
        ),
        key=lambda pair: (-pair[0], pair[1], pair[2]),
    )
    pairs: dict[int, int] = {}
    for _, i, j in candidates:
        if i not in pairs and j not in pairs.values():
            pairs[i] = j

    fields = []
    for i, left in enumerate(labelled):
        right = found[pairs[i]] if i in pairs else {}
        for key, same in parts:
            value = right.get(key)
            correct = i in pairs and same(left.get(key), value)
            fields.append(Field(f"{name}.{key}", left.get(key), value, correct))
    for j, right in enumerate(found):
        if j not in pairs.values():
            fields.extend(Field(f"{name}.{key}", None, right.get(key), False) for key, _ in parts)
    return fields


def compare_profile(expected: Profile, extracted: Profile) -> list[Field]:
    fields = [
        Field(
            key, expected.get(key), extracted.get(key), same(expected.get(key), extracted.get(key))
        )
        for key, same in SCALARS.items()
    ]
    for key, same in ITEMS.items():
        fields += compare_items(key, as_list(expected.get(key)), as_list(extracted.get(key)), same)
    for key in RECORDS:
        fields += compare_records(key, as_list(expected.get(key)), as_list(extracted.get(key)))
    return fields


# Results ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Tally:
    correct: int = 0
    total: int = 0

    def __add__(self, other: "Tally") -> "Tally":
        return Tally(self.correct + other.correct, self.total + other.total)

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.total if self.total else None

    def describe(self) -> str:
        if self.accuracy is None:
            return "not measured"
        return f"{self.accuracy:.1%} ({self.correct}/{self.total})"


@dataclass(frozen=True)
class Result:
    """How one document went."""

    document: Document
    fields: tuple[Field, ...]
    flagged_unsupported: bool
    error: str | None = None

    @property
    def tally(self) -> Tally:
        return Tally(sum(f.correct for f in self.fields), len(self.fields))


def evaluate(document: Document, extraction: Extraction) -> Result:
    flagged = isinstance(extraction, Unsupported)
    if not document.supported:
        # Language detection has its own test (T039); an unsupported document holds no fields.
        return Result(document, (), flagged)
    if isinstance(extraction, Unsupported):
        # A supported CV turned away is a CV with nothing extracted.
        fields = compare_profile(document.profile, {})
        return Result(document, tuple(Field(f.name, f.expected, None, False) for f in fields), True)
    return Result(document, tuple(compare_profile(document.profile, extraction)), False)


def failed(document: Document, error: Exception) -> Result:
    """An extractor that raises has extracted nothing, which the gate counts, rather than a crash
    that stops the measurement."""
    fields = compare_profile(document.profile, {}) if document.supported else []
    wrong = tuple(Field(f.name, f.expected, None, False) for f in fields)
    return Result(document, wrong, False, f"{type(error).__name__}: {error}")


@dataclass(frozen=True)
class Report:
    results: tuple[Result, ...]

    def tally(self, results: Iterable[Result]) -> Tally:
        total = Tally()
        for result in results:
            total += result.tally
        return total

    def group(self, *, captured: bool, real_only: bool) -> Tally:
        return self.tally(
            r
            for r in self.results
            if r.document.supported
            and r.document.captured == captured
            and (r.document.real or not real_only)
        )

    @property
    def native(self) -> Tally:
        """SC-002, real documents only."""
        return self.group(captured=False, real_only=True)

    @property
    def captured(self) -> Tally:
        """SC-003, real documents only."""
        return self.group(captured=True, real_only=True)

    @property
    def native_passes(self) -> bool:
        return self.native.accuracy is not None and self.native.accuracy >= NATIVE_GATE

    @property
    def captured_passes(self) -> bool:
        return self.captured.accuracy is not None and self.captured.accuracy >= CAPTURED_GATE

    def by_field(self) -> dict[str, Tally]:
        tallies: dict[str, Tally] = {}
        for result in self.results:
            for f in result.fields:
                tallies[f.name] = tallies.get(f.name, Tally()) + Tally(int(f.correct), 1)
        return tallies

    def render(self) -> str:
        def count(real_only: bool, captured: bool) -> int:
            return sum(
                1
                for r in self.results
                if r.document.supported
                and r.document.captured == captured
                and (r.document.real or not real_only)
            )

        def verdict(passes: bool, tally: Tally, gate: float) -> str:
            if tally.accuracy is None:
                return "not measured: no real documents yet"
            return f"{'passes' if passes else 'fails'} (needs {gate:.0%})"

        rows = [
            ("Native PDFs (SC-002)", False, self.native_passes, NATIVE_GATE),
            ("Scanned and photographed (SC-003)", True, self.captured_passes, CAPTURED_GATE),
        ]
        lines = [
            "Field accuracy. Only real CVs, scanned or photographed for real, decide the gates.",
            "",
        ]
        for label, captured, passes, gate in rows:
            real = self.group(captured=captured, real_only=True)
            everything = self.group(captured=captured, real_only=False)
            lines.append(f"  {label}")
            lines.append(f"    real documents ({count(True, captured)}):  {real.describe()}")
            lines.append(f"    whole corpus ({count(False, captured)}):  {everything.describe()}")
            lines.append(f"    gate: {verdict(passes, real, gate)}")
        unsupported = [r for r in self.results if not r.document.supported]
        turned_away = [r for r in self.results if r.document.supported and r.flagged_unsupported]
        lines += [
            "",
            "  Language: "
            f"{sum(r.flagged_unsupported for r in unsupported)}/{len(unsupported)} unsupported "
            f"documents flagged, {len(turned_away)} supported documents wrongly flagged",
            "",
            "  By field, whole corpus:",
        ]
        width = max((len(name) for name in self.by_field()), default=0)
        lines += [
            f"    {name:<{width}}  {t.describe()}" for name, t in sorted(self.by_field().items())
        ]
        lines += ["", "  By document:"]
        for r in self.results:
            about = r.document
            kind = f"{about.capture}, {about.language}, {about.origin}"
            if about.simulated:
                kind += ", simulated"
            if not about.supported:
                outcome = (
                    "flagged unsupported" if r.flagged_unsupported else "NOT flagged unsupported"
                )
            else:
                outcome = r.tally.describe()
            note = f"  [{r.error}]" if r.error else ""
            lines.append(f"    {about.name:<24} {kind:<37} {outcome}{note}")
        return "\n".join(lines)


def run(extractor: Extractor, documents: Sequence[Document] | None = None) -> Report:
    results = []
    for document in load_corpus() if documents is None else documents:
        try:
            results.append(evaluate(document, extractor(document.path)))
        except Exception as error:  # any extractor failure is measured, not fatal
            results.append(failed(document, error))
    return Report(tuple(results))
