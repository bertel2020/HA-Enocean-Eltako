"""icons.json covers every translated entity and every action."""

import json
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/enocean_eltako"


def test_every_translated_entity_has_an_icon() -> None:
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    icons = json.loads((COMPONENT / "icons.json").read_text(encoding="utf-8"))
    for platform, keys in strings["entity"].items():
        assert set(icons["entity"][platform]) == set(keys), platform
    for platform in icons["entity"].values():
        for icon in platform.values():
            assert icon["default"].startswith("mdi:")
    assert set(icons["services"]) == set(strings["services"])
