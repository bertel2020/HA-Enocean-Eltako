"""Every catalog profile has test telegrams (E12) and the device docs match the catalog."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from custom_components.enocean_eltako.catalog import (
    CATALOG,
    CATEGORIES,
    EEP_OPTIONS,
    EEP_TO_MODEL,
    GROUPS,
    categories_of,
)
from custom_components.enocean_eltako.protocol.eep import EEPRef
from custom_components.enocean_eltako.protocol.eep.codecs import decode_telegram
from custom_components.enocean_eltako.protocol.eep.teach_in import MANUFACTURER_ELTAKO, TeachIn4BS
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg
from custom_components.enocean_eltako.subentry_flow import candidates

ID = 0x05000001

# one known-good telegram per receive profile: (RORG, data, status)
SAMPLES: dict[str, tuple[int, str, int]] = {
    "M5-38-08:eltako": (Rorg.RPS, "70", 0x30),
    "A5-38-08:eltako": (Rorg.BS4, "02320009", 0),
    "G5-3F-7F:eltako": (Rorg.RPS, "70", 0x30),
    "D2-01-09:std": (0xD2, "0460E4", 0),
    "A5-12-01:std": (Rorg.BS4, "00100009", 0),
    "A5-12-01:eltako": (Rorg.BS4, "00100009", 0),
    "A5-12-02:eltako": (Rorg.BS4, "00303909", 0),
    "A5-12-03:eltako": (Rorg.BS4, "00000F0D", 0),
    "F6-10-00:std": (Rorg.RPS, "F0", 0x20),
    "D5-00-01:std": (Rorg.BS1, "09", 0),
    "F6-02-01:std": (Rorg.RPS, "70", 0x30),
    "A5-04-02:std": (Rorg.BS4, "007D7D08", 0),
    "A5-08-01:eltako": (Rorg.BS4, "00800009", 0),
    "A5-09-04:std": (Rorg.BS4, "40606008", 0),
    "M5-10-06:eltako": (Rorg.RPS, "70", 0x30),
    "A5-10-06:eltako": (Rorg.BS4, "007F8009", 0),
    "A5-13-01:eltako": (Rorg.BS4, "80808C1A", 0),
}


def _catalog_refs() -> set[str]:
    refs = set()
    for model in CATALOG.values():
        if model.receive:
            refs.add(str(model.receive))
        refs.update(str(r) for r in model.receive_extra)
    return refs


def test_every_catalog_profile_has_a_sample() -> None:
    assert _catalog_refs() <= set(SAMPLES), _catalog_refs() - set(SAMPLES)


@pytest.mark.parametrize("ref", sorted(SAMPLES))
def test_sample_decodes(ref: str) -> None:
    rorg, data, status = SAMPLES[ref]
    telegram = RadioTelegram(rorg, bytes.fromhex(data), ID, status)
    assert decode_telegram(EEPRef.parse(ref), telegram)


def test_device_docs_up_to_date() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/gen_device_docs.py", "--check"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout


COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/enocean_eltako"


@pytest.mark.parametrize("name", ["strings.json", "translations/en.json", "translations/de.json"])
def test_flow_texts_cover_the_catalog(name: str) -> None:
    """Every kind, category menu entry and EEP choice has a label in every language."""
    data = json.loads((COMPONENT / name).read_text(encoding="utf-8"))
    assert set(data["selector"]["device_model"]["options"]) == set(CATALOG)
    assert set(data["selector"]["eep"]["options"]) == set(EEP_OPTIONS)
    steps = data["config_subentries"]["device"]["step"]
    for group in GROUPS:
        expected = {f"{group}_{c}" for c in categories_of(group)}
        assert set(steps[group]["menu_options"]) == expected | {"user"}  # + back
        assert set(steps[group]["menu_option_descriptions"]) == expected
    kinds = {f"model_{m}" for m in CATALOG}
    assert set(steps["kind"]["menu_options"]) == kinds | set(GROUPS)  # + back


def test_catalog_entries_have_a_place_in_the_menus() -> None:
    for model in CATALOG.values():
        assert model.group in GROUPS and model.category in CATEGORIES, model.id
        assert model.base is None or model.base in CATALOG, model.id
    assert all(m in CATALOG for m in EEP_TO_MODEL.values())


def test_candidates_from_a_heard_telegram() -> None:
    assert candidates(Rorg.BS1, None) == ["contact", "enocean_contact"]
    # Eltako teach-in: Eltako entries first; other manufacturers: theirs first
    eltako = TeachIn4BS(0x12, 0x01, MANUFACTURER_ELTAKO)
    assert candidates(Rorg.BS4, eltako) == ["meter", "psc"]
    assert candidates(Rorg.BS4, TeachIn4BS(0x12, 0x01, 0x046)) == ["psc", "meter"]
    assert candidates(Rorg.BS4, TeachIn4BS(0x38, 0x08, MANUFACTURER_ELTAKO)) == ["dimmer"]
