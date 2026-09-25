"""Text from a native PDF or DOCX CV, in the order a person reads it (T052, FR-004).

PDF text comes from pdfminer.six's line analysis: each line of text with its box on the page.
reading_order puts the lines in reading order, column by column, and visual_order repairs Arabic
lines that the PDF stores backwards. A PDF with no text layer, such as a scan, gives empty text,
which is what sends it to OCR instead.

DOCX text is read from the document's XML in document order, which is already reading order:
paragraphs, table cells row by row, and the text boxes Word CV templates use for sidebars, each
read where it is anchored.

pdfminer.six (MIT) rather than PyMuPDF, which the plan first named: PyMuPDF is licensed under the
AGPL, and this runs in the hosted service. See research.md.
"""

import io
import re
import unicodedata
import zipfile
from collections.abc import Iterator
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from pdfminer.high_level import extract_pages
from pdfminer.layout import LAParams, LTContainer, LTPage, LTTextLine

from masirah_pipeline.adapters.reading_order import Line, reading_order
from masirah_pipeline.adapters.visual_order import (
    is_right_to_left,
    laid_out_right_to_left,
    logical_line,
    stored_backwards,
)

# A CV runs to a few pages. Reading no further bounds the time a hostile file can take.
MAX_PAGES = 20
# A DOCX is a zip archive. Refusing one that unpacks beyond this bounds the memory it can take.
MAX_DOCX_BYTES = 20 * 1024 * 1024

PDF_SIGNATURE = b"%PDF-"
ZIP_SIGNATURE = b"PK\x03\x04"

PERSIAN_LETTERS = str.maketrans(
    {
        "\N{ARABIC LETTER HEH DOACHASHMEE}": "\N{ARABIC LETTER HEH}",
        "\N{ARABIC LETTER HEH GOAL}": "\N{ARABIC LETTER HEH}",
        "\N{ARABIC LETTER KEHEH}": "\N{ARABIC LETTER KAF}",
    }
)
FARSI_YEH_INSIDE_WORD = re.compile(r"\N{ARABIC LETTER FARSI YEH}(?=\w)")
# Three or more characters each followed by a single space: lettering spaced out for effect.
LETTER_SPACED = re.compile(r"(?<!\S)(?:\S ){2,}\S(?!\S)")
SPACES = re.compile(r" {2,}")
# The share of a line's letters in the other script that makes it a line in that direction.
OTHER_DIRECTION_SHARE = 0.6

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# Word stores a text box twice: as a modern shape and, under this element, as a fallback copy
# for older readers. Only the first is read.
FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
# Formatting, whose elements share names with content: a tab stop is a w:tab too.
PROPERTIES = (f"{W}pPr", f"{W}rPr")


class UnreadableDocumentError(ValueError):
    """The file is not a PDF or DOCX that can be read."""


def read_native_text(content: bytes) -> str:
    if content.startswith(PDF_SIGNATURE):
        return _pdf_text(content)
    if content.startswith(ZIP_SIGNATURE):
        return _docx_text(content)
    raise UnreadableDocumentError("the file is neither a PDF nor a DOCX")


def _pdf_text(content: bytes) -> str:
    # all_texts: some CV builders draw text inside figures, which pdfminer otherwise leaves as
    # loose characters rather than lines.
    layout = LAParams(all_texts=True)
    try:
        pages = list(extract_pages(io.BytesIO(content), maxpages=MAX_PAGES, laparams=layout))
    # A broken or hostile PDF fails inside pdfminer in many ways, and each means the same thing.
    except Exception as error:
        raise UnreadableDocumentError(f"the PDF cannot be read: {error}") from error
    lines = [_page_lines(page) for page in pages]
    backwards = stored_backwards(
        [word for page in lines for ln in page for word in ln.text.split()]
    )
    return "\n\n".join(_page_text(page, backwards) for page in lines).strip()


def _page_lines(page: LTPage) -> list[Line]:
    lines = []
    for item in _text_lines(page):
        text = _without_icons(item.get_text()).strip()
        if text:
            x0, y0, x1, y1 = item.bbox
            lines.append(
                Line(x0=x0, top=page.height - y1, x1=x1, bottom=page.height - y0, text=text)
            )
    return lines


def _text_lines(container: LTContainer[Any]) -> Iterator[LTTextLine]:
    for item in container:
        if isinstance(item, LTTextLine):
            yield item
        elif isinstance(item, LTContainer):
            yield from _text_lines(item)


def _without_icons(text: str) -> str:
    """Drops private-use characters: icon fonts draw a phone or an envelope with them."""
    return "".join(char for char in text if unicodedata.category(char) != "Co")


def _page_text(lines: list[Line], backwards: bool) -> str:
    right_to_left = _mostly_right_to_left(line.text for line in lines)
    rows = reading_order(lines, right_to_left=right_to_left)
    return "\n".join(
        "\t".join(_piece_text(piece.text, backwards, right_to_left) for piece in row)
        for row in rows
    )


