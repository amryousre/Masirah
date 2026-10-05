"""The web's copy of the name spellings is the worker's (T069).

The web folds a search the way the worker folded each name into name_normalised. Its table and its
test examples are generated from domain/arabic.py by tools/export_name_spellings.py, so a change to
the table here that is not exported fails this test rather than silently breaking search.
"""

import json

from tools.export_name_spellings import EXAMPLES, SPELLINGS, examples, spellings


def test_the_web_has_the_current_spellings() -> None:
    assert json.loads(SPELLINGS.read_text(encoding="utf-8")) == spellings(), (
        "run `uv run python -m tools.export_name_spellings`"
    )


def test_the_web_tests_check_the_current_forms() -> None:
    assert json.loads(EXAMPLES.read_text(encoding="utf-8")) == examples(), (
        "run `uv run python -m tools.export_name_spellings`"
    )
