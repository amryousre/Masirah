"""Anonymise a CV before it enters the repository (T028).

Replaces identifying values span by span, keeping each span's position, size and colour, swaps
photographs for a blank placeholder, and drops every link, annotation, form field and attachment
and all metadata. The result is then re-read and must contain none of the original values in its
text, metadata, links or raw objects, none of the original photo pixels, and no annotation or form
field. An output that fails, or that cannot be checked, is deleted rather than kept.

The plan names the real values, so it lives outside the repository beside the originals:

    uv run python -m tools.anonymise_cv <plan.json> tests/fixtures/cvs

    {"cvs": [{"source": "original.pdf", "output": "en-native-01.pdf",
              "replace": [["Real Name", "Invented Name"]], "forbid": ["surname"], "photos": [42]}]}

Sources resolve against the plan's folder and outputs against the output folder. "forbid" lists
values that must not survive beyond those already being replaced, and "photos" lists image xrefs.
"""

import hashlib
import json
import re
import sys
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf

_BOLD, _SERIF, _ITALIC = 16, 4, 2
_BASE14 = {  # (serif, bold, italic) -> built-in font; replacements are Latin text only
    (False, False, False): "helv",
    (False, True, False): "hebo",
    (False, False, True): "heit",
    (False, True, True): "hebi",
    (True, False, False): "tiro",
    (True, True, False): "tibo",
    (True, False, True): "tiit",
    (True, True, True): "tibi",
}


@dataclass(frozen=True)
class CvPlan:
    source: Path
    output: Path
    replace: tuple[tuple[str, str], ...]
    forbid: tuple[str, ...] = ()
    photos: tuple[int, ...] = ()

    @property
    def forbidden(self) -> tuple[str, ...]:
        return tuple(original for original, _ in self.replace) + self.forbid


def normalise(text: str) -> str:
    """Letters and digits only, case-folded: spacing and punctuation cannot hide a match."""
    return "".join(char for char in text.casefold() if char.isalnum())


def _squeeze(text: str) -> str:
    """Whitespace removed but punctuation kept, so a dash drawn as a dot still counts as lost."""
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def _pattern(original: str) -> re.Pattern[str]:
    """Matches the value even when the PDF letter-spaces it ("J a n e")."""
    chars = [re.escape(char) for char in original if not char.isspace()]
    return re.compile(r"\s*".join(chars), re.IGNORECASE)


def _literally(replacement: str) -> Callable[[re.Match[str]], str]:
    """A replacement function, so backslashes in the new value are never read as group refs."""
    return lambda _: replacement


def _font(flags: int) -> str:
    return _BASE14[(bool(flags & _SERIF), bool(flags & _BOLD), bool(flags & _ITALIC))]


Patterns = list[tuple[re.Pattern[str], str]]


def _rewrite_line(spans: list[dict[str, Any]], patterns: Patterns) -> list[tuple[int, int, str]]:
    """Matches against the whole line, since a value is often split where the font changes.

    Returns the runs of spans to rewrite, each with its new text. A span holding a whole match is
    rewritten alone, in place; spans merge only where a match crosses between them, so the rest
    of the line keeps its layout.
    """
    joined = "".join(span["text"] for span in spans)
    bounds, offset = [], 0
    for span in spans:
        bounds.append((offset, offset + len(span["text"])))
        offset += len(span["text"])
    runs = []
    for pattern, _ in patterns:
        for match in pattern.finditer(joined):
            start, end = match.span()
            touched = [i for i, (a, b) in enumerate(bounds) if start < b and a < end]
            runs.append((touched[0], touched[-1]))
    merged: list[list[int]] = []
    for first, last in sorted(runs):
        if merged and first <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], last)
        else:
            merged.append([first, last])
    rewrites = []
    for first, last in merged:
        text = joined[bounds[first][0] : bounds[last][1]]
        for pattern, replacement in patterns:
            text = pattern.sub(_literally(replacement), text)
        # The redrawing font has no ligature glyphs, so "ﬁ" is written as the plain "fi".
        rewrites.append((first, last, unicodedata.normalize("NFKC", text)))
    return rewrites