def _piece_text(stored: str, backwards: bool, page_right_to_left: bool) -> str:
    if backwards and laid_out_right_to_left(stored):
        stored = logical_line(stored, right_to_left=_line_direction(stored, page_right_to_left))
    return _unspaced(readable(stored))


def _line_direction(stored: str, page_right_to_left: bool) -> bool:
    """A line is in the page's direction unless most of its letters are in the other script.

    A CV can set one Arabic item in an English page, or the reverse. Mostly, not merely more:
    an Arabic job title carrying its English name in brackets is still an Arabic line.
    """
    letters = [char for char in stored if char.isalpha()]
    other = sum(is_right_to_left(char) != page_right_to_left for char in letters)
    flipped = other >= OTHER_DIRECTION_SHARE * len(letters) > 0
    return page_right_to_left != flipped


def readable(text: str) -> str:
    """Presentation forms as letters, and Persian letter codes as the Arabic letters they draw.

    Fonts can map an Arabic glyph to its Persian twin: the yeh, heh and kaf look the same on the
    page, but a search or a comparison treats them as different letters. The Farsi yeh is dotted
    inside a word, as the Arabic yeh is, and dotless at its end, as the alef maksura is.
    """
    text = unicodedata.normalize("NFKC", text).translate(PERSIAN_LETTERS)
    text = FARSI_YEH_INSIDE_WORD.sub("\N{ARABIC LETTER YEH}", text)
    return text.replace("\N{ARABIC LETTER FARSI YEH}", "\N{ARABIC LETTER ALEF MAKSURA}")


def _unspaced(text: str) -> str:
    """Letter-spaced words ("P R O F I L E") joined, and runs of spaces made one.

    pdfminer adds a space wherever two glyphs sit apart, so spaced-out lettering comes out as
    single letters, which would split a year or a phone number into single digits.
    """
    text = LETTER_SPACED.sub(lambda match: match.group(0).replace(" ", ""), text)
    return SPACES.sub(" ", text)


def _mostly_right_to_left(texts: Iterator[str]) -> bool:
    letters = [char for text in texts for char in text if char.isalpha()]
    return sum(map(is_right_to_left, letters)) > len(letters) / 2


def _docx_text(content: bytes) -> str:
    document = _opened_docx(content)
    section = document.sections[0] if document.sections else None
    blocks: list[str] = []
    if section is not None and not section.header.is_linked_to_previous:
        blocks += _blocks(section.header.part.element)
    blocks += _blocks(document.element.body)
    if section is not None and not section.footer.is_linked_to_previous:
        blocks += _blocks(section.footer.part.element)
    return readable("\n".join(block for block in blocks if block.strip()))


def _opened_docx(content: bytes) -> DocxDocument:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            unpacked = sum(entry.file_size for entry in archive.infolist())
    except (zipfile.BadZipFile, OSError, ValueError) as error:
        raise UnreadableDocumentError(f"the DOCX is not a readable archive: {error}") from error
    # The sizes are the ones the archive declares, and zipfile never unpacks past them.
    if unpacked > MAX_DOCX_BYTES:
        raise UnreadableDocumentError("the DOCX unpacks to more than a CV could hold")
    try:
        return Document(io.BytesIO(content))
    # A broken or hostile archive fails in lxml or python-docx in many ways.
    except Exception as error:
        raise UnreadableDocumentError(f"the DOCX cannot be read: {error}") from error


def _blocks(container: Any) -> Iterator[str]:
    """Paragraph texts in document order, descending into tables and text boxes."""
    for child in container:
        if child.tag == f"{W}p":
            yield _paragraph_text(child)
            for box in _text_boxes(child):
                yield from _blocks(box)
        elif child.tag == f"{W}tbl":
            for row in child.iterchildren(f"{W}tr"):
                for cell in row.iterchildren(f"{W}tc"):
                    yield from _blocks(cell)
        elif child.tag == f"{W}sdt":
            for content in child.iterchildren(f"{W}sdtContent"):
                yield from _blocks(content)


def _paragraph_text(element: Any) -> str:
    parts: list[str] = []
    for child in element:
        if child.tag in (f"{W}txbxContent", FALLBACK, *PROPERTIES):
            continue
        if child.tag == f"{W}t":
            parts.append(child.text or "")
        elif child.tag == f"{W}tab":
            parts.append("\t")
        elif child.tag in (f"{W}br", f"{W}cr"):
            parts.append("\n")
        else:
            parts.append(_paragraph_text(child))
    return "".join(parts)


def _text_boxes(element: Any) -> Iterator[Any]:
    """The text boxes anchored in a paragraph. One inside another is read by _blocks."""
    for child in element:
        if child.tag == FALLBACK:
            continue
        if child.tag == f"{W}txbxContent":
            yield child
        else:
            yield from _text_boxes(child)
