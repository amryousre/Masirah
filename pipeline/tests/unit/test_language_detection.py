"""Language detection (T039, SC-015, ADR 0005).

Version 1.0 supports Arabic and English. A CV in another language is flagged unsupported rather
than parsed, and a supported CV with a minority of third-language text is not flagged on the
strength of it.
"""

import json
from pathlib import Path

import pytest

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.domain.language import detect_language

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"
NATIVE = [
    path
    for path in sorted(CORPUS.glob("*.pdf"))
    if json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))["document"]["capture"]
    == "native"
]


def labelled(path: Path) -> tuple[str, bool]:
    labels = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    return labels["document"]["language"], labels["expected"] == "parsed"


@pytest.mark.parametrize("pdf", NATIVE, ids=lambda path: path.stem)
def test_every_corpus_cv_gets_its_labelled_language(pdf: Path) -> None:
    language, supported = labelled(pdf)
    verdict = detect_language(read_native_text(pdf.read_bytes()))
    assert (verdict.language, verdict.supported) == (language, supported)


def test_an_english_cv_with_a_few_french_lines_is_supported() -> None:
    """SC-015: syn-en-native-01 carries two French sentences among its English."""
    text = read_native_text((CORPUS / "syn-en-native-01.pdf").read_bytes())
    assert "Je rédige" in text
    assert detect_language(text).supported


@pytest.mark.parametrize(
    ("text", "language"),
    [
        (
            "Experiencia profesional\nResponsable de ventas en la empresa con más de diez años de "
            "experiencia y gestión de los clientes para el mercado del país.",
            "es",
        ),
        (
            "Berufserfahrung\nLeiter der Abteilung für Vertrieb und Marketing mit Verantwortung "
            "für die Planung und den Ausbau der Kundenbeziehungen im Unternehmen.",
            "de",
        ),
        (
            "سوابق کاری\nمدیر فروش در شرکت با بیش از ده سال تجربه است و برای مشتریان این شرکت "
            "گزارش‌های ماهانه را آماده می‌کند.",
            "fa",
        ),
    ],
    ids=["spanish", "german", "persian"],
)
def test_a_cv_in_another_language_is_unsupported(text: str, language: str) -> None:
    verdict = detect_language(text)
    assert not verdict.supported
    assert verdict.language == language


def test_text_with_nothing_to_go_on_is_not_flagged() -> None:
    """Names, numbers and skill lists say nothing about language; flagging needs evidence."""
    verdict = detect_language("Karim Nassar\n0100 000 0207\nSQL, Excel, Power BI\n2015 - 2019")
    assert verdict.supported


def test_empty_text_is_not_flagged() -> None:
    assert detect_language("").supported


@pytest.mark.parametrize(
    ("text", "language"),
    [
        # A short French CV with no function words at all.
        (
            "Expérience professionnelle\nResponsable commercial gestion clientèle\n"
            "Développement stratégie commerciale",
            "fr",
        ),
        # A short Persian CV whose lines each hold too little to decide alone.
        ("سوابق تحصیلی\nمدیر پروژه در شرکت بزرگ\nمسئول تیم فروش و توسعه", "fa"),
        # Another script altogether.
        ("Опыт работы\nРуководитель крупных проектов", "other"),  # noqa: RUF001 Cyrillic on purpose
    ],
    ids=["short-french", "short-persian", "cyrillic"],
)
def test_a_short_cv_in_another_language_is_unsupported(text: str, language: str) -> None:
    verdict = detect_language(text)
    assert (verdict.language, verdict.supported) == (language, False)


def test_digits_are_not_letters_of_either_script() -> None:
    """A phone number in Arabic-Indic digits does not make an English CV Arabic."""
    assert detect_language("Ahmed Ali\n٠١٢٣٤٥٦٧٨٩\nSQL").language == "en"


def test_a_short_urdu_cv_is_unsupported() -> None:
    """Urdu's heh goal and its word for and, which neither Arabic nor Persian uses."""
    verdict = detect_language("تجربہ اور مہارت\nتعلیم اور ملازمت")
    assert (verdict.language, verdict.supported) == ("ur", False)
