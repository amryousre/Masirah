"""Constitution II: domain and ports never import adapters or infrastructure.

Each case copies the real package into a temporary directory, adds one module, and runs
the real contracts from pyproject.toml against the copy. The working tree is never touched.
"""

import shutil
import sys
from pathlib import Path

import pytest
from importlinter.cli import lint_imports

PIPELINE_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "masirah_pipeline"
CONTRACTS_KEPT = 0


def lint_package_with(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: str, source: str
) -> int:
    copy = tmp_path / PACKAGE
    shutil.copytree(
        PIPELINE_ROOT / "src" / PACKAGE, copy, ignore=shutil.ignore_patterns("__pycache__")
    )
    (copy / module).write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)
    for name in [n for n in sys.modules if n == PACKAGE or n.startswith(f"{PACKAGE}.")]:
        monkeypatch.delitem(sys.modules, name)
    return lint_imports(
        config_filename=str(PIPELINE_ROOT / "pyproject.toml"), no_cache=True, no_logo=True
    )


def test_adapters_may_import_domain_and_ports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "from masirah_pipeline import domain, ports\n"
    assert lint_package_with(tmp_path, monkeypatch, "adapters/probe.py", source) == CONTRACTS_KEPT


@pytest.mark.parametrize(
    ("module", "source"),
    [
        ("domain/probe.py", "import masirah_pipeline.adapters\n"),
        ("domain/probe.py", "from masirah_pipeline import adapters\n"),
        ("domain/probe.py", "from .. import adapters\n"),
        ("domain/probe.py", "import anthropic\n"),
        ("domain/probe.py", "from supabase import create_client\n"),
        ("ports/probe.py", "from masirah_pipeline import adapters\n"),
    ],
    ids=[
        "domain-absolute",
        "domain-from",
        "domain-relative",
        "domain-provider",
        "domain-db",
        "ports",
    ],
)
def test_inner_layers_may_not_import_outward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module: str, source: str
) -> None:
    assert lint_package_with(tmp_path, monkeypatch, module, source) != CONTRACTS_KEPT
