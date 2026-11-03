"""Commands Home Assistant sends, read back for the telegram log."""

import pytest

from custom_components.enocean_eltako import catalog
from custom_components.enocean_eltako.protocol.eep import EEPRef
from custom_components.enocean_eltako.protocol.eep.codecs import decode_command
from custom_components.enocean_eltako.protocol.eep.eltako import heating, shutter, switching
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg


def tg(rorg: int, data: bytes | str, status: int = 0) -> RadioTelegram:
    data = bytes.fromhex(data) if isinstance(data, str) else data
    return RadioTelegram(rorg, data, 0xFFB744B8, status)


def test_heating_controller_without_a_temperature_of_its_own() -> None:
    # sent to a FUTH's actuator: DB1 = 0 is "none", not 40 degC
    values = decode_command(EEPRef("A5-10-06", "eltako"), tg(Rorg.BS4, "00860008"))
    assert values == {"night_setback": 0, "setpoint": 21.0}


@pytest.mark.parametrize(
    ("setpoint", "temperature", "setback"), [(21.0, None, 0), (25.0, 20.0, 1), (5.0, 18.0, 5)]
)
def test_heating_controller_reads_what_the_encoder_wrote(
    setpoint: float, temperature: float | None, setback: int
) -> None:
    data = heating.encode_controller(setpoint, temperature, setback)
    values = decode_command(EEPRef("A5-10-06", "eltako"), tg(Rorg.BS4, data))
    assert values is not None
    assert values["night_setback"] == setback
    assert values["setpoint"] == pytest.approx(setpoint, abs=0.2)
    assert values.get("temperature") == (
        None if temperature is None else pytest.approx(temperature, abs=0.2)
    )


def test_central_commands() -> None:
    ref = EEPRef("A5-38-08", "eltako")
    assert decode_command(ref, tg(Rorg.BS4, "00000008")) == {"command": "status_request"}
    assert decode_command(ref, tg(Rorg.BS4, switching.encode_switch(True))) == {"on": True}
    assert decode_command(ref, tg(Rorg.BS4, switching.encode_switch(False, lock=True))) == {
        "on": False,
        "lock": True,
    }
    assert decode_command(ref, tg(Rorg.BS4, switching.encode_dim(50))) == {"on": True, "dim": 50}
    assert decode_command(ref, tg(Rorg.BS4, bytes(4))) is None


def test_standard_controller_command() -> None:
    ref = EEPRef("A5-38-08", "std")
    assert decode_command(ref, tg(Rorg.BS4, catalog._std_switch(True))) == {"on": True, "dim": 100}
    assert decode_command(ref, tg(Rorg.BS4, catalog._std_switch(False))) == {"on": False, "dim": 0}


def test_shutter_commands() -> None:
    ref = EEPRef("H5-3F-7F", "eltako")
    assert decode_command(ref, tg(Rorg.BS4, shutter.encode_command(shutter.UP, 20))) == {
        "command": "up",
        "run_time": 20,
    }
    assert decode_command(ref, tg(Rorg.BS4, shutter.encode_command(shutter.STOP))) == {
        "command": "stop"
    }
    data = shutter.encode_command(shutter.DOWN, 12.5, tenths=True, lock=True)
    assert decode_command(ref, tg(Rorg.BS4, data)) == {
        "command": "down",
        "run_time": 12.5,
        "lock": True,
    }


def test_rocker_press_and_release() -> None:
    ref = EEPRef("F6-02-01", "std")
    assert decode_command(ref, tg(Rorg.RPS, "70", 0x30)) == {"button": "BO", "pressed": True}
    assert decode_command(ref, tg(Rorg.RPS, "10", 0x30)) == {"button": "AI", "pressed": True}
    assert decode_command(ref, tg(Rorg.RPS, "00", 0x20)) == {"pressed": False}


def test_other_profiles_are_not_guessed() -> None:
    assert decode_command(EEPRef("D2-01-00", "std"), tg(Rorg.VLD, "010000")) is None
