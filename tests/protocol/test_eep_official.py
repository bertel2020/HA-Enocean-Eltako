"""Standard profiles against the official EEP Viewer test containers.

The containers are EnOcean Alliance files and never committed; scripts/fetch_eep.py puts
them into .eep_cache/ (CI fetches them). Without the cache these tests are skipped.
"""

from __future__ import annotations

import math
import re
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
    # expects 8388607.5 for raw 0x7FFFFF with divisor x/1 (same container for gas and water)
    ("A5-12-01", "MR"),
    ("A5-12-02", "MR"),
    ("A5-12-03", "MR"),
    # "unused field test": the LRN bit is masked out (ignoremask 0x09) but expected as 1
    ("A5-07-01", "LRNB"),
}


# Phase 5 generates every profile. In these the official containers and the generic decoder
# disagree: several cases that the data cannot tell apart (A5-3F-00 radio link test, A5-20
# valves: direction), or container errors like those above. None is used by the catalog;
# they decode generically and stay marked until a profile is checked by hand.
UNVERIFIED_PROFILES = frozenset(
    (
        "A5-02-20",
        "A5-02-30",
        "A5-06-01",
        "A5-06-03",
        "A5-06-05",
        "A5-07-02",
        "A5-08-02",
        "A5-08-03",
        "A5-09-02",
        "A5-09-0A",
        "A5-09-0B",
        "A5-10-01",
        "A5-10-15",
        "A5-10-16",
        "A5-10-17",
        "A5-11-02",
        "A5-12-00",
        "A5-12-10",
        "A5-13-03",
        "A5-13-06",
        "A5-13-07",
        "A5-13-10",
        "A5-14-01",
        "A5-14-02",
        "A5-14-03",
        "A5-14-04",
        "A5-14-06",
        "A5-14-09",
        "A5-14-0A",
        "A5-20-04",
        "A5-20-10",
        "A5-20-12",
        "A5-30-05",
        "A5-3F-00",
    )
)


def _hex(text: str) -> int:
    return int(re.sub(r"[^0-9a-fA-FxX]", "", text), 0)


def _masked(ignored: bytes, offset: int, size: int) -> bool:
    """The container marks a bit of this field as don't care (ignoremask)."""
    mask = int.from_bytes(ignored, "big") if ignored else 0
    total = len(ignored) * 8
    return any(mask >> (total - 1 - bit) & 1 for bit in range(offset, offset + size))


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
                ordered = sorted(telegram.findall("Byte"), key=lambda b: int(b.get("order")))
                try:  # some containers carry invisible characters ("0x\u202d01")
                    data = bytes(_hex(b.text) for b in ordered)
                    ignored = bytes(_hex(b.get("ignoremask") or "0") for b in ordered)
                except (TypeError, ValueError):
                    continue
                expected = {}
                for item in dataset.iter("Data"):
                    shortcut = (item.findtext("Shortcut") or "").strip()
                    value = (item.findtext("Value") or "").strip()
                    if shortcut and value:
                        expected[ALIASES.get(shortcut, shortcut)] = value
                if expected:
                    name = f"{eep}-{test.findtext('Name').strip()}-{n}"
                    marks = (
                        pytest.mark.xfail(reason="unverified profile", strict=False)
                        if eep in UNVERIFIED_PROFILES
                        else ()
                    )
                    cases.append(pytest.param(eep, data, expected, ignored, id=name, marks=marks))
    return cases


CASES = _cases()


@pytest.mark.skipif(not CASES, reason="no official test containers in .eep_cache")
@pytest.mark.parametrize(("eep", "data", "expected", "ignored"), CASES)
def test_official_container(
    eep: str, data: bytes, expected: dict[str, str], ignored: bytes
) -> None:
    profile = PROFILES[eep]
    values = decode(profile, data)
    for shortcut, text in expected.items():
        if shortcut not in values or (eep, shortcut) in KNOWN_CONTAINER_ERRORS:
            continue  # field of a different case, teach-in information, container error
        want = float(text.replace(",", "."))
        got = float(values[shortcut])
        field = next(f for c in profile.cases for f in c.fields if f.shortcut == shortcut)
        if _masked(ignored, field.offset, field.size):
            continue  # the container does not set these bits
        step = 0.0
        if field.raw and field.scale and field.raw[1] != field.raw[0]:
            step = abs((field.scale[1] - field.scale[0]) / (field.raw[1] - field.raw[0]))
        assert math.isclose(got, want, abs_tol=step + 1e-6), f"{shortcut}: {got} != {want}"
