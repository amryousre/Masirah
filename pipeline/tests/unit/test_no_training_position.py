"""Each model provider has a documented no-training position before it is enabled (T094, AI-09).

The position is contractual, so it cannot be checked at runtime. It is checked here instead: a
provider the registry can configure fails this test until the adapters README records its terms,
when they were read, and that they rule out training on what is sent.
"""

import re
from pathlib import Path

import pytest

from masirah_pipeline.adapters.provider_registry import KEY_VARIABLES

README = Path(__file__).parents[2] / "src" / "masirah_pipeline" / "adapters" / "README.md"


def _sections() -> dict[str, str]:
    text = README.read_text(encoding="utf-8")
    parts = re.split(r"^### ", text, flags=re.MULTILINE)[1:]
    return {part.splitlines()[0].strip(): part for part in parts}


@pytest.mark.parametrize("provider", sorted(KEY_VARIABLES))
def test_each_configurable_provider_has_a_position(provider: str) -> None:
    section = _sections().get(provider)
    assert section is not None, f"the adapters README has no position for {provider}"
    assert re.search(r"^- \*\*Trains on what Masirah sends:\*\* no\b", section, re.MULTILINE)
    assert re.search(r"^- \*\*Checked:\*\* \d{1,2} \w+ \d{4}\b", section, re.MULTILINE)
    assert re.search(r"^- \*\*Terms:\*\* .*https://", section, re.MULTILINE)


def test_the_readme_names_no_provider_the_registry_cannot_configure() -> None:
    assert set(_sections()) == set(KEY_VARIABLES)
