"""Writes the web's copy of the name spellings, and the examples its tests must match (T069).

Run from pipeline/ whenever domain/arabic.py's tables change:

    uv run python -m tools.export_name_spellings

The web folds a recruiter's search the way the worker folded each candidate's name into
name_normalised, or a search for Mohamed would miss Mohammed. Python is the source: this writes
web/lib/domain/name-spellings.json (every listed spelling mapped to its name's Arabic form, with
the Abd prefixes and the Latin articles) and web/tests/unit/fixtures/name-examples.json (names
with the form Python gives them). tests/unit/test_name_spellings_export.py fails while either file
is out of date, and the web's tests fail while its port gives any example a different form.
"""

import json
from pathlib import Path

from masirah_pipeline.domain.arabic import ABD_PREFIXES, CANONICAL, LATIN_ARTICLES, name_normalised

WEB = Path(__file__).resolve().parents[2] / "web"
SPELLINGS = WEB / "lib" / "domain" / "name-spellings.json"
EXAMPLES = WEB / "tests" / "unit" / "fixtures" / "name-examples.json"

# Each one exercises a rule: listed names in both scripts, marks and letter variants, the Abd
# compounds, the article, doubled letters, unlisted names, case, spacing and punctuation.
EXAMPLE_NAMES = (
    "Mohamed",
    "Mohammed",
    "Muhammad",
    "محمد",
    "مُحَمَّد",
    "Mahmoud",
    "محمود",
    "Ahmed",
    "احمد",
    "أحمد",
    "Hassan",
    "Hussein",
    "حسين",
    "Amr",
    "Omar",
    "Fatma",
    "فاطمه",
    "Mostafa",
    "مصطفي",
    "Abdel Rahman",
    "Abdelrahman",
    "Abd El Rahman",
    "Abdul Rahman",
    "عبد الرحمن",
    "عبدالرحمن",
    "Abdallah",
    "Abdullah",
    "عبد الله",
    "El Sayed",
    "Elsayed",
    "السيد",
    "El Shafei",
    "Shafei",
    "Hanna",
    "Hana",
    "Hossam",
    "Zeyad Khalil",
    "MOHAMED  ahmed-HASSAN",
    "Mohamed Ahmed El Sayed",
    "محمد أحمد السيد",
    "Yasmin Farouk",
    "ياسمين فاروق",
    "Renée",
    "Straße",
    "123",
    "",
)


def spellings() -> dict[str, object]:
    return {
        "spellings": dict(sorted(CANONICAL.items())),
        "abdPrefixes": list(ABD_PREFIXES),
        "latinArticles": sorted(LATIN_ARTICLES),
    }


def examples() -> list[list[str]]:
    return [[name, name_normalised(name)] for name in EXAMPLE_NAMES]


def as_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    EXAMPLES.parent.mkdir(parents=True, exist_ok=True)
    SPELLINGS.write_text(as_json(spellings()), encoding="utf-8", newline="\n")
    EXAMPLES.write_text(as_json(examples()), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
