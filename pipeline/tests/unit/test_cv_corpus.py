"""The anonymised CV corpus (T028) and its ground truth.

Two jobs. The labels must agree with the documents they describe, since the accuracy gate (T029)
is only as good as they are. And the corpus must stay anonymised: this is the last check before a
CV reaches GitHub, so a real document committed by mistake fails here rather than being published.
"""

import json
import re
from pathlib import Path
from typing import Any

import pymupdf
import pytest

from tools.anonymise_cv import normalise

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"
PDFS = sorted(CORPUS.glob("*.pdf"))
DATE = re.compile(r"\d{4}(-(0[1-9]|1[0-2]))?")
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.)+[a-z]{2,}", re.IGNORECASE)
EGYPTIAN_MOBILE = re.compile(r"(?:\+\s*20|(?<!\d)0)[\s()-]*1[0125](?:[\s-]*\d){8}")
FAKE_MOBILE = "1000000"  # every invented number is 01000000xxx


def labels(pdf: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(pdf.with_suffix(".json").read_text(encoding="utf-8"))
    return loaded


def text(pdf: Path) -> str:
    return "".join(page.get_text() for page in pymupdf.open(pdf))


def test_the_corpus_is_not_empty() -> None:
    assert PDFS


def test_every_document_has_labels_and_every_label_a_document() -> None:
    documents = {path.stem for path in PDFS}
    labelled = {path.stem for path in CORPUS.glob("*.json")}
    assert documents == labelled


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_labels_follow_the_documented_format(pdf: Path) -> None:
    truth = labels(pdf)
    assert set(truth) == {"document", "expected", "profile", "protected"}
    document = truth["document"]
    assert document["capture"] in {"native", "scanned", "photographed"}
    assert document["language"] in {"en", "ar", "mixed", "fr"}
    assert document["layout"] in {"single_column", "two_column"}
    assert document["pages"] == pymupdf.open(pdf).page_count
    assert truth["expected"] in {"parsed", "unsupported_language"}
    profile = truth["profile"]
    assert set(profile) == {
        "name", "emails", "phones", "location", "years_of_experience", "employment",
        "education", "skills", "languages", "certifications",
    }  # fmt: skip
    assert all(re.fullmatch(r"\+\d{10,15}", phone) for phone in profile["phones"])
    for entry in profile["employment"] + profile["education"]:
        assert entry["start"] is None or DATE.fullmatch(entry["start"])
        assert entry["end"] in {None, "present"} or DATE.fullmatch(entry["end"])
    assert set(truth["protected"]) <= {
        "date_of_birth", "gender", "nationality", "marital_status", "photograph",
    }  # fmt: skip


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_labelled_identity_and_employers_appear_in_the_document(pdf: Path) -> None:
    profile, haystack = labels(pdf)["profile"], normalise(text(pdf))
    expected = [profile["name"], *profile["emails"]]
    expected += [job["employer"] for job in profile["employment"]]
    assert [value for value in expected if normalise(value) not in haystack] == []
    digits = re.sub(r"\D", "", text(pdf))
    assert [phone for phone in profile["phones"] if phone[-10:] not in digits] == []


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_no_document_carries_metadata_links_or_attachments(pdf: Path) -> None:
    doc = pymupdf.open(pdf)
    metadata = doc.metadata or {}
    assert [key for key in ("author", "title", "subject", "keywords") if metadata.get(key)] == []
    assert not doc.get_xml_metadata()
    assert [link for page in doc for link in page.get_links()] == []
    assert doc.embfile_count() == 0


def real_contacts(content: str) -> tuple[set[str], list[str]]:
    """Email domains and mobile numbers that are not invented ones.

    The text is also read with all whitespace removed, because a letter-spaced heading or a value
    wrapped across lines hides from a pattern that expects it in one piece.
    """
    domains: set[str] = set()
    mobiles: list[str] = []
    for variant in (content, "".join(content.split())):
        domains |= {m.group(0).rsplit("@", 1)[1].lower() for m in EMAIL.finditer(variant)}
        mobiles += [re.sub(r"\D", "", m.group(0)) for m in EGYPTIAN_MOBILE.finditer(variant)]
    return (
        {domain for domain in domains if not domain.startswith("example.")},
        [number for number in mobiles if FAKE_MOBILE not in number],
    )


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_every_email_and_mobile_number_is_invented(pdf: Path) -> None:
    assert real_contacts(text(pdf)) == (set(), [])
