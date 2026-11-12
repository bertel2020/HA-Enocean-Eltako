"""Eltako sensor variants of standard profiles.

A5-04-02:eltako (FAFT60, solar-powered outdoor sensor): as official, plus DB3 = supply voltage of
    its energy storage, 0.025 V per step (0 ... 6.375 V; official: DB3 unused). The scale is taken
    from a FAFT60 in use, whose storage reads 2.8 ... 3.5 V, rising by day and falling by night;
    a data byte of 0 means no voltage was sent.

A5-08-01:eltako (FBH65, FBH65S, FABH65S, FBH65TF): as official, but DB1 carries no
    temperature (official 0...51 degC) and the occupancy button bit is always "released";
    both are left out.

A5-10-06:eltako (FUTH, FTR65HS, FTAF55D): DB3 = night setback 0...5 K
    (0x00, 0x06, 0x0C, 0x13, 0x19, 0x1F; official: reserved), DB2 = setpoint 0...40 degC
    (official: raw value without unit), DB1 = temperature 40...0 degC (inverted, as official),
    DB0.0 = slide switch / day-night.

A5-12-01/02/03:eltako (FWZ12, FWZ14, FSDG14, DSZ14DRS, DSZ14WDRS, F3Z14D for electricity, gas and
    water, FSR14M-2x, FSR61VA, FSVA-230V): data telegrams as official. Source: Eltako, "Inhalte der
    Eltako-Funktelegramme" (PDF). Only the meters FWZ12, FWZ14, FSDG14, DSZ14DRS and DSZ14WDRS also
    send the serial number printed on them, S-AABBCC, every 10 minutes in two consecutive telegrams
    with DB0 = 0x8F (TI 8, DT 1, DIV 3), which a standard decoder would read as a current value:
    DB3 = AA, DB2 = 0, DB1 = 0x00 and DB3 = CC, DB2 = BB, DB1 = 0x01. The F3Z14D and the actuators
    do not send it. The PDF does not say how a digit pair is coded; it is read as BCD (0x12 = 12),
    and as a binary number (0x0C = 12) when a nibble is above 9. Not yet checked against a capture.
    The telegrams are returned as serial parts, not as readings.

A5-13-01:eltako (FWS61, FWG14MS): weather station sending two telegrams under one ID, told
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


def decode_solar_temp_humidity(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08:
        return None
    values = decode(PROFILES["A5-04-02"], data)
    values.pop("LRNB", None)
    values["supply_voltage"] = round(data[0] * 0.025, 3) if data[0] else None
    return values


def decode_room_controller(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08:
        return None
    return {
        "night_setback": round(min(data[0], 0x1F) * 5 / 31),
        "setpoint": round(data[1] * 40 / 255, 1),
        "temperature": round((255 - data[2]) * 40 / 255, 1),
        "slide_switch": data[3] & 0x01,
    }


SERIAL_TELEGRAM = 0x8F


def format_meter_serial(digit_pairs: bytes) -> str | None:
    """S-AABBCC from the three digit-pair bytes AA BB CC (see the module docstring)."""
    if len(digit_pairs) != 3:
        return None
    if all(b >> 4 <= 9 and b & 0x0F <= 9 for b in digit_pairs):
        return "S-" + digit_pairs.hex().upper()
    if all(b <= 99 for b in digit_pairs):
        return "S-" + "".join(f"{b:02d}" for b in digit_pairs)
    return None


def decode_meter(data: bytes, eep: str = "A5-12-01") -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08:
        return None
    if data[3] == SERIAL_TELEGRAM:
        if data[2] not in (0, 1):
            return None
        # part 0: AA in DB3; part 1: BB in DB2, CC in DB3
        return {
            "serial_part": data[2],
            "serial_bytes": bytes([data[0]]) if data[2] == 0 else bytes([data[1], data[0]]),
        }
    values = decode(PROFILES[eep], data)
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
