"""FUTH room controller: the telegrams of its IDs (captured from a FUTH55ED) and their meaning."""

import pytest

from custom_components.enocean_eltako.protocol.eep import EEPRef
from custom_components.enocean_eltako.protocol.eep.codecs import decode_telegram
from custom_components.enocean_eltako.protocol.eep.eltako import futh
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

PUMP_MODE = EEPRef("F6-02-01", "eltako")


def tg(rorg: int, data: str, status: int = 0) -> RadioTelegram:
    return RadioTelegram(rorg, bytes.fromhex(data), 0xFF801C01, status)


def test_controller_telegram_of_a_capture() -> None:
    values = decode_telegram(EEPRef("A5-10-06", "eltako"), tg(Rorg.BS4, "008C700F"))
    assert values == {"night_setback": 0, "setpoint": 22.0, "temperature": 22.4, "slide_switch": 1}


def test_hygrostat_telegram_of_a_capture() -> None:
    values = decode_telegram(EEPRef("A5-10-12", "std"), tg(Rorg.BS4, "7F648B08"))
    assert futh.interpret(futh.HYGROSTAT, values) == {
        "humidity": 40.0,
        "hygrostat_temperature": 22.2,
    }


@pytest.mark.parametrize("status", [0x00, 0x20, 0x30])  # the status byte does not matter
@pytest.mark.parametrize(
    ("code", "pump", "mode"),
    [
        ("70", True, "normal"),
        ("50", False, "night_setback"),
        ("30", None, "setback"),
        ("10", None, "off"),
    ],
)
def test_pump_and_mode_codes(code: str, pump: bool | None, mode: str, status: int) -> None:
    values = decode_telegram(PUMP_MODE, tg(Rorg.RPS, code, status))
    assert futh.interpret(futh.MODE, values) == {"heating_mode": mode}
    expected = None if pump is None else {"pump": pump}
    assert futh.interpret(futh.PUMP, values) == expected


def test_release_telegram_and_other_lengths_are_no_state() -> None:
    assert decode_telegram(PUMP_MODE, tg(Rorg.RPS, "00")) is None
    assert decode_telegram(PUMP_MODE, tg(Rorg.RPS, "7070")) is None
    assert decode_telegram(PUMP_MODE, tg(Rorg.BS4, "00000070")) is None


def test_other_roles_pass_values_through() -> None:
    assert futh.interpret(futh.CONTROLLER, {"setpoint": 21.0}) == {"setpoint": 21.0}
    assert futh.interpret(futh.HYGROSTAT, {"LRNB": 1}) is None
