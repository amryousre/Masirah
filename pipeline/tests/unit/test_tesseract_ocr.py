"""The Tesseract fallback OCR engine (T078, research.md "OCR strategy").

Tesseract reads a photograph, or each page of a scanned PDF rendered to an image, in Arabic and
English. It runs on the worker's own machine, so a reading costs nothing and nothing leaves it.

The first tests run against a fake Tesseract, so they need nothing installed. The last ones run the
real engine on scans and photos from the corpus and are skipped where it is not installed; CI
installs it, so they always run there.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from masirah_pipeline.adapters.tesseract_ocr import TesseractOcr, pdf_page_images
from masirah_pipeline.ports.document_text import UnreadableDocumentError
from masirah_pipeline.ports.model_provider import ProviderUnavailableError, TimedOutError

CORPUS = Path(__file__).parents[1] / "fixtures" / "cvs"


@dataclass
class FakeTesseract:
    """Stands in for the tesseract process: answers each page with the next output."""

    outputs: list[str] = field(default_factory=lambda: ["page one"])
    code: int = 0
    error: Exception | None = None
    calls: list[tuple[list[str], bytes]] = field(default_factory=list)

    def __call__(self, args: list[str], stdin: bytes, timeout: float) -> tuple[int, bytes, bytes]:
        self.calls.append((args, stdin))
        if self.error is not None:
            raise self.error
        output = self.outputs[min(len(self.calls), len(self.outputs)) - 1]
        return self.code, output.encode(), b"could not read the image" if self.code else b""


def engine(fake: FakeTesseract, pages: list[bytes] | None = None) -> TesseractOcr:
    return TesseractOcr(
        command="tesseract",
        tessdata="/data/tessdata",
        run=fake,
        render=lambda content: pages if pages is not None else [b"P5 page"],
    )


class TestWithAFakeEngine:
    def test_a_photograph_is_read_in_arabic_and_english_at_no_cost(self) -> None:
        fake = FakeTesseract(["محاسب أول\n"])
        reading = engine(fake).read(b"\xff\xd8\xff a photo", "image/jpeg")
        assert (reading.text, reading.source, reading.identity, reading.cost_egp) == (
            "محاسب أول",
            "tesseract_ocr",
            None,
            Decimal(0),
        )
        [(args, stdin)] = fake.calls
        assert stdin == b"\xff\xd8\xff a photo"
        assert args[:3] == ["tesseract", "stdin", "stdout"]
        assert args[args.index("-l") : args.index("-l") + 2] == ["-l", "ara+eng"]
        assert args[args.index("--tessdata-dir") : args.index("--tessdata-dir") + 2] == [
            "--tessdata-dir",
            "/data/tessdata",
        ]

    def test_each_page_of_a_scanned_pdf_is_read_in_order(self) -> None:
        fake = FakeTesseract(["first page", "second page"])
        reading = engine(fake, pages=[b"P5 one", b"P5 two"]).read(b"%PDF", "application/pdf")
        assert reading.text == "first page\n\nsecond page"
        assert [stdin for _, stdin in fake.calls] == [b"P5 one", b"P5 two"]

    def test_the_direction_marks_tesseract_adds_are_removed(self) -> None:
        """Tesseract wraps Latin runs in Arabic text in LRM and RLM marks. Left in, they keep an
        email or a product name from matching the profile's value, which lowers confidence."""
        fake = FakeTesseract(["القاهرة | \u200eahmed@example.com\u200f | \u200eOracle\u200f"])
        reading = engine(fake).read(b"photo", "image/png")
        assert reading.text == "القاهرة | ahmed@example.com | Oracle"

    def test_windows_line_endings_become_plain_ones(self) -> None:
        fake = FakeTesseract(["Alexandria\r\n01000000101\r\n"])
        assert engine(fake).read(b"photo", "image/png").text == "Alexandria\n01000000101"

    def test_an_image_tesseract_cannot_read_is_unreadable(self) -> None:
        with pytest.raises(UnreadableDocumentError, match="could not read the image"):
            engine(FakeTesseract(code=1)).read(b"not an image", "image/png")

    def test_a_reading_that_takes_too_long_is_timed_out(self) -> None:
        fake = FakeTesseract(error=subprocess.TimeoutExpired("tesseract", 120))
        with pytest.raises(TimedOutError):
            engine(fake).read(b"photo", "image/png")

    def test_a_missing_tesseract_is_unavailable(self) -> None:
        fake = FakeTesseract(error=FileNotFoundError("tesseract"))
        with pytest.raises(ProviderUnavailableError, match="not installed"):
            engine(fake).read(b"photo", "image/png")

    def test_a_type_it_cannot_take_is_refused(self) -> None:
        with pytest.raises(UnreadableDocumentError, match="image/webp"):
            engine(FakeTesseract()).read(b"RIFF", "image/webp")

    def test_a_pdf_with_no_pages_is_unreadable(self) -> None:
        with pytest.raises(UnreadableDocumentError, match="no pages"):
            engine(FakeTesseract(), pages=[]).read(b"%PDF", "application/pdf")


class TestPdfPages:
    def test_each_page_becomes_a_greyscale_image_tesseract_can_take(self) -> None:
        pages = pdf_page_images((CORPUS / "en-scanned-01.pdf").read_bytes())
        assert len(pages) == 2
        for page in pages:
            header, width, height, depth = page.split(maxsplit=4)[:4]
            assert header == b"P5"
            assert int(width) > 1000
            assert int(height) > 1000
            assert depth == b"255"

    def test_a_file_that_is_not_a_pdf_is_unreadable(self) -> None:
        with pytest.raises(UnreadableDocumentError):
            pdf_page_images(b"not a pdf at all")


def _installed() -> tuple[str, str | None] | None:
    """Where Tesseract and its Arabic data are on this machine, or None."""
    command = os.environ.get("MASIRAH_TESSERACT_CMD") or shutil.which("tesseract")
    windows = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
    if command is None and windows.exists():
        command = str(windows)
    if command is None:
        return None
    tessdata = os.environ.get("MASIRAH_TESSDATA_DIR")
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "tessdata"
    if tessdata is None and (local / "ara.traineddata").exists():
        tessdata = str(local)
    return command, tessdata


INSTALLED = _installed()
real = pytest.mark.skipif(INSTALLED is None, reason="Tesseract is not installed here")


@real
class TestTheRealEngine:
    @pytest.fixture
    def tesseract(self) -> TesseractOcr:
        assert INSTALLED is not None
        command, tessdata = INSTALLED
        return TesseractOcr(command=command, tessdata=tessdata)

    def test_an_arabic_photograph_is_read(self, tesseract: TesseractOcr) -> None:
        photo = (CORPUS / "syn-ar-photographed-01.jpg").read_bytes()
        text = tesseract.read(photo, "image/jpeg").text
        assert "محاسب أول" in text
        assert "ahmed.samir@example.com" in text

    def test_a_scanned_english_pdf_is_read_page_by_page(self, tesseract: TesseractOcr) -> None:
        """Both pages are read. What Tesseract misses here is why it is only the fallback: the name,
        pale capitals on a dark band, is not read at all, and the email gains a space. Confidence
        then sends such a profile to review rather than ranking it on a wrong name."""
        scan = (CORPUS / "en-scanned-01.pdf").read_bytes()
        text = tesseract.read(scan, "application/pdf").text
        assert "linkedin.com/in/karim-farag-example" in text
        assert "Andalusia Medical Service Group" in text
        assert "\r" not in text
