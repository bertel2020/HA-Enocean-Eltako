"""strings.json is the source of the translations: en and de have exactly its keys."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent / "custom_components" / "enocean_eltako"


def _keys(node: object, path: str = "") -> set[str]:
    if not isinstance(node, dict):
        return {path}
    return set().union(*(_keys(v, f"{path}.{k}") for k, v in node.items())) or {path}


@pytest.mark.parametrize("language", ["en", "de"])
def test_translation_keys_match_strings(language: str) -> None:
    source = _keys(json.loads((ROOT / "strings.json").read_text(encoding="utf-8")))
    path = ROOT / "translations" / f"{language}.json"
    translated = _keys(json.loads(path.read_text(encoding="utf-8")))
    assert sorted(translated - source) == []
    assert sorted(source - translated) == []
