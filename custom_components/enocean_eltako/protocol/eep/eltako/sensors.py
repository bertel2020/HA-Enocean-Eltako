"""Eltako sensor variants of standard profiles.

A5-08-01:eltako (FBH65, FBH65S, FABH65S, FBH65TF): as official, but DB1 carries no
    temperature (official 0...51 degC) and the occupancy button bit is always "released";
    both are left out.

A5-10-06:eltako (FUTH, FTR65HS, FTAF55D): DB3 = night setback 0...5 K
    (0x00, 0x06, 0x0C, 0x13, 0x19, 0x1F; official: reserved), DB2 = setpoint 0...40 degC
    (official: raw value without unit), DB1 = temperature 40...0 degC (inverted, as official),
    DB0.0 = slide switch / day-night.

A5-12-01:eltako (FWZ12, FSDG14, DSZ14DRS, F3Z14D): data telegrams as official; the meters
    also send their serial number in two telegrams with DB0 = 0x8F, which a standard decoder
    would read as a power value. Those are dropped.

A5-13-01:eltako (FWS61, FWG14): weather station sending two telegrams under one ID, told
    apart by the identifier in DB0.7...4 (1 = official A5-13-01 layout, 2 = A5-13-02).
"""

from __future__ import annotations

from typing import Any

from ..model import decode
from ..std.profiles import PROFILES


def decode_fbh(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08:
        return None
    values = decode(PROFILES["A5-08-01"], data)
    return {k: v for k, v in values.items() if k not in ("TMP", "OCC", "LRNB")}


def decode_room_controller(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08:
        return None
    return {
        "night_setback": round(min(data[0], 0x1F) * 5 / 31),
        "setpoint": round(data[1] * 40 / 255, 1),
        "temperature": round((255 - data[2]) * 40 / 255, 1),
        "slide_switch": data[3] & 0x01,
    }


def decode_meter(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08 or data[3] == 0x8F:
        return None
    values = decode(PROFILES["A5-12-01"], data)
    values.pop("LRNB", None)
    return values


def decode_weather(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08:
        return None
    identifier = data[3] >> 4
    eep = {1: "A5-13-01", 2: "A5-13-02"}.get(identifier)
    if eep is None:
        return None
    values = decode(PROFILES[eep], data)
    values.pop("LRNB", None)
    values.pop("ID", None)
    return values
