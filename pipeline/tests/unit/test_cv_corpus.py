"""The anonymised CV corpus (T028) and its ground truth.

Two jobs. The labels must agree with the documents they describe, since the accuracy gate (T029)
is only as good as they are. And the corpus must stay anonymised: this is the last check before a
CV reaches GitHub, so a real document committed by mistake fails here rather than being published.
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf
import pytest

from tools.anonymise_cv import normalise

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"
PDFS = sorted(CORPUS.glob("*.pdf"))
DATE = re.compile(r"\d{4}(-(0[1-9]|1[0-2]))?")
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.)+[a-z]{2,}", re.IGNORECASE)
EGYPTIAN_MOBILE = re.compile(r"(?:(?:\+|00)\s*20|(?<!\d)0)[\s()-]*1[0125](?:[\s-]*\d){8}")
INVENTED_MOBILE = "1000000"  # 01000000xxx: the national number starts 1000000
INVENTED_DOMAINS = ("example.com", "example.net", "example.org")


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


def without_arabic(value: str) -> str:
    return "".join(char for char in value if "ARABIC" not in unicodedata.name(char, ""))


def label_values(truth: dict[str, Any]) -> list[tuple[str, str]]:
    """Every labelled text value, paired with its field, for checking against the document."""
    profile, protected = truth["profile"], truth["protected"]
    values = [("name", profile["name"]), ("location", profile["location"])]
    values += [("email", email) for email in profile["emails"]]
    for job in profile["employment"]:
        values += [("employer", job["employer"]), ("title", job["title"])]
    for school in profile["education"]:
        values += [("institution", school["institution"])]
        values += [("qualification", school["qualification"])]
    values += [("skill", skill) for skill in profile["skills"]]
    for language in profile["languages"]:
        values += [("language", language["language"]), ("level", language["level"])]
    for cert in profile["certifications"]:
        values += [("certification", cert["name"]), ("issuer", cert["issuer"])]
    values += [(key, protected.get(key)) for key in ("nationality", "marital_status")]
    return [(field, value) for field, value in values if value]


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_every_label_is_written_as_the_document_writes_it(pdf: Path) -> None:
    """Arabic script is left to review: a PDF text layer often stores it in visual order or as
    presentation forms, which is exactly what extraction has to repair, so only the Latin part of
    a mixed value is compared here.
    """
    haystack = normalise(text(pdf))
    missing = [
        f"{field}: {value!r}"
        for field, value in label_values(labels(pdf))
        if (latin := normalise(without_arabic(value))) and latin not in haystack
    ]
    assert missing == []


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_every_labelled_phone_and_year_is_in_the_document(pdf: Path) -> None:
    profile, content = labels(pdf)["profile"], text(pdf)
    digits = re.sub(r"\D", "", content)
    assert [phone for phone in profile["phones"] if phone[-10:] not in digits] == []
    years = set(re.findall(r"\d{4}", content))
    dates = [
        date
        for entry in profile["employment"] + profile["education"]
        for date in (entry["start"], entry["end"])
        if date not in (None, "present")
    ]
    assert [date for date in dates if date[:4] not in years] == []


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_no_document_carries_metadata_links_or_attachments(pdf: Path) -> None:
    doc = pymupdf.open(pdf)
    metadata = doc.metadata or {}
    assert [key for key in ("author", "title", "subject", "keywords") if metadata.get(key)] == []
    assert not doc.get_xml_metadata()
    assert [link for page in doc for link in page.get_links()] == []
    assert doc.embfile_count() == 0


def invented_domain(domain: str, *, squeezed: bool) -> bool:
    if not squeezed:
        return domain in INVENTED_DOMAINS
    # Removing whitespace glues the next word onto the domain, so only its start can be compared,
    # and a following dot still means a longer domain such as example.com.evil.org.
    return any(
        domain.startswith(invented) and not domain[len(invented) :].startswith(".")
        for invented in INVENTED_DOMAINS
    )


def invented_mobile(number: str) -> bool:
    """Compares the national number from its first digit, whatever prefix it was written with."""
    digits = re.sub(r"\D", "", number)
    for prefix in ("0020", "20", "0"):
        if digits.startswith(prefix):
            digits = digits[len(prefix) :]
            break
    return digits.startswith(INVENTED_MOBILE)


def real_contacts(content: str) -> tuple[set[str], list[str]]:
    """Email domains and mobile numbers that are not invented ones.

    The text is also read with all whitespace removed, because a letter-spaced heading or a value
    wrapped across lines hides from a pattern that expects it in one piece.
    """
    domains: set[str] = set()
    mobiles: list[str] = []
    for variant, squeezed in ((content, False), ("".join(content.split()), True)):
        for match in EMAIL.finditer(variant):
            domain = match.group(0).rsplit("@", 1)[1].lower()
            if not invented_domain(domain, squeezed=squeezed):
                domains.add(domain)
        mobiles += [m.group(0) for m in EGYPTIAN_MOBILE.finditer(variant)]
    return domains, [number for number in mobiles if not invented_mobile(number)]


@pytest.mark.parametrize("pdf", PDFS, ids=lambda path: path.stem)
def test_every_email_and_mobile_number_is_invented(pdf: Path) -> None:
    assert real_contacts(text(pdf)) == (set(), [])


@pytest.mark.parametrize(
    "content",
    [
        "Mobile: 00201012345678",
        "Mobile: 01010000001",
        "Call +20 101 234 5678",
        "Email: person@example.com.evil.org",
        "Email: person@gmail.com",
        "E m a i l :  p e r s o n @ g m a i l . c o m",
        "Mail: person@\ngmail.com",
    ],
    ids=[
        "0020-prefix",
        "fake-digits-in-the-wrong-place",
        "plus-20",
        "invented-domain-as-a-prefix",
        "real-domain",
        "letter-spaced",
        "wrapped",
    ],
)
def test_the_contact_guard_catches_real_details(content: str) -> None:
    assert real_contacts(content) != (set(), [])


@pytest.mark.parametrize(
    "content",
    [
        "karim.farag@example.com",
        "Mobile: 01000000101",
        "+20 100 000 0105",
        "(+20) 1000000110",
        "0100 000 0103",
        "mahmoud.saeed@\nexample.com\n12 Example Street",
    ],
)
def test_the_contact_guard_accepts_invented_details(content: str) -> None:
    assert real_contacts(content) == (set(), [])
