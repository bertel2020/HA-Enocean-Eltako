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


def test_five_blueprints() -> None:
    assert len(BLUEPRINTS) == 5