def _glyph_band(span: dict[str, Any]) -> pymupdf.Rect:
    """A band through the middle of the span's glyphs rather than its full bounding box.

    A large heading's box reaches well below its baseline, so redacting the whole box also
    removes a small line tucked underneath it. Every character of the span still crosses the band.
    """
    x0, _, x1, _ = span["bbox"]
    baseline, size = span["origin"][1], span["size"]
    return pymupdf.Rect(x0 + 0.1, baseline - 0.6 * size, x1 - 0.1, baseline - 0.1 * size)


def _draw(page: pymupdf.Page, span: dict[str, Any], text: str, width: float) -> None:
    """Writes the new text in the span's style, narrowed if it is wider than what it replaces,
    so it cannot overlap the text after it and blur the layout the extraction is tested on.
    """
    font, size = _font(span["flags"]), span["size"]
    natural = pymupdf.get_text_length(text, fontname=font, fontsize=size)
    origin = pymupdf.Point(span["origin"])
    morph = (origin, pymupdf.Matrix(width / natural, 1)) if natural > width > 0 else None
    page.insert_text(
        origin,
        text,
        fontsize=size,
        fontname=font,
        color=pymupdf.sRGB_to_pdf(span["color"]),
        morph=morph,
    )


def _rewrite_page(page: pymupdf.Page, patterns: Patterns) -> list[str]:
    """Rewrites the page and returns every line's intended text, for find_losses."""
    rewrites: list[tuple[dict[str, Any], str, float]] = []
    expected: list[str] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            runs = _rewrite_line(spans, patterns)
            rewritten = {i for first, last, _ in runs for i in range(first, last + 1)}
            if not runs:
                expected.append(_squeeze("".join(span["text"] for span in spans)))
            expected += [_squeeze(s["text"]) for i, s in enumerate(spans) if i not in rewritten]
            for first, last, text in runs:
                expected.append(_squeeze(text))
                for span in spans[first : last + 1]:
                    page.add_redact_annot(_glyph_band(span), fill=False)
                width = spans[last]["bbox"][2] - spans[first]["bbox"][0]
                rewrites.append((spans[first], text, width))
    # Text only: backgrounds, rules and images under a redacted span stay exactly as they were.
    page.apply_redactions(
        images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE
    )
    for span, text, width in rewrites:
        if text.strip():
            _draw(page, span, text, width)
    for link in page.get_links():
        page.delete_link(link)
    # Notes, text boxes, attachments and form fields can each hold a person, outside the text.
    annot = page.first_annot
    while annot:
        annot = page.delete_annot(annot)
    widget = page.first_widget
    while widget:
        widget = page.delete_widget(widget)
    return [text for text in expected if text]


def _blank_photos(doc: pymupdf.Document, photos: Iterable[int]) -> None:
    placeholder = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 8, 8), False)
    placeholder.clear_with(0xDD)
    for xref in photos:
        page = next(p for p in doc if any(image[0] == xref for image in p.get_images(full=True)))
        page.replace_image(xref, pixmap=placeholder)


def anonymise(plan: CvPlan) -> list[str]:
    """Writes the anonymised CV and returns the text every line should now read, squeezed."""
    patterns = [(_pattern(original), new) for original, new in plan.replace]
    doc = pymupdf.open(plan.source)
    expected = [text for page in doc for text in _rewrite_page(page, patterns)]
    _blank_photos(doc, plan.photos)
    for name in doc.embfile_names():
        doc.embfile_del(name)
    doc.set_toc([])
    doc.set_metadata({})
    doc.del_xml_metadata()
    doc.save(plan.output, garbage=4, deflate=True, clean=True)
    return expected


def _all_text(doc: pymupdf.Document) -> str:
    """Both reading orders, so a value split across blocks is still seen whole."""
    return "".join(page.get_text() for page in doc) + "".join(
        page.get_text(sort=True) for page in doc
    )


