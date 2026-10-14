"""The Tesseract fallback OCR engine (T078, research.md "OCR strategy").

Tesseract reads a photograph, or each page of a scanned PDF rendered to an image, in Arabic and
English. It runs on the worker's own machine, so a reading costs nothing and nothing leaves it.

The first tests run against a fake Tesseract, so they need nothing installed. The last ones run the
real engine on scans and photos from the corpus and are skipped where it is not installed; CI
installs it, so they always run there.
"""

import io
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest
from PIL import Image

from masirah_pipeline.adapters import tesseract_ocr
from masirah_pipeline.adapters.tesseract_ocr import TesseractOcr, pdf_page_images
from masirah_pipeline.ports.document_text import UnreadableDocumentError
from masirah_pipeline.ports.model_provider import ProviderUnavailableError, TimedOutError

CORPUS = Path(__file__).parents[1] / "fixtures" / "cvs"


@dataclass
class FakeTesseract:
    """Stands in for the tesseract process: answers each page with the next output."""

    outputs: list[str] = field(default_factory=lambda: ["page one"])
    code: int = 0
    errors: str = "could not read the image"
    error: Exception | None = None
    calls: list[tuple[list[str], bytes, float]] = field(default_factory=list)

    def __call__(self, args: list[str], stdin: bytes, timeout: float) -> tuple[int, bytes, bytes]:
        self.calls.append((args, stdin, timeout))
        if self.error is not None:
            raise self.error
        output = self.outputs[min(len(self.calls), len(self.outputs)) - 1]
        return self.code, output.encode(), self.errors.encode() if self.code else b""


@dataclass
class Clock:
    """Seconds passing: each reading of the clock moves it on by the given step."""

    now: float = 0.0
    step: float = 0.0

    def __call__(self) -> float:
        self.now += self.step
        return self.now


def engine(
    fake: FakeTesseract, pages: list[bytes] | None = None, clock: Clock | None = None
) -> TesseractOcr:
    return TesseractOcr(
        command="tesseract",
        tessdata="/data/tessdata",
        run=fake,
        render=lambda content: iter(pages if pages is not None else [b"P5 page"]),
        clock=clock or Clock(),
    )


def option(args: list[str], name: str) -> list[str]:
    return args[args.index(name) : args.index(name) + 2]


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
        [(args, stdin, _)] = fake.calls
        assert stdin == b"\xff\xd8\xff a photo"
        assert args[0] == "tesseract"
        assert "stdin" in args
        assert "stdout" in args
        assert option(args, "-l") == ["-l", "ara+eng"]
        assert option(args, "--tessdata-dir") == ["--tessdata-dir", "/data/tessdata"]

    def test_tesseract_finds_the_page_orientation_itself(self) -> None:
        """Mode 1 detects orientation, so a phone photo stored on its side is read upright; the
        default mode reads it sideways (checked against a rotated corpus photo below)."""
        fake = FakeTesseract()
        engine(fake).read(b"photo", "image/jpeg")
        [(args, _, _)] = fake.calls
        assert option(args, "--psm") == ["--psm", "1"]

    def test_each_page_of_a_scanned_pdf_is_read_in_order(self) -> None:
        fake = FakeTesseract(["first page", "second page"])
        reading = engine(fake, pages=[b"P5 one", b"P5 two"]).read(b"%PDF", "application/pdf")
        assert reading.text == "first page\n\nsecond page"
        assert [stdin for _, stdin, _ in fake.calls] == [b"P5 one", b"P5 two"]

    def test_the_pages_share_one_time_budget(self) -> None:
        """A long scan cannot hold the worker past the queue's visibility timeout: each page gets
        what is left of the document's budget, and none once it is spent."""
        fake = FakeTesseract(["one", "two", "three"])
        clock = Clock(step=70)
        reader = engine(fake, pages=[b"P5 1", b"P5 2", b"P5 3"], clock=clock)
        with pytest.raises(TimedOutError, match="document"):
            reader.read(b"%PDF", "application/pdf")
        assert [timeout for _, _, timeout in fake.calls] == [110, 40]

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

    @pytest.mark.parametrize(
        "error", [FileNotFoundError("tesseract"), PermissionError("tesseract")], ids=str
    )
    def test_a_tesseract_that_cannot_run_is_unavailable(self, error: OSError) -> None:
        with pytest.raises(ProviderUnavailableError, match="cannot run"):
            engine(FakeTesseract(error=error)).read(b"photo", "image/png")

    @pytest.mark.parametrize(
        ("code", "errors"),
        [
            (-9, ""),
            (1, "Failed loading language 'eng'"),
            (1, "Error opening data file /data/tessdata/ara.traineddata"),
        ],
        ids=["killed", "missing-language", "missing-data-file"],
    )
    def test_a_fault_of_the_install_is_retried_not_blamed_on_the_file(
        self, code: int, errors: str
    ) -> None:
        with pytest.raises(ProviderUnavailableError):
            engine(FakeTesseract(code=code, errors=errors)).read(b"photo", "image/png")

    def test_a_type_it_cannot_take_is_refused(self) -> None:
        with pytest.raises(UnreadableDocumentError, match="image/webp"):
            engine(FakeTesseract()).read(b"RIFF", "image/webp")

    def test_a_pdf_with_no_pages_is_unreadable(self) -> None:
        with pytest.raises(UnreadableDocumentError, match="no pages"):
            engine(FakeTesseract(), pages=[]).read(b"%PDF", "application/pdf")


