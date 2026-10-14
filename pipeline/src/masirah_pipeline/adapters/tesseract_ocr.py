"""The Tesseract OCR engine, the fallback for scans and photographs (T078, research.md).

Tesseract runs on the worker's own machine, in Arabic and English, so a reading costs nothing and
nothing leaves the machine. It is weaker than the vision model (T077) on Arabic and on photographs
of printed pages, which is why it is the fallback rather than the primary path.

A photograph goes to Tesseract as it is. A scanned PDF is rendered one page at a time at 300 dpi
with PDFium (pypdfium2, BSD and Apache licensed, unlike PyMuPDF), each page passed as a greyscale
PGM image, so no imaging library is needed at run time. Tesseract finds each page's orientation
itself (page segmentation mode 1, with its osd data), so a phone photo stored on its side is read
upright. Tesseract is a separate program: its command and the directory holding its language data
are settings (MASIRAH_TESSERACT_CMD, MASIRAH_TESSDATA_DIR), and it must be installed wherever the
worker runs.
"""

import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from decimal import Decimal

import pypdfium2 as pdfium

from masirah_pipeline.ports.document_text import UnreadableDocumentError
from masirah_pipeline.ports.model_provider import ProviderUnavailableError, TimedOutError
from masirah_pipeline.ports.ocr_engine import OcrReading

# A process run: arguments, input, seconds allowed; returns the exit code, output and errors.
Runner = Callable[[list[str], bytes, float], tuple[int, bytes, bytes]]

IMAGE_TYPES = frozenset({"image/jpeg", "image/png"})
# Arabic and English, and the orientation data page segmentation mode 1 needs.
LANGUAGE_DATA = ("ara", "eng", "osd")
# Scanned pages are rendered at the resolution Tesseract is tuned for.
DPI = 300
# A CV says who the candidate is and what they have done in its first pages; reading further would
# only hold the worker. The native reader stops at its own limit for the same reason.
MAX_PAGES = 8
# All of one document's pages share this many seconds, so a long scan cannot hold the worker past
# the queue's visibility timeout.
DOCUMENT_SECONDS = 180.0
# The direction marks and isolates Tesseract puts around Latin runs in Arabic text.
DIRECTION_MARKS = dict.fromkeys(map(ord, "‎‏؜‪‫‬‭‮⁦⁧⁨⁩"))


def run(args: list[str], stdin: bytes, timeout: float) -> tuple[int, bytes, bytes]:
    done = subprocess.run(args, input=stdin, capture_output=True, timeout=timeout, check=False)  # noqa: S603
    return done.returncode, done.stdout, done.stderr


def pdf_page_images(content: bytes) -> Iterator[bytes]:
    """The first MAX_PAGES pages of a PDF as greyscale PGM images, in order, one at a time."""
    try:
        document = pdfium.PdfDocument(content)
    except pdfium.PdfiumError as error:
        raise UnreadableDocumentError(f"the PDF cannot be opened: {error}") from error
    try:
        for index in range(min(len(document), MAX_PAGES)):
            yield _pgm(document[index])
    finally:
        document.close()


def _pgm(page: pdfium.PdfPage) -> bytes:
    bitmap = page.render(scale=DPI / 72, grayscale=True)
    width, height, stride = bitmap.width, bitmap.height, bitmap.stride
    pixels = bytes(bitmap.buffer)
    if stride != width:
        pixels = b"".join(pixels[row * stride : row * stride + width] for row in range(height))
    return b"P5 %d %d 255\n" % (width, height) + pixels


@dataclass
class TesseractOcr:
    command: str = "tesseract"
    # Where the .traineddata files are, or None for Tesseract's own default.
    tessdata: str | None = None
    languages: str = "ara+eng"
    document_seconds: float = DOCUMENT_SECONDS
    run: Runner = field(default=run, repr=False)
    render: Callable[[bytes], Iterator[bytes]] = field(default=pdf_page_images, repr=False)
    clock: Callable[[], float] = field(default=time.monotonic, repr=False)

    def read(self, content: bytes, media_type: str) -> OcrReading:
        if media_type in IMAGE_TYPES:
            pages: Iterator[bytes] = iter([content])
        elif media_type == "application/pdf":
            pages = self.render(content)
        else:
            raise UnreadableDocumentError(f"Tesseract cannot read {media_type}")
        deadline = self.clock() + self.document_seconds
        texts = [self._page(page, deadline).strip() for page in pages]
        if not texts:
            raise UnreadableDocumentError("the PDF has no pages")
        text = "\n\n".join(texts).translate(DIRECTION_MARKS)
        return OcrReading(text, "tesseract_ocr", None, Decimal(0))

    def available_languages(self) -> set[str]:
        """The language data this Tesseract can load, run exactly as a reading runs it."""
        output = self._run([*self._base(), "--list-langs"], b"", 30)
        # A header line, then one language per line.
        lines = output.decode("utf-8", "replace").splitlines()[1:]
        return {line.strip() for line in lines if line.strip()}

    def _base(self) -> list[str]:
        return [self.command] + (["--tessdata-dir", self.tessdata] if self.tessdata else [])

    def _page(self, image: bytes, deadline: float) -> str:
        left = deadline - self.clock()
        if left <= 0:
            raise TimedOutError(f"Tesseract took over {self.document_seconds:g}s for the document")
        args = [*self._base(), "stdin", "stdout", "-l", self.languages, "--psm", "1"]
        # Tesseract ends its lines as the platform does; a profile's text uses plain line breaks.
        return self._run(args, image, left).decode("utf-8", "replace").replace("\r\n", "\n")

    def _run(self, args: list[str], stdin: bytes, timeout: float) -> bytes:
        try:
            code, output, errors = self.run(args, stdin, timeout)
        except subprocess.TimeoutExpired as error:
            raise TimedOutError(f"Tesseract took over {timeout:g}s") from error
        except OSError as error:
            raise ProviderUnavailableError(
                f"Tesseract cannot run at {self.command}: {error}"
            ) from error
        if code == 0:
            return output
        reason = (errors.decode("utf-8", "replace").strip().splitlines() or [""])[-1]
        # Killed, or unable to load its own data: the install is at fault, not the file, and the
        # same file may read on a later attempt.
        if code < 0 or "Failed loading language" in reason or "Error opening data file" in reason:
            raise ProviderUnavailableError(reason or f"Tesseract exited with {code}")
        raise UnreadableDocumentError(reason or f"Tesseract exited with {code}")
