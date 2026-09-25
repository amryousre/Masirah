"""Adds a real scan or phone photo of a corpus CV to the corpus (T028).

Run from pipeline/, giving the images in page order:

    uv run python -m tools.add_capture <source> <scanned|photographed> <name> <image>... \
        --corpus tests/fixtures/cvs

For example, two phone photos of the two pages of en-native-03:

    uv run python -m tools.add_capture en-native-03 photographed en-photographed-01 p1.jpg p2.jpg

Each image is turned upright by its EXIF orientation and then re-encoded from its pixels, so no
camera metadata survives: a phone photo's EXIF can hold where it was taken, the device and the
owner's name. The pages become one image-only PDF with no document metadata. The labels are the
source's with only the capture changed, `copy_of` set and `simulated` false: a scan or photo of a
corpus document shows the same person, so it needs no new labels and brings no new personal data.
"""

import io
import json
import re
import sys
from pathlib import Path
from typing import Literal, cast

import pymupdf
from PIL import Image, ImageOps

Capture = Literal["scanned", "photographed"]

CORPUS = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "cvs"
DOCUMENT_LINE = re.compile(r'^  "document": \{.*\},$', re.MULTILINE)
# Pixels become points at this density, so a page's size in the PDF follows the image's shape.
POINTS_PER_PIXEL = 72 / 150
JPEG_QUALITY = 92


def copied_labels(source: Path, capture: Capture, pages: int, *, simulated: bool) -> str:
    """A copy's labels: source's, with only the capture fields changed. Nothing is written, so a
    source whose labels cannot be copied is found before any file exists."""
    text = source.with_suffix(".json").read_text(encoding="utf-8")
    document = json.loads(text)["document"] | {
        "capture": capture,
        "pages": pages,
        "copy_of": source.stem,
        "simulated": simulated,
    }
    # Only the document line changes, so the copy keeps its source's hand-kept layout.
    inline = "{ " + json.dumps(document, ensure_ascii=False)[1:-1] + " }"
    text, replaced = DOCUMENT_LINE.subn(f'  "document": {inline},', text, count=1)
    if replaced != 1:
        raise ValueError(f"{source.stem}.json has no one-line document entry to rewrite")
    return text


def write_labels(output: Path, text: str) -> None:
    # LF on every platform, as the corpus is stored.
    output.with_suffix(".json").write_text(text, encoding="utf-8", newline="\n")


def copy_labels(source: Path, output: Path, capture: Capture, *, simulated: bool) -> None:
    """Writes the labels of a copy already made at output."""
    pages = pymupdf.open(output).page_count
    write_labels(output, copied_labels(source, capture, pages, simulated=simulated))


def clean_jpeg(image: Path) -> tuple[bytes, tuple[int, int]]:
    """The image upright and re-encoded from its pixels, with no EXIF, XMP or comment."""
    with Image.open(image) as picture:
        upright = ImageOps.exif_transpose(picture).convert("RGB")
    # A new image from the raw pixels alone. Saving the opened one would carry its comment and
    # colour profile over from the file's info, and either can name the device or the owner.
    pixels = Image.frombytes("RGB", upright.size, upright.tobytes())
    stream = io.BytesIO()
    pixels.save(stream, "JPEG", quality=JPEG_QUALITY)
    return stream.getvalue(), pixels.size


def add_capture(
    source: str, capture: Capture, name: str, images: list[Path], corpus: Path = CORPUS
) -> Path:
    original = corpus / f"{source}.pdf"
    labels = json.loads(original.with_suffix(".json").read_text(encoding="utf-8"))
    if labels["document"]["capture"] != "native":
        raise ValueError(f"{source} is itself a capture; photograph or scan a native document")
    output = corpus / f"{name}.pdf"
    if output.exists():
        raise FileExistsError(f"{output.name} is already in the corpus")
    if not images:
        raise ValueError("give the images in page order")

    # Everything that can fail is done before anything is written, so the corpus never holds a
    # capture without its labels, which would also block a retry under the same name.
    text = copied_labels(original, capture, len(images), simulated=False)
    document = pymupdf.open()
    for image in images:
        jpeg, (width, height) = clean_jpeg(image)
        page = document.new_page(width=width * POINTS_PER_PIXEL, height=height * POINTS_PER_PIXEL)
        page.insert_image(page.rect, stream=jpeg)
    document.set_metadata({})
    document.del_xml_metadata()
    document.save(output, garbage=4, deflate=True)
    try:
        write_labels(output, text)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return output


def main(argv: list[str]) -> int:
    corpus = CORPUS
    if "--corpus" in argv:
        at = argv.index("--corpus")
        if at + 1 >= len(argv):
            print(__doc__)
            return 2
        corpus = Path(argv[at + 1])
        argv = argv[:at] + argv[at + 2 :]
    if len(argv) < 4 or argv[1] not in ("scanned", "photographed"):
        print(__doc__)
        return 2
    source, capture, name, *images = argv
    output = add_capture(
        source, cast(Capture, capture), name, [Path(image) for image in images], corpus
    )
    print(f"{output.name}: {capture} copy of {source}, {len(images)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
