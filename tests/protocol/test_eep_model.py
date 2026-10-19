"""Table-driven EEP model (own fixtures, independent of the official containers)."""

import pytest

from custom_components.enocean_eltako.protocol.eep import EEPRef
from custom_components.enocean_eltako.protocol.eep.model import decode, encode, get_bits, unit_of
from custom_components.enocean_eltako.protocol.eep.std.profiles import PROFILES


def test_eepref_roundtrip() -> None:
    ref = EEPRef.parse("a5-08-01:eltako")
    assert ref == EEPRef("A5-08-01", "eltako")
    assert str(ref) == "A5-08-01:eltako"
    with pytest.raises(ValueError):
        EEPRef.parse("A5-08-01")


def test_get_bits_msb_first() -> None:
    data = bytes.fromhex("80000008")
    assert get_bits(data, 0, 1) == 1
    assert get_bits(data, 28, 1) == 1


def test_rocker_case_depends_on_status() -> None:
    profile = PROFILES["F6-02-01"]
    pressed = decode(profile, b"\x70", status=0x30)  # T21=1, NU=1: rocker B0 pressed
    assert pressed["R1"] == 3 and pressed["EB"] == 1
    released = decode(profile, b"\x00", status=0x20)  # T21=1, NU=0
    assert released["EB"] == 0


def test_window_handle() -> None:
    profile = PROFILES["F6-10-00"]
    assert decode(profile, b"\xf0", status=0x20)  # handle down (closed)


def test_meter_unit_follows_data_type() -> None:
    profile = PROFILES["A5-12-01"]
    cumulative = bytes.fromhex("00100009")  # DT=0, DIV=1
    current = bytes.fromhex("0003E80C")  # 1000 W, DT=1, DIV=0
    assert decode(profile, cumulative)["MR"] == pytest.approx(409.6)
    assert unit_of(profile, cumulative, "MR") == "kWh"
    assert decode(profile, current)["MR"] == 1000
    assert unit_of(profile, current, "MR") == "W"


def test_encode_dim_command_standard() -> None:
    profile = PROFILES["A5-38-08"]
    case = next(
        i for i, c in enumerate(profile.cases) if c.conditions and c.conditions[0].value == 2
    )
    data = encode(profile, {"EDIM": 50, "RMP": 0, "LRNB": 1, "SW": 1}, case_index=case)
    assert data == bytes([0x02, 0x80, 0x00, 0x09])
    assert decode(profile, data)["EDIM"] == pytest.approx(50.2, abs=0.3)
