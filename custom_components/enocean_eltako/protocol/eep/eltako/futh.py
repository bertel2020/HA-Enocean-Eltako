"""FUTH room controller (FUTH55ED, FUTH65D): one device, four IDs.

The controller sends from consecutive IDs, each a fixed offset above a base ID (the lowest of
them, ending in 00 for the room 1 controller):

    +0x01  room controller   A5-10-06:eltako  setpoint, temperature, night setback, slide switch
    +0x10  pump              F6-02-01:eltako  0x70 = on, 0x50 = off
    +0x11  operating mode    F6-02-01:eltako  0x70 normal, 0x50 night setback (-4 K),
                                              0x30 reduced (-2 K), 0x10 off
    +0x12  hygrostat         A5-10-12:std     humidity and temperature of the built-in sensor

F6-02-01:eltako: the pump and mode telegrams are RPS rocker codes as official, but they are
read from the data byte alone (no status byte check) and the release telegram 0x00 is no state.

The offsets come from the table of the old eltako integration (docs/heating-and-cooling), taken
from the FHEM forum; a capture of a FUTH55ED confirms them: 4BS 00 8C 70 0F at +0x01 reads as
22.0 degC setpoint and 22.4 degC, 4BS 7F 64 8B 08 at +0x12 as 40 % and 22.2 degC.
"""

from __future__ import annotations

from typing import Any

CONTROLLER = "controller"
PUMP = "pump"
MODE = "mode"
HYGROSTAT = "hygrostat"

MODES = {0x70: "normal", 0x50: "night_setback", 0x30: "setback", 0x10: "off"}
PUMP_CODES = {0x70: True, 0x50: False}


def decode_code(data: bytes) -> dict[str, Any] | None:
    """The rocker code of a pump or mode telegram; the release telegram is no state."""
    if len(data) != 1 or data[0] not in MODES:
        return None
    return {"code": data[0]}


def interpret(role: str, values: dict[str, Any]) -> dict[str, Any] | None:
    """The values a telegram means under the ID of this role, None when it means nothing."""
    if role == PUMP:
        return {"pump": PUMP_CODES[values["code"]]} if values.get("code") in PUMP_CODES else None
    if role == MODE:
        return {"heating_mode": MODES[values["code"]]} if values.get("code") in MODES else None
    if role == HYGROSTAT:
        found = {
            key: round(values[field], 1)
            for key, field in (("humidity", "HUM"), ("hygrostat_temperature", "TMP"))
            if field in values
        }
        return found or None
    return values
