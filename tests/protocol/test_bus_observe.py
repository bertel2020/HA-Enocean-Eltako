"""Reading the FAM14 bus by listening: addresses from the confirmation telegrams heard.

Fixtures from Eltako's description of the confirmation telegrams of the series 14 ("Inhalte der
Eltako-Funktelegramme"): the radio ID is the FAM14's base ID plus the device address, an FSR14
channel sends 0x70 (on) or 0x50 (off) as a rocker telegram, an FSB14 0x01/0x02 when it starts.
"""

from custom_components.enocean_eltako.protocol.bus.observe import (
    Heard,
    answers,
    base_candidates,
    base_of,
    bus_address,
    feedback_id,
    telegram_kind,
)

FAM14 = 0xFF9A1C80  # a base ID of a FAM14 (multiple of 0x80)
OWN = 0xFFB74480  # the base ID of the FAM-USB of Home Assistant


def radio(sender: int, data: int = 0x70, t: float = 1.0, rorg: int = 0xF6) -> Heard:
    return Heard(sender, "gw1", False, rorg, bytes([data]), t)


def test_the_kind_of_a_confirmation_telegram() -> None:
    assert telegram_kind(0xF6, b"\x70") == "on" and telegram_kind(0xF6, b"\x50") == "off"
    assert telegram_kind(0xF6, b"\x01") == "up" and telegram_kind(0xF6, b"\x02") == "down"
    assert telegram_kind(0xA5, b"\x02\x40\x00\x09") == "4bs"
    assert telegram_kind(0xD2, b"\x00") == "other"


def test_a_base_id_and_offset() -> None:
    assert base_of(FAM14 + 1) == (FAM14, 1)
    assert base_of(FAM14 + 126) == (FAM14, 126)
    assert base_of(FAM14) is None and base_of(FAM14 + 127) is None  # no device address
    assert base_of(0x05103A2B) is None  # a chip ID, not in the base ID range


def test_addresses_heard_by_radio_with_the_base_id() -> None:
    heard = [
        radio(FAM14 + 1, 0x70, 1.0),
        radio(FAM14 + 1, 0x50, 2.0),  # the newer one wins
        radio(FAM14 + 9, 0x01, 1.5),
        radio(OWN + 3),  # Home Assistant's own sender
        radio(0x05103A2B),
    ]
    found = answers(heard, FAM14)
    assert sorted(found) == [1, 9]
    assert found[1].kind == "off" and found[9].kind == "up"
    assert answers(heard, None) == {}  # by radio the base ID is needed


def test_on_the_wire_the_address_is_the_id_assumed() -> None:
    wired = Heard(0x00000005, "gw2", True, 0xF6, b"\x70", 1.0)
    assert sorted(answers([wired], None)) == [5]


def test_base_id_candidates_leave_out_the_gateways_own() -> None:
    heard = [radio(FAM14 + a) for a in (1, 2, 3)] + [
        radio(OWN + 1),
        radio(0xFFC0AA81),
        radio(0xFF00AA81),
    ]
    assert base_candidates(heard, [OWN]) == [
        (FAM14, 3),
        (0xFFC0AA80, 1),
    ]  # FF-00-AA-81 lies below the base ID range


def test_the_feedback_id_is_base_plus_address() -> None:
    assert feedback_id(FAM14, 1) == "FF-9A-1C-81"
    assert feedback_id(FAM14, 126) == "FF-9A-1C-FE"


def test_the_bus_range_is_base_plus_1_to_126() -> None:
    assert bus_address(FAM14 + 1, FAM14) == 1
    assert bus_address(FAM14 + 126, FAM14) == 126
    assert bus_address(FAM14, FAM14) is None  # the base ID itself
    assert bus_address(FAM14 + 127, FAM14) is None  # the last ID of the block is no address
    assert bus_address(FAM14 - 1, FAM14) is None  # the block below
    assert bus_address(FAM14 + 128, FAM14) is None  # the block above
