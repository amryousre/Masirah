"""Adds the synthetic CVs and the simulated scans and photographs to the corpus (T028).

Run from pipeline/ after rendering the HTML sources:

    node tools/synthetic_cvs/render.mjs <raw folder>
    uv run python -m tools.build_synthetic_cvs <raw folder> tests/fixtures/cvs

Rendered PDFs lose their document metadata on the way in. Each copy is made from a native document
already in the corpus, and its labels are that document's labels with only the capture changed,
so a copy can never disagree with its source. Labels for the synthetic CVs themselves are written
by hand beside them, like the labels for the real ones.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pymupdf

from tools.simulate_capture import photograph, scan


@dataclass(frozen=True)
class Copy:
    name: str
    source: str
    capture: Literal["scanned", "photographed"]
    seed: int

    @property
    def suffix(self) -> str:
        return ".pdf" if self.capture == "scanned" else ".jpg"


DOCUMENT_LINE = re.compile(r'^  "document": \{.*\},$', re.MULTILINE)

COPIES = (
    Copy("en-scanned-01", "en-native-01", "scanned", 101),
    Copy("syn-ar-scanned-01", "syn-ar-native-03", "scanned", 102),
    Copy("syn-ar-photographed-01", "syn-ar-native-01", "photographed", 103),
    Copy("syn-en-photographed-01", "syn-en-native-01", "photographed", 104),
)


def add_rendered(raw: Path, corpus: Path) -> list[str]:
    """Copies each rendered PDF into the corpus without its title, author or other metadata."""
    added = []
    for pdf in sorted(raw.glob("syn-*.pdf")):
        doc = pymupdf.open(pdf)
        doc.set_metadata({})
        doc.del_xml_metadata()
        doc.save(corpus / pdf.name, garbage=4, deflate=True)
        added.append(pdf.name)
    return added


def add_copy(copy: Copy, corpus: Path) -> str:
    source = corpus / f"{copy.source}.pdf"
    output = corpus / f"{copy.name}{copy.suffix}"
    if copy.capture == "scanned":
        scan(source, output, copy.seed)
    else:
        photograph(source, output, copy.seed)
    text = source.with_suffix(".json").read_text(encoding="utf-8")
    document = json.loads(text)["document"] | {
        "capture": copy.capture,
        "pages": pymupdf.open(output).page_count,
        "copy_of": copy.source,
        "simulated": True,
    }
    # Only the document line changes, so the copy keeps its source's hand-kept layout.
    inline = "{ " + json.dumps(document, ensure_ascii=False)[1:-1] + " }"
    text, replaced = DOCUMENT_LINE.subn(f'  "document": {inline},', text, count=1)
    if replaced != 1:
        raise ValueError(f"{source.stem}.json has no one-line document entry to rewrite")
    output.with_suffix(".json").write_text(text, encoding="utf-8")
    return output.name


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    raw, corpus = Path(argv[0]), Path(argv[1])
    for name in add_rendered(raw, corpus):
        print(f"{name}: rendered")
    for copy in COPIES:
        print(f"{add_copy(copy, corpus)}: {copy.capture} copy of {copy.source}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
