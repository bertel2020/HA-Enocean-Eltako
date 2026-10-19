"""Standard profiles against the official EEP Viewer test containers.

The containers are EnOcean Alliance files and never committed; scripts/fetch_eep.py puts
them into .eep_cache/ (CI fetches them). Without the cache these tests are skipped.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from custom_components.enocean_eltako.protocol.eep.model import decode
from custom_components.enocean_eltako.protocol.eep.std.profiles import PROFILES

CACHE = Path(__file__).resolve().parents[2] / ".eep_cache"
ALIASES = {"LRN": "LRNB"}

# Containers whose expected values contradict their own profile definition; checked by hand.
KNOWN_CONTAINER_ERRORS = {
    # expects tenths of a volt (51 = 5.1 V) although the profile scales to 0...5.1 V
    ("A5-08-01", "SVC"),
    # expects the raw value 1...65535 although the profile scales TIM to 0.1...6553.5 s
    ("A5-38-08", "TIM"),
    # expects 8388607.5 for raw 0x7FFFFF with divisor x/1
    ("A5-12-01", "MR"),
}


def _cases() -> list:
    cases = []
    for eep in sorted(PROFILES):
        path = CACHE / f"{eep}_test.xml"
        if not path.exists():
            continue
        root = ET.parse(path).getroot()
        for test in root.iter("Test"):
            for n, dataset in enumerate(test.iter("DataSet")):
                telegram = dataset.find("Telegram")
                if telegram is None:
                    continue
                data = bytes(
                    int(b.text, 0)
                    for b in sorted(telegram.findall("Byte"), key=lambda b: int(b.get("order")))
                )
                expected = {}
                for item in dataset.iter("Data"):
                    shortcut = (item.findtext("Shortcut") or "").strip()
                    value = (item.findtext("Value") or "").strip()
                    if shortcut and value:
                        expected[ALIASES.get(shortcut, shortcut)] = value
                if expected:
                    name = f"{eep}-{test.findtext('Name').strip()}-{n}"
                    cases.append(pytest.param(eep, data, expected, id=name))
    return cases


CASES = _cases()


@pytest.mark.skipif(not CASES, reason="no official test containers in .eep_cache")
@pytest.mark.parametrize(("eep", "data", "expected"), CASES)
def test_official_container(eep: str, data: bytes, expected: dict[str, str]) -> None:
    profile = PROFILES[eep]
    values = decode(profile, data)
    for shortcut, text in expected.items():
        if shortcut not in values or (eep, shortcut) in KNOWN_CONTAINER_ERRORS:
            continue  # field of a different case, teach-in information, container error
        want = float(text.replace(",", "."))
        got = float(values[shortcut])
        field = next(f for c in profile.cases for f in c.fields if f.shortcut == shortcut)
        step = 0.0
        if field.raw and field.scale and field.raw[1] != field.raw[0]:
            step = abs((field.scale[1] - field.scale[0]) / (field.raw[1] - field.raw[0]))
        assert math.isclose(got, want, abs_tol=step + 1e-6), f"{shortcut}: {got} != {want}"
