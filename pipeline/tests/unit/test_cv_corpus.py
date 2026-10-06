"""The anonymised CV corpus (T028) and its ground truth.

Two jobs. The labels must agree with the documents they describe, since the accuracy gate (T029)
is only as good as they are. And the corpus must stay anonymised: this is the last check before a
CV reaches GitHub, so a real document committed by mistake fails here rather than being published.
"""

import io
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf
import pytest
from PIL import Image

from tools.anonymise_cv import normalise

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"
DATE = re.compile(r"\d{4}(-(0[1-9]|1[0-2]))?")
EMAIL = re.compile(r"[\w.+-]+@([\w-]+\.)+[a-z]{2,}", re.IGNORECASE)
EGYPTIAN_MOBILE = re.compile(r"(?:(?:\+|00)\s*20|(?<!\d)0)[\s()-]*1[0125](?:[\s-]*\d){8}")
INVENTED_MOBILE = "1000000"  # 01000000xxx: the national number starts 1000000
INVENTED_DOMAINS = ("example.com", "example.net", "example.org")
# Arabic-Indic and Eastern Arabic-Indic digits, read as the digits they stand for.
ARABIC_INDIC = {base + n: str(n) for base in (0x0660, 0x06F0) for n in range(10)}
NUMBER = re.compile(r"\d[\d\s()+-]*\d")


def labels(document: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(document.with_suffix(".json").read_text(encoding="utf-8"))
    return loaded


def stem(path: Path) -> str:
    return path.stem


DOCUMENTS = sorted([*CORPUS.glob("*.pdf"), *CORPUS.glob("*.jpg")])
PDFS = [document for document in DOCUMENTS if document.suffix == ".pdf"]
IMAGES = [document for document in DOCUMENTS if document.suffix == ".jpg"]
NATIVE = [d for d in DOCUMENTS if labels(d)["document"]["capture"] == "native"]
COPIES = [d for d in DOCUMENTS if labels(d)["document"]["copy_of"]]


def text(document: Path) -> str:
    """The text layer, with Arabic-Indic digits read as ASCII. A photograph has none."""
    content = "".join(page.get_text() for page in pymupdf.open(document))
    return content.translate(ARABIC_INDIC)


def numbers_reversed(content: str) -> str:
    """A PDF can store right-to-left lines in visual order, which reverses every number in them."""
    return NUMBER.sub(lambda match: match.group(0)[::-1], content)


def test_the_corpus_is_not_empty() -> None:
    assert NATIVE
    assert COPIES


def test_every_document_has_labels_and_every_label_a_document() -> None:
    documents = [path.stem for path in DOCUMENTS]
    assert len(documents) == len(set(documents)), "two documents share a name"
    assert set(documents) == {path.stem for path in CORPUS.glob("*.json")}


@pytest.mark.parametrize("document", DOCUMENTS, ids=stem)
def test_labels_follow_the_documented_format(document: Path) -> None:
    truth = labels(document)
    assert set(truth) == {"document", "expected", "profile", "protected"}
    about = truth["document"]
    assert set(about) == {
        "capture", "language", "layout", "pages", "origin", "copy_of", "simulated",
    }  # fmt: skip
    assert about["capture"] in {"native", "scanned", "photographed"}
    assert about["language"] in {"en", "ar", "mixed", "fr"}
    assert about["layout"] in {"single_column", "two_column"}
    assert about["pages"] == pymupdf.open(document).page_count
    assert about["origin"] in {"real", "synthetic"}
    assert isinstance(about["simulated"], bool)
    if about["copy_of"] is None:
        # A real capture stands alone; a simulated one is either a copy of a corpus document or
        # an invented document photographed or scanned digitally, which never counts for the gate.
        assert not about["simulated"] or about["origin"] == "synthetic", (
            "only a copy of a corpus document, or an invented one, can be simulated"
        )
    else:
        assert about["capture"] != "native", "a copy is a scan or a photograph"
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
        "military_service",
    }  # fmt: skip


@pytest.mark.parametrize("copy", COPIES, ids=stem)
def test_a_copy_carries_its_sources_labels(copy: Path) -> None:
    """A scan or photo of a corpus document shows the same person, so only the capture differs."""
    truth = labels(copy)
    source = CORPUS / f"{truth['document']['copy_of']}.pdf"
    original = labels(source)
    assert original["document"]["capture"] == "native"
    for key in ("expected", "profile", "protected"):
        assert truth[key] == original[key], key
    for key in ("language", "layout", "origin"):
        assert truth["document"][key] == original["document"][key], key


@pytest.mark.parametrize("copy", COPIES, ids=stem)
def test_a_scan_or_photo_has_no_text_layer(copy: Path) -> None:
    """Otherwise extraction could read the text and never meet the pixels it is meant to test.
    This holds for real captures too: SC-003 measures reading pixels, not a scanner's OCR."""
    assert text(copy).strip() == ""


