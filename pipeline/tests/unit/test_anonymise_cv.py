"""The CV anonymiser (T028): nothing identifying survives, and everything else does.

The CVs here are built on the fly around an invented person, so no real data enters the
repository to test the tool that keeps real data out of it.
"""

import json
from pathlib import Path

import pymupdf
import pytest

from tools import anonymise_cv
from tools.anonymise_cv import (
    CvPlan,
    _pattern,
    _rewrite_line,
    anonymise,
    find_leaks,
    find_losses,
    main,
    photo_pixels,
    run,
)

NAME = "Jane Placeholder"
EMAIL = "jane.placeholder@mail.test"
PHONE = "+20 100 555 0199"
EN_DASH, LIGATURE_FI = chr(0x2013), chr(0xFB01)
REPLACE = (
    (NAME, "Amal Fathy"),
    (EMAIL, "amal.fathy@example.com"),
    (PHONE, "+20 100 000 0001"),
)


def make_cv(path: Path) -> int:
    """One page with the person in text, letter-spaced text, metadata, a link and a photo."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), NAME, fontsize=20)
    # Tucked under the large name, inside the reach of its bounding box.
    page.insert_text((72, 82), "Alexandria / Miami", fontsize=8)
    page.insert_text((72, 96), "J a n e   P l a c e h o l d e r", fontsize=9)
    page.insert_text((72, 120), f"{EMAIL} | {PHONE}", fontsize=10)
    page.insert_text((72, 160), "Senior Engineer, Acme Industries, 2019 - present", fontsize=10)
    # One line, two spans: the name is split where the font changes, as many real CVs do.
    page.insert_text((72, 200), "Contact: Jane ", fontname="helv", fontsize=10)
    after = 72 + pymupdf.get_text_length("Contact: Jane ", fontname="helv", fontsize=10)
    page.insert_text((after, 200), "Placeholder, Cairo", fontname="tiro", fontsize=10)
    link = pymupdf.Rect(72, 110, 250, 124)
    page.insert_link({"kind": pymupdf.LINK_URI, "from": link, "uri": f"mailto:{EMAIL}"})
    photo = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 32, 32), False)
    for x in range(32):
        for y in range(32):
            photo.set_pixel(x, y, (x * 8, y * 8, 128))
    xref: int = page.insert_image(pymupdf.Rect(400, 50, 480, 130), pixmap=photo)
    # Places a person can hide outside the page text: notes, text boxes, attachments, form fields.
    page.add_text_annot((300, 300), f"Call {NAME}")
    page.add_freetext_annot(pymupdf.Rect(300, 320, 520, 340), f"Note: {NAME}")
    page.add_file_annot((300, 360), NAME.encode(), "contact.txt")
    field = pymupdf.Widget()
    field.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    field.field_name = "candidate"
    field.field_value = NAME
    field.rect = pymupdf.Rect(300, 380, 520, 400)
    page.add_widget(field)
    doc.set_metadata({"author": NAME, "title": f"{NAME} CV"})
    doc.save(path)
    return xref


@pytest.fixture
def plan(tmp_path: Path) -> CvPlan:
    source, output = tmp_path / "original.pdf", tmp_path / "anonymised.pdf"
    return CvPlan(source=source, output=output, replace=REPLACE, photos=(make_cv(source),))


def text_of(pdf: Path) -> str:
    return "".join(page.get_text() for page in pymupdf.open(pdf))


def test_identifiers_are_replaced_and_the_rest_survives(plan: CvPlan) -> None:
    assert run(plan) == []
    text = text_of(plan.output)
    for _, replacement in REPLACE:
        assert replacement in text
    assert "Senior Engineer, Acme Industries, 2019 - present" in text


def test_text_beside_a_replaced_value_survives(plan: CvPlan) -> None:
    run(plan)
    assert "Alexandria / Miami" in text_of(plan.output)


def test_losing_text_that_was_not_replaced_is_reported(plan: CvPlan) -> None:
    expected = anonymise(plan)
    assert "alexandria/miami" in expected
    doc = pymupdf.open(plan.output)
    doc[0].add_redact_annot(doc[0].search_for("Acme Industries")[0])
    doc[0].apply_redactions()
    damaged = plan.output.with_name("damaged.pdf")
    doc.save(damaged)
    assert find_losses(damaged, expected) == [
        "lost text: 'seniorengineer,acmeindustries,2019-present'"
    ]


def test_a_ligature_on_a_rewritten_line_becomes_plain_letters() -> None:
    spans = [{"text": f"Certi{LIGATURE_FI}cate No : JP-12345"}]
    rewrite = _rewrite_line(spans, [(_pattern("JP-12345"), "XX-00000")])
    assert rewrite == [(0, 0, "Certificate No : XX-00000")]


PATTERNS = [(_pattern(original), new) for original, new in REPLACE]


def test_values_in_separate_spans_are_rewritten_in_place() -> None:
    spans = [{"text": NAME}, {"text": "        "}, {"text": PHONE}]
    assert _rewrite_line(spans, PATTERNS) == [(0, 0, "Amal Fathy"), (2, 2, "+20 100 000 0001")]


def test_a_value_split_across_spans_merges_only_those_spans() -> None:
    spans = [{"text": "Contact: Jane "}, {"text": "Placeholder, Cairo"}, {"text": " | Giza"}]
    assert _rewrite_line(spans, PATTERNS) == [(0, 1, "Contact: Amal Fathy, Cairo")]


def test_a_replacement_the_font_cannot_draw_is_reported(plan: CvPlan) -> None:
    # The built-in fonts draw an en dash as a middle dot, silently.
    replace = ((NAME, f"Amal {EN_DASH} Fathy"), *REPLACE[1:])
    problems = run(CvPlan(plan.source, plan.output, replace=replace))
    assert problems
    assert all(p.startswith("lost text:") and EN_DASH in p for p in problems)
    assert not plan.output.exists()


def test_a_longer_replacement_is_fitted_to_the_original_width(tmp_path: Path) -> None:
    source = tmp_path / "links.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Site: jp.gd", fontname="helv", fontsize=10)
    after = 72 + pymupdf.get_text_length("Site: jp.gd", fontname="helv", fontsize=10)
    page.insert_text((after, 72), " | Cairo", fontname="tiro", fontsize=10)
    doc.save(source)
    longer = (("jp.gd", "jane-placeholder.example.com"),)
    plan = CvPlan(source, tmp_path / "out.pdf", replace=longer)
    assert run(plan) == []
    page = pymupdf.open(plan.output)[0]
    [site], [bar] = page.search_for("jane-placeholder.example.com"), page.search_for("|")
    assert site.x1 <= bar.x0 + 0.5, "the longer value would overlap the text after it"


def test_letter_spaced_text_is_matched_too(plan: CvPlan) -> None:
    run(plan)
    squeezed = "".join(text_of(plan.output).split()).casefold()
    assert "placeholder" not in squeezed


def test_metadata_links_and_the_photo_are_gone(plan: CvPlan) -> None:
    original = photo_pixels(plan.source, plan.photos)
    run(plan)
    doc = pymupdf.open(plan.output)
    assert doc.metadata is not None
    assert (doc.metadata["author"], doc.metadata["title"]) == ("", "")
    assert [link for page in doc for link in page.get_links()] == []
    kept = photo_pixels(plan.output, [image[0] for image in doc[0].get_images(full=True)])
    assert kept, "the photo slot keeps a placeholder so the layout is unchanged"
    assert not kept & original


def test_a_missed_identifier_is_reported(plan: CvPlan) -> None:
    anonymise(CvPlan(plan.source, plan.output, replace=REPLACE[:2], photos=plan.photos))
    leaks = find_leaks(plan.output, [NAME, EMAIL, PHONE])
    assert f"{PHONE!r} in text" in leaks
    assert all(leak.startswith(repr(PHONE)) for leak in leaks)


def test_an_untouched_cv_leaks_everywhere(plan: CvPlan) -> None:
    leaks = find_leaks(plan.source, [NAME, EMAIL], photo_pixels(plan.source, plan.photos))
    assert f"{NAME!r} in text" in leaks
    assert f"{NAME!r} in metadata" in leaks
    assert f"{EMAIL!r} in links" in leaks
    assert "an original photo is still embedded" in leaks
    assert "an annotation is still present" in leaks
    assert "a form field is still present" in leaks


def test_annotations_and_form_fields_are_removed(plan: CvPlan) -> None:
    assert run(plan) == []
    doc = pymupdf.open(plan.output)
    assert [annot.type for page in doc for annot in page.annots()] == []
    assert [widget.field_name for page in doc for widget in page.widgets()] == []


def test_a_crashing_check_leaves_no_unchecked_file(
    plan: CvPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    def crash(*_: object) -> list[str]:
        raise RuntimeError("the check itself failed")

    monkeypatch.setattr(anonymise_cv, "find_losses", crash)
    with pytest.raises(RuntimeError):
        run(plan)
    assert not plan.output.exists()


def test_the_command_reports_a_failing_cv_and_carries_on(
    plan: CvPlan, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = plan.source.parent
    entries = [
        {"source": "missing.pdf", "output": "first.pdf", "replace": []},
        {
            "source": plan.source.name,
            "output": "second.pdf",
            "replace": [list(pair) for pair in REPLACE],
            "photos": list(plan.photos),
        },
    ]
    (folder / "plan.json").write_text(json.dumps({"cvs": entries}), encoding="utf-8")
    output_dir = folder / "out"
    output_dir.mkdir()
    assert main([str(folder / "plan.json"), str(output_dir)]) == 1
    report = capsys.readouterr().out
    assert "first.pdf: FAILED" in report
    assert "second.pdf: clean" in report
    assert [path.name for path in output_dir.iterdir()] == ["second.pdf"]


def test_a_leaking_output_is_deleted_rather_than_kept(plan: CvPlan) -> None:
    missed = CvPlan(plan.source, plan.output, replace=REPLACE[:2], forbid=(PHONE,))
    assert run(missed) != []
    assert not plan.output.exists()
