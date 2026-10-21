"""Eltako variants and the codec registry (own fixtures from the Eltako telegram docs)."""

import pytest

from custom_components.enocean_eltako.protocol.eep import EEPRef
from custom_components.enocean_eltako.protocol.eep.codecs import decode_telegram
from custom_components.enocean_eltako.protocol.eep.eltako import shutter, switching
from custom_components.enocean_eltako.protocol.eep.teach_in import (
    decode_teach_in_4bs,
    encode_teach_in_4bs,
)
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

ID = 0x0510A2B3


def tg(rorg: int, data: str, status: int = 0) -> RadioTelegram:
    return RadioTelegram(rorg, bytes.fromhex(data), ID, status)


def test_teach_in_telegrams() -> None:
    assert encode_teach_in_4bs("A5-38-08").hex().upper() == "E0400D80"
    assert encode_teach_in_4bs("A5-3F-7F").hex().upper() == "FFF80D80"
    teach = decode_teach_in_4bs(bytes.fromhex("20080D85"))
    assert teach.eep == "A5-08-01" and teach.manufacturer == 0x00D
    assert decode_teach_in_4bs(bytes.fromhex("0000FF08")) is None  # data telegram


@pytest.mark.parametrize(
    ("data", "on", "channel"),
    [("70", True, 1), ("50", False, 1), ("30", True, 2), ("10", False, 2)],
)
def test_m5_38_08(data: str, on: bool, channel: int) -> None:
    values = decode_telegram(EEPRef("M5-38-08", "eltako"), tg(Rorg.RPS, data, 0x30))
    assert values == {"on": on, "channel": channel}


def test_switch_and_dim_commands() -> None:
    assert switching.encode_switch(True).hex() == "01000009"
    assert switching.encode_switch(False, lock=True).hex() == "0100000c"
    assert switching.encode_dim(55, speed=1).hex() == "02370109"
    status = decode_telegram(EEPRef("A5-38-08", "eltako"), tg(Rorg.BS4, "02320009"))
    assert status == {"on": True, "brightness": 50}


def test_shutter_status_and_command() -> None:
    ref = EEPRef("G5-3F-7F", "eltako")
    assert decode_telegram(ref, tg(Rorg.RPS, "70", 0x30)) == {"state": "open"}
    assert decode_telegram(ref, tg(Rorg.RPS, "02", 0x30)) == {"state": "closing"}
    assert decode_telegram(ref, tg(Rorg.BS4, "00960 20A".replace(" ", ""))) == {
        "driven_time": 15.0,
        "direction": "down",
    }
    assert shutter.encode_command(shutter.UP, 25).hex() == "00190108"
    # whole seconds unless the 100 ms form is chosen (not every firmware knows it)
    assert shutter.encode_command(shutter.DOWN, 2.5).hex() == "00030208"
    assert shutter.encode_command(shutter.DOWN, 0.2).hex() == "00010208"  # at least 1 s
    assert shutter.encode_command(shutter.UP, 300).hex() == "00ff0108"  # at most 255 s
    assert shutter.encode_command(shutter.DOWN, 2.5, tenths=True).hex() == "0019020a"
    assert shutter.encode_command(shutter.UP, 25, tenths=True).hex() == "00190108"
    assert shutter.encode_command(shutter.STOP).hex() == "00000008"


def test_eltako_fbh_drops_temperature_and_occupancy() -> None:
    values = decode_telegram(EEPRef("A5-08-01", "eltako"), tg(Rorg.BS4, "00800009"))
    assert set(values) == {"SVC", "ILL", "PIRS"}
    assert values["PIRS"] == 0
    std = decode_telegram(EEPRef("A5-08-01", "std"), tg(Rorg.BS4, "00800009"))
    assert "TMP" in std


def test_room_controller() -> None:
    values = decode_telegram(EEPRef("A5-10-06", "eltako"), tg(Rorg.BS4, "137F8009"))
    assert values["night_setback"] == 3
    assert values["setpoint"] == pytest.approx(19.9, abs=0.1)
    assert values["temperature"] == pytest.approx(19.9, abs=0.2)


def test_meter_drops_serial_number_telegrams() -> None:
    ref = EEPRef("A5-12-01", "eltako")
    assert decode_telegram(ref, tg(Rorg.BS4, "1234568F")) is None
    assert decode_telegram(ref, tg(Rorg.BS4, "00100009"))["MR"] == pytest.approx(409.6)


def test_weather_station_two_telegrams() -> None:
    ref = EEPRef("A5-13-01", "eltako")
    first = decode_telegram(ref, tg(Rorg.BS4, "80808C1A"))
    assert first["RAN"] == 1 and "TMP" in first and "WND" in first
    second = decode_telegram(ref, tg(Rorg.BS4, "10203028"))
    assert set(second) >= {"SNW", "SNS", "SNE"}


def test_std_skips_teach_in_and_contact() -> None:
    assert decode_telegram(EEPRef("A5-04-02", "std"), tg(Rorg.BS4, "10100080")) is None
    contact = EEPRef("D5-00-01", "std")
    assert decode_telegram(contact, tg(Rorg.BS1, "09"))["CO"] == 1
    assert decode_telegram(contact, tg(Rorg.BS1, "08"))["CO"] == 0
    assert decode_telegram(contact, tg(Rorg.BS4, "00000009")) is None  # wrong RORG