def latin_parts(value: str) -> list[str]:
    """The stretches of a value between its Arabic words, each compared on its own: in a mixed
    value such as "ICDL النسخة 5" the Arabic words sit between them in the document's text."""
    parts = [""]
    for char in value:
        if "ARABIC" in unicodedata.name(char, ""):
            parts.append("")
        else:
            parts[-1] += char
    return [part for part in map(normalise, parts) if part]


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


@pytest.mark.parametrize("pdf", NATIVE, ids=stem)
def test_every_label_is_written_as_the_document_writes_it(pdf: Path) -> None:
    """Arabic script is left to review: a PDF text layer often stores it in visual order or as
    presentation forms, which is exactly what extraction has to repair, so only the Latin parts of
    a mixed value are compared here. test_native_text.py checks the Arabic, through extraction.
    """
    haystack = normalise(text(pdf))
    missing = [
        f"{field}: {value!r}"
        for field, value in label_values(labels(pdf))
        if any(part not in haystack for part in latin_parts(value))
    ]
    assert missing == []


@pytest.mark.parametrize("pdf", NATIVE, ids=stem)
def test_every_labelled_phone_and_year_is_in_the_document(pdf: Path) -> None:
    profile, content = labels(pdf)["profile"], text(pdf)
    readings = (content, numbers_reversed(content))
    digits = [re.sub(r"\D", "", reading) for reading in readings]
    assert [p for p in profile["phones"] if not any(p[-10:] in d for d in digits)] == []
    years = {year for reading in readings for year in re.findall(r"\d{4}", reading)}
    dates = [
        date
        for entry in profile["employment"] + profile["education"]
        for date in (entry["start"], entry["end"])
        if date not in (None, "present")
    ]
    assert [date for date in dates if date[:4] not in years] == []


@pytest.mark.parametrize("pdf", PDFS, ids=stem)
def test_no_pdf_carries_metadata_links_or_attachments(pdf: Path) -> None:
    doc = pymupdf.open(pdf)
    metadata = doc.metadata or {}
    assert [key for key in ("author", "title", "subject", "keywords") if metadata.get(key)] == []
    assert not doc.get_xml_metadata()
    assert [link for page in doc for link in page.get_links()] == []
    assert doc.embfile_count() == 0


@pytest.mark.parametrize("image", IMAGES, ids=stem)
def test_no_photograph_carries_camera_metadata(image: Path) -> None:
    """A phone photo's EXIF can hold the place it was taken, the device and the owner's name."""
    with Image.open(image) as picture:
        assert picture.format == "JPEG"
        assert not picture.getexif()
        assert not {"exif", "xmp", "comment"} & set(picture.info)


@pytest.mark.parametrize("pdf", PDFS, ids=stem)
def test_no_image_inside_a_pdf_carries_camera_metadata(pdf: Path) -> None:
    """A real scan or photo is stored as a PDF of its pages, and each page image is a JPEG that
    could still hold the same EXIF as a photo saved on its own."""
    doc = pymupdf.open(pdf)
    for xref in {image[0] for page in doc for image in page.get_images()}:
        extracted = doc.extract_image(xref)
        with Image.open(io.BytesIO(extracted["image"])) as picture:
            assert not picture.getexif(), f"image {xref}"
            assert not {"exif", "xmp", "comment"} & set(picture.info), f"image {xref}"


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
    wrapped across lines hides from a pattern that expects it in one piece, and with every number
    reversed, because a number stored in visual order reads backwards.
    """
    content = content.translate(ARABIC_INDIC)
    domains: set[str] = set()
    mobiles: list[str] = []
    readings = (
        (content, False),
        ("".join(content.split()), True),
        (numbers_reversed(content), False),
    )
    for reading, squeezed in readings:
        for match in EMAIL.finditer(reading):
            domain = match.group(0).rsplit("@", 1)[1].lower()
            if not invented_domain(domain, squeezed=squeezed):
                domains.add(domain)
        mobiles += [m.group(0) for m in EGYPTIAN_MOBILE.finditer(reading)]
    return domains, [number for number in mobiles if not invented_mobile(number)]


@pytest.mark.parametrize("document", DOCUMENTS, ids=stem)
def test_every_email_and_mobile_number_is_invented(document: Path) -> None:
    assert real_contacts(text(document)) == (set(), [])


def arabic_indic(ascii_text: str) -> str:
    return "".join(chr(0x0660 + int(c)) if c.isdigit() else c for c in ascii_text)


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
        arabic_indic("01012345678"),
        arabic_indic("0101 234 5678")[::-1],
    ],
    ids=[
        "0020-prefix",
        "fake-digits-in-the-wrong-place",
        "plus-20",
        "invented-domain-as-a-prefix",
        "real-domain",
        "letter-spaced",
        "wrapped",
        "arabic-indic-digits",
        "arabic-indic-stored-reversed",
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
        arabic_indic("0100 000 0202"),
        arabic_indic("0100 000 0202")[::-1],
    ],
)
def test_the_contact_guard_accepts_invented_details(content: str) -> None:
    assert real_contacts(content) == (set(), [])