class TestPdfPages:
    def test_each_page_becomes_a_greyscale_image_tesseract_can_take(self) -> None:
        pages = list(pdf_page_images((CORPUS / "en-scanned-01.pdf").read_bytes()))
        assert len(pages) == 2
        for page in pages:
            header, width, height, depth = page.split(maxsplit=4)[:4]
            assert header == b"P5"
            assert int(width) > 1000
            assert int(height) > 1000
            assert depth == b"255"

    def test_only_the_first_pages_of_a_long_pdf_are_read(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A long scan is read as far as a CV's details go, never refused as unreadable."""
        monkeypatch.setattr(tesseract_ocr, "MAX_PAGES", 1)
        pages = list(pdf_page_images((CORPUS / "en-scanned-01.pdf").read_bytes()))
        assert len(pages) == 1

    def test_pages_are_rendered_one_at_a_time(self) -> None:
        pages = pdf_page_images((CORPUS / "en-scanned-01.pdf").read_bytes())
        assert next(pages).startswith(b"P5 ")

    def test_a_file_that_is_not_a_pdf_is_unreadable(self) -> None:
        with pytest.raises(UnreadableDocumentError):
            list(pdf_page_images(b"not a pdf at all"))


class TestLanguages:
    def test_the_languages_are_read_from_tesseracts_listing(self) -> None:
        listing = 'List of available languages in "/data/tessdata/" (3):\nara\neng\nosd\n'
        fake = FakeTesseract([listing])
        assert engine(fake).available_languages() == {"ara", "eng", "osd"}
        [(args, _, _)] = fake.calls
        assert option(args, "--tessdata-dir") == ["--tessdata-dir", "/data/tessdata"]
        assert "--list-langs" in args


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

    @pytest.mark.parametrize("angle", [90, 180, 270])
    def test_a_photograph_taken_on_its_side_is_read_upright(
        self, tesseract: TesseractOcr, angle: int
    ) -> None:
        """Phone photos are often stored rotated. The corpus strips their camera metadata, so the
        rotation is made here."""
        photo = Image.open(CORPUS / "syn-ar-photographed-01.jpg").rotate(angle, expand=True)
        buffer = io.BytesIO()
        photo.save(buffer, "JPEG")
        text = tesseract.read(buffer.getvalue(), "image/jpeg").text
        assert "محاسب أول" in text

    def test_a_scanned_english_pdf_is_read_page_by_page(self, tesseract: TesseractOcr) -> None:
        """Both pages are read. What Tesseract misses here is why it is only the fallback: the name,
        pale capitals on a dark band, is not read at all, and the email gains a space. Confidence
        then sends such a profile to review rather than ranking it on a wrong name."""
        scan = (CORPUS / "en-scanned-01.pdf").read_bytes()
        text = tesseract.read(scan, "application/pdf").text
        assert "linkedin.com/in/karim-farag-example" in text
        assert "Andalusia Medical Service Group" in text
        assert "\r" not in text
