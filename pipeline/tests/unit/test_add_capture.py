"""Adding a real scan or phone photo to the corpus (T028) leaves no camera metadata behind."""

import io
import json
import shutil
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from tools.add_capture import CORPUS, add_capture, main

SOURCE = "en-native-03"

# EXIF tags a phone writes: make, model, artist (often the owner), and the GPS block.
MAKE, MODEL, ARTIST, ORIENTATION, GPS = 0x010F, 0x0110, 0x013B, 0x0112, 0x8825


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    for suffix in (".pdf", ".json"):
        shutil.copy(CORPUS / f"{SOURCE}{suffix}", tmp_path / f"{SOURCE}{suffix}")
    return tmp_path


def phone_photo(folder: Path, name: str, *, rotated: bool = False) -> Path:
    """A photo as a phone saves it: EXIF with device, owner and place, stored sideways if asked."""
    # Stored landscape with orientation 6 means the phone was held upright: portrait on screen.
    picture = Image.new("RGB", (400, 300) if rotated else (300, 400), (240, 238, 230))
    exif = Image.Exif()
    exif[MAKE] = "PhoneMaker"
    exif[MODEL] = "Model X"
    exif[ARTIST] = "Owner Name"
    exif[ORIENTATION] = 6 if rotated else 1
    exif.get_ifd(GPS)[2] = (30.0, 2.0, 40.0)  # GPSLatitude
    path = folder / f"{name}.jpg"
    picture.save(path, "JPEG", exif=exif.tobytes(), comment=b"taken at home")
    with Image.open(path) as saved:
        assert saved.getexif()[ARTIST] == "Owner Name"
    return path


def embedded_images(pdf: Path) -> list[Image.Image]:
    document = pymupdf.open(pdf)
    images: list[Image.Image] = []
    for page in document:
        for xref, *_ in page.get_images():
            images.append(Image.open(io.BytesIO(document.extract_image(xref)["image"])))
    return images


def test_makes_one_image_only_pdf_page_per_photo(corpus: Path, tmp_path: Path) -> None:
    photos = [phone_photo(tmp_path, "p1"), phone_photo(tmp_path, "p2")]
    output = add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    document = pymupdf.open(output)
    assert document.page_count == 2
    assert "".join(page.get_text() for page in document).strip() == ""


def test_no_camera_metadata_survives(corpus: Path, tmp_path: Path) -> None:
    photos = [phone_photo(tmp_path, "p1")]
    output = add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    for image in embedded_images(output):
        assert not image.getexif()
        assert not {"exif", "xmp", "comment"} & set(image.info)
    document = pymupdf.open(output)
    assert not any((document.metadata or {}).get(key) for key in ("author", "title", "creator"))
    assert not document.get_xml_metadata()
    assert b"Owner Name" not in output.read_bytes()
    assert b"PhoneMaker" not in output.read_bytes()


def test_a_sideways_photo_is_turned_upright(corpus: Path, tmp_path: Path) -> None:
    photos = [phone_photo(tmp_path, "p1", rotated=True)]
    output = add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    page = pymupdf.open(output)[0]
    assert page.rect.height > page.rect.width
    (image,) = embedded_images(output)
    assert image.height > image.width


def test_labels_are_the_sources_with_only_the_capture_changed(corpus: Path, tmp_path: Path) -> None:
    photos = [phone_photo(tmp_path, "p1"), phone_photo(tmp_path, "p2")]
    output = add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    source = json.loads((corpus / f"{SOURCE}.json").read_text(encoding="utf-8"))
    copy = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    assert copy["document"] == source["document"] | {
        "capture": "photographed",
        "copy_of": SOURCE,
        "simulated": False,
        "pages": 2,
    }
    for key in ("expected", "profile", "protected"):
        assert copy[key] == source[key]
    assert b"\r\n" not in output.with_suffix(".json").read_bytes()


def test_refuses_to_overwrite_or_to_copy_a_copy(corpus: Path, tmp_path: Path) -> None:
    photos = [phone_photo(tmp_path, "p1")]
    add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    with pytest.raises(FileExistsError):
        add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    with pytest.raises(ValueError, match="itself a capture"):
        add_capture("en-photographed-01", "scanned", "en-scanned-09", photos, corpus)


def test_labels_that_cannot_be_copied_leave_no_pdf(corpus: Path, tmp_path: Path) -> None:
    """Otherwise the corpus would hold a capture without labels, and a retry would be refused."""
    labels = corpus / f"{SOURCE}.json"
    document = json.loads(labels.read_text(encoding="utf-8"))
    labels.write_text(json.dumps(document, indent=2), encoding="utf-8")  # no one-line entry
    photos = [phone_photo(tmp_path, "p1")]
    with pytest.raises(ValueError, match="one-line document entry"):
        add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    assert not (corpus / "en-photographed-01.pdf").exists()


def test_a_failed_label_write_takes_back_both_files(
    corpus: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def full_disk(output: Path, text: str) -> None:
        output.with_suffix(".json").write_text(text[:40], encoding="utf-8")  # partway, then fails
        raise OSError("no space left on device")

    monkeypatch.setattr("tools.add_capture.write_labels", full_disk)
    photos = [phone_photo(tmp_path, "p1")]
    with pytest.raises(OSError, match="no space"):
        add_capture(SOURCE, "photographed", "en-photographed-01", photos, corpus)
    assert not (corpus / "en-photographed-01.pdf").exists()
    assert not (corpus / "en-photographed-01.json").exists()


def test_a_label_file_already_there_is_never_overwritten_or_removed(
    corpus: Path, tmp_path: Path
) -> None:
    stray = corpus / "en-photographed-01.json"
    stray.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match=r"en-photographed-01\.json"):
        add_capture(
            SOURCE, "photographed", "en-photographed-01", [phone_photo(tmp_path, "p1")], corpus
        )
    assert stray.read_text(encoding="utf-8") == "{}"
    assert not (corpus / "en-photographed-01.pdf").exists()


def test_runs_from_the_command_line(corpus: Path, tmp_path: Path) -> None:
    photo = str(phone_photo(tmp_path, "p1"))
    assert main([SOURCE, "scanned", "en-scanned-02", photo, "--corpus", str(corpus)]) == 0
    assert (corpus / "en-scanned-02.pdf").exists()
    assert main([SOURCE, "faxed", "en-faxed-01", photo, "--corpus", str(corpus)]) == 2
    assert main([SOURCE, "scanned", "en-scanned-03", photo, "--corpus"]) == 2
