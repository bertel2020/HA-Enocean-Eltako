"""The shipped blueprints load and validate."""

from pathlib import Path

import pytest
from homeassistant.components.blueprint import models
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.util.yaml import load_yaml

BLUEPRINTS = sorted(
    (Path(__file__).parents[1] / "blueprints/automation/enocean_eltako").glob("*.yaml")
)


@pytest.mark.parametrize("path", BLUEPRINTS, ids=lambda p: p.stem)
def test_blueprint_is_valid(path: Path) -> None:
    data = load_yaml(path)
    BLUEPRINT_SCHEMA(data)
    blueprint = models.Blueprint(data, expected_domain="automation", schema=BLUEPRINT_SCHEMA)
    assert blueprint.inputs


def test_seven_blueprints() -> None:
    assert len(BLUEPRINTS) == 7


def _strings(node: object):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


@pytest.mark.parametrize("path", BLUEPRINTS, ids=lambda p: p.stem)
def test_blueprint_templates_parse(path: Path) -> None:
    """Every template in a blueprint is valid Jinja (the rest only shows at runtime)."""
    from jinja2 import Environment

    data = load_yaml(path)
    for text in _strings({k: v for k, v in data.items() if k != "blueprint"}):
        if "{{" in text or "{%" in text:
            Environment().parse(text)
