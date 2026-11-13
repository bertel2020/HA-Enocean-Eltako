"""Decoders by EEP reference: standard profiles from the generated table, Eltako variants
from eep/eltako/. The two never share a code path."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..telegram import RadioTelegram, Rorg
from . import EEPRef
from .eltako import commands, futh, heating, sensors, shutter, switching
from .model import decode
from .std.profiles import PROFILES

Decoder = Callable[[RadioTelegram], dict[str, Any] | None]


def _std(eep: str) -> Decoder:
    profile = PROFILES[eep]
    lrn_field = "LRNB" if profile.rorg == Rorg.BS4 else "LRN"

    def decode_std(telegram: RadioTelegram) -> dict[str, Any] | None:
        if telegram.rorg != profile.rorg:
            return None
        values = decode(profile, telegram.data, telegram.status)
        if values.get(lrn_field, 1) == 0:
            return None  # teach-in telegram
        return values or None

    return decode_std


def _eltako(rorg: int, fn: Callable[[bytes], dict[str, Any] | None]) -> Decoder:
    def decode_eltako(telegram: RadioTelegram) -> dict[str, Any] | None:
        return fn(telegram.data) if telegram.rorg == rorg else None

    return decode_eltako


def _shutter_status(telegram: RadioTelegram) -> dict[str, Any] | None:
    if telegram.rorg not in (Rorg.RPS, Rorg.BS4):
        return None
    return shutter.decode_status(telegram.data)


DECODERS: dict[EEPRef, Decoder] = {
    **{EEPRef(eep, "std"): _std(eep) for eep in PROFILES},
    EEPRef("M5-38-08", "eltako"): _eltako(Rorg.RPS, switching.decode_switch_status),
    EEPRef("A5-38-08", "eltako"): _eltako(Rorg.BS4, switching.decode_dim_status),
    EEPRef("G5-3F-7F", "eltako"): _shutter_status,
    EEPRef("A5-04-02", "eltako"): _eltako(Rorg.BS4, sensors.decode_solar_temp_humidity),
    EEPRef("A5-06-01", "eltako"): _eltako(Rorg.BS4, sensors.decode_brightness),
    EEPRef("A5-06-02", "eltako"): _eltako(Rorg.BS4, sensors.decode_brightness_voltage),
    EEPRef("A5-08-01", "eltako"): _eltako(Rorg.BS4, sensors.decode_fbh),
    EEPRef("M5-10-06", "eltako"): lambda t: (
        heating.decode_status(t.data) if t.rorg in (Rorg.RPS, Rorg.BS4) else None
    ),
    EEPRef("A5-10-06", "eltako"): _eltako(Rorg.BS4, sensors.decode_room_controller),
    EEPRef("F6-02-01", "eltako"): _eltako(Rorg.RPS, futh.decode_code),
    EEPRef("A5-12-01", "eltako"): _eltako(Rorg.BS4, sensors.decode_meter),
    EEPRef("A5-12-02", "eltako"): _eltako(Rorg.BS4, lambda d: sensors.decode_meter(d, "A5-12-02")),
    EEPRef("A5-12-03", "eltako"): _eltako(Rorg.BS4, lambda d: sensors.decode_meter(d, "A5-12-03")),
    EEPRef("A5-13-01", "eltako"): _eltako(Rorg.BS4, sensors.decode_weather),
}


def decode_telegram(ref: EEPRef, telegram: RadioTelegram) -> dict[str, Any] | None:
    """Decoded values, or None for teach-in, foreign or undecodable telegrams."""
    decoder = DECODERS.get(ref)
    values = decoder(telegram) if decoder else None
    if values is not None and ref == EEPRef("F6-02-01", "std"):
        # NU=0 is a U-message ("several buttons"): R1 is no rocker code then
        values["NU"] = 1 if telegram.status & 0x10 else 0
    return values


ROCKER_BUTTONS = {0: "AI", 1: "AO", 2: "BI", 3: "BO"}


def _std_switch_command(telegram: RadioTelegram) -> dict[str, Any] | None:
    """A5-38-08 command 2 as the standard controller sends it: on/off with a dim value."""
    values = _std("A5-38-08")(telegram)
    if not values or values.get("COM") != 2 or values.get("EDIM R"):
        return None
    return {"on": bool(values["SW"]), "dim": round(values["EDIM"])}


def _std_rocker_command(telegram: RadioTelegram) -> dict[str, Any] | None:
    """F6-02-01 as a sender presses and releases a rocker."""
    values = _std("F6-02-01")(telegram)
    if values is None:
        return None
    if telegram.status & 0x10:  # NU: the data byte is a rocker code
        if values["EB"] and values["R1"] in ROCKER_BUTTONS:
            return {"button": ROCKER_BUTTONS[values["R1"]], "pressed": True}
        return None
    return {"pressed": False} if telegram.data == b"\x00" else None


# what a device sends to an actuator, by the EEP of its sender profile (not what it receives)
COMMAND_DECODERS: dict[EEPRef, Decoder] = {
    EEPRef("A5-38-08", "eltako"): _eltako(Rorg.BS4, commands.decode_central),
    EEPRef("H5-3F-7F", "eltako"): _eltako(Rorg.BS4, commands.decode_shutter),
    EEPRef("A5-10-06", "eltako"): _eltako(Rorg.BS4, commands.decode_heating_controller),
    EEPRef("A5-38-08", "std"): _std_switch_command,
    EEPRef("F6-02-01", "std"): _std_rocker_command,
}


def decode_command(ref: EEPRef, telegram: RadioTelegram) -> dict[str, Any] | None:
    """Values of a telegram we sent from the sender profile with this EEP, or None."""
    decoder = COMMAND_DECODERS.get(ref)
    return decoder(telegram) if decoder else None