def find_losses(pdf: Path, expected: Iterable[str]) -> list[str]:
    """Every line must read as intended: a redaction box can reach a neighbouring line, and the
    redrawing font silently draws a character it lacks, such as an en dash, as a dot.
    """
    haystack = _squeeze(_all_text(pymupdf.open(pdf)))
    return [f"lost text: {text!r}" for text in dict.fromkeys(expected) if text not in haystack]


def photo_pixels(pdf: Path, xrefs: Iterable[int]) -> set[str]:
    """Digests of image pixels, so a photo is recognised however its stream is encoded."""
    doc = pymupdf.open(pdf)
    return {hashlib.sha256(pymupdf.Pixmap(doc, xref).samples).hexdigest() for xref in xrefs}


def _raw_objects(doc: pymupdf.Document) -> str:
    parts = []
    for xref in range(1, doc.xref_length()):
        parts.append(doc.xref_object(xref, compressed=False))
        if doc.xref_is_stream(xref) and doc.xref_get_key(xref, "Subtype")[1] != "/Image":
            parts.append(doc.xref_stream(xref).decode("latin-1"))
    return "".join(parts)


def find_leaks(pdf: Path, forbidden: Iterable[str], photos: Iterable[str] = ()) -> list[str]:
    doc = pymupdf.open(pdf)
    metadata = doc.metadata or {}
    haystacks = {
        "text": normalise(_all_text(doc)),
        "metadata": normalise(
            "".join(str(value) for value in metadata.values()) + doc.get_xml_metadata()
        ),
        "links": normalise("".join(str(ln.get("uri", "")) for p in doc for ln in p.get_links())),
        "raw objects": normalise(_raw_objects(doc)),
    }
    leaks = [
        f"{value!r} in {where}"
        for value in forbidden
        for where, haystack in haystacks.items()
        if normalise(value) in haystack
    ]
    images = [image[0] for page in doc for image in page.get_images(full=True)]
    if photo_pixels(pdf, images) & set(photos):
        leaks.append("an original photo is still embedded")
    if doc.embfile_count():
        leaks.append("an attachment is still embedded")
    if any(page.first_annot for page in doc):
        leaks.append("an annotation is still present")
    if any(page.first_widget for page in doc) or doc.is_form_pdf:
        leaks.append("a form field is still present")
    return leaks


def run(plan: CvPlan) -> list[str]:
    """Anonymise, then prove it. An output that leaks, is damaged, or could not be checked at all
    is deleted, so nothing unverified is left where it could be committed.
    """
    try:
        originals = photo_pixels(plan.source, plan.photos)
        expected = anonymise(plan)
        leaks = find_leaks(plan.output, plan.forbidden, originals)
        problems = leaks + find_losses(plan.output, expected)
    except BaseException:
        plan.output.unlink(missing_ok=True)
        raise
    if problems:
        plan.output.unlink()
    return problems


def _plan(entry: dict[str, Any], plan_file: Path, output_dir: Path) -> CvPlan:
    return CvPlan(
        source=plan_file.parent / entry["source"],
        output=output_dir / entry["output"],
        replace=tuple((original, new) for original, new in entry["replace"]),
        forbid=tuple(entry.get("forbid", ())),
        photos=tuple(entry.get("photos", ())),
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    plan_file, output_dir = Path(argv[0]), Path(argv[1])
    entries: list[Any] = json.loads(plan_file.read_text(encoding="utf-8"))["cvs"]
    failed = 0
    for number, entry in enumerate(entries, 1):
        has_output = isinstance(entry, dict) and isinstance(entry.get("output"), str)
        name = entry["output"] if has_output else f"entry {number}"
        # Parsing sits inside the boundary too: one malformed entry must not stop the rest.
        try:
            problems = run(_plan(entry, plan_file, output_dir))
        except Exception as error:
            problems = [f"could not be processed: {type(error).__name__}: {error}"]
        failed += bool(problems)
        # The report can name original values, so it goes to the local terminal only.
        print(f"{name}: {'FAILED ' + '; '.join(problems) if problems else 'clean'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
