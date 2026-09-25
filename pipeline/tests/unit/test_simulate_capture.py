"""Simulated scans and photographs (T028), and the build step that adds them to the corpus."""

import json
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from tools import build_synthetic_cvs
from tools.build_synthetic_cvs import Copy, add_copy, add_rendered
from tools.simulate_capture import PHOTO_SIZE, _perspective, photograph, scan

SOURCE_LABELS = """{
  "document": { "capture": "native", "language": "en", "origin": "synthetic", "simulated": false },
  "expected": "parsed",
  "profile": { "name": "Amal Fathy", "skills": ["SQL",   "Excel"] },
  "protected": {}
}
"""


def make_pdf(path: Path, pages: int = 1) -> Path:
    doc = pymupdf.open()
    for number in range(pages):
        doc.new_page().insert_text((72, 72), f"Amal Fathy, page {number + 1}", fontsize=14)
    doc.set_metadata({"title": "Amal Fathy CV", "author": "Amal Fathy"})
    doc.save(path)
    return path


def test_a_scan_keeps_every_page_and_leaves_only_pixels(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "cv.pdf", pages=2)
    scan(source, tmp_path / "scan.pdf", seed=1)
    scanned = pymupdf.open(tmp_path / "scan.pdf")
    assert scanned.page_count == 2
    assert scanned[0].rect == pymupdf.open(source)[0].rect
    assert all(page.get_text().strip() == "" for page in scanned)
    assert all(len(page.get_images()) == 1 for page in scanned)


def test_a_photograph_is_a_phone_sized_jpeg_without_exif(tmp_path: Path) -> None:
    photograph(make_pdf(tmp_path / "cv.pdf"), tmp_path / "photo.jpg", seed=1)
    with Image.open(tmp_path / "photo.jpg") as picture:
        assert (picture.format, picture.size) == ("JPEG", PHOTO_SIZE)
        assert not picture.getexif()


def test_the_same_seed_gives_the_same_photograph(tmp_path: Path) -> None:
    source = make_pdf(tmp_path / "cv.pdf")
    first, second, other = (tmp_path / f"{name}.jpg" for name in ("a", "b", "c"))
    photograph(source, first, seed=7)
    photograph(source, second, seed=7)
    photograph(source, other, seed=8)
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() != other.read_bytes()


def test_a_photograph_of_several_pages_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="one page"):
        photograph(make_pdf(tmp_path / "cv.pdf", pages=2), tmp_path / "photo.jpg", seed=1)


def test_the_perspective_maps_each_corner_back_to_the_paper() -> None:
    photo = [(110.0, 95.0), (1420.0, 120.0), (1460.0, 1950.0), (80.0, 1930.0)]
    paper = [(0.0, 0.0), (1400.0, 0.0), (1400.0, 1980.0), (0.0, 1980.0)]
    a, b, c, d, e, f, g, h = _perspective(photo, paper)
    for (x, y), (u, v) in zip(photo, paper, strict=True):
        w = g * x + h * y + 1
        assert (a * x + b * y + c) / w == pytest.approx(u, abs=1e-6)
        assert (d * x + e * y + f) / w == pytest.approx(v, abs=1e-6)


def test_rendered_pdfs_enter_the_corpus_without_metadata(tmp_path: Path) -> None:
    raw, corpus = tmp_path / "raw", tmp_path / "corpus"
    raw.mkdir()
    corpus.mkdir()
    make_pdf(raw / "syn-en-native-09.pdf")
    make_pdf(raw / "unrelated.pdf")
    assert add_rendered(raw, corpus) == ["syn-en-native-09.pdf"]
    metadata = pymupdf.open(corpus / "syn-en-native-09.pdf").metadata or {}
    assert (metadata.get("title"), metadata.get("author")) == ("", "")


def test_a_copy_changes_only_its_document_line(tmp_path: Path) -> None:
    make_pdf(tmp_path / "syn-en-native-09.pdf")
    (tmp_path / "syn-en-native-09.json").write_text(SOURCE_LABELS, encoding="utf-8")
    copy = Copy("syn-en-scanned-09", "syn-en-native-09", "scanned", seed=3)
    assert add_copy(copy, tmp_path) == "syn-en-scanned-09.pdf"
    written = (tmp_path / "syn-en-scanned-09.json").read_text(encoding="utf-8")
    pairs = zip(SOURCE_LABELS.splitlines(), written.splitlines(), strict=True)
    assert [number for number, (a, b) in enumerate(pairs) if a != b] == [1]
    assert json.loads(written)["document"] == {
        "capture": "scanned", "language": "en", "origin": "synthetic", "simulated": True,
        "pages": 1, "copy_of": "syn-en-native-09",
    }  # fmt: skip


def test_every_planned_copy_names_a_distinct_file() -> None:
    names = [copy.name for copy in build_synthetic_cvs.COPIES]
    assert len(names) == len(set(names))
    assert all(copy.name != copy.source for copy in build_synthetic_cvs.COPIES)
