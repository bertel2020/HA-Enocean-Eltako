"""Real captures in tests/fixtures/captures mark catalog models as checked on hardware."""

import json
from pathlib import Path

import pytest

from custom_components.enocean_eltako.catalog import CATALOG

CAPTURES = Path(__file__).parent / "fixtures" / "captures"
FILES = sorted(CAPTURES.glob("*.jsonl"))
KEYS = {"time", "gateway", "dir", "rorg", "data", "sender", "status", "destination", "dbm"}


def test_capture_directory_exists() -> None:
    assert CAPTURES.is_dir()


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_capture_belongs_to_a_catalog_model(path: Path) -> None:
    assert path.stem in CATALOG
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines
    assert all(KEYS <= json.loads(line).keys() for line in lines)
