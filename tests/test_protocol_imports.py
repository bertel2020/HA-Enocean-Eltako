"""The protocol layer must not import from homeassistant."""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts/check_protocol_imports.py"
_spec = importlib.util.spec_from_file_location("check_protocol_imports", _SCRIPT)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def test_protocol_layer_has_no_homeassistant_imports():
    assert check.find_violations() == []


def test_checker_detects_forbidden_imports(tmp_path):
    (tmp_path / "bad.py").write_text(
        "import homeassistant\n"
        "from homeassistant.core import HomeAssistant\n"
        "import homeassistantx\n"
    )
    (tmp_path / "ok.py").write_text("from . import homeassistant\nimport asyncio\n")
    assert [v.split(": ")[1] for v in check.find_violations(tmp_path)] == [
        "homeassistant",
        "homeassistant.core",
    ]
