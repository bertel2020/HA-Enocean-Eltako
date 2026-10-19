"""Eltako heating actuators (FHK14, FAE14, F4HK14, FHK61) with Home Assistant as controller.

M5-10-06 (our name, after Eltako's M5-38-08; not an official profile): RPS status of the
    actuator: 0x70 normal, 0x50 night setback (-4 K), 0x30 setback (-2 K), 0x10 off.

A5-10-06:eltako sent by the controller (see sensors.py for the layout): DB3 = night setback
    0...5 K (0x00 ... 0x1F), DB2 = setpoint 0...40 degC, DB1 = temperature 40...0 degC,
    DB0 = 0x08: data telegram, only the values of the taught-in controller count (priority).
    Actuators answer with DB0 = 0x0F and their setpoint and temperature.
    Without a temperature telegram for more than 1 h the actuators go into fault mode
    (fixed heating cycle), so the controller sends at least every 10 min.
    Teach-in: 4BS A5-10-06 with manufacturer Eltako.
"""

from __future__ import annotations

from typing import Any

from ..teach_in import encode_teach_in_4bs

TEACH_IN = encode_teach_in_4bs("A5-10-06")
MODES = {0x70: "normal", 0x50: "night_setback", 0x30: "setback", 0x10: "off"}
PRIORITY_CONTROLLER = 0x08
ACTUATOR_ACK = 0x0F


def decode_status(data: bytes) -> dict[str, Any] | None:
    """RPS mode status, or the actuator's A5-10-06 acknowledgement."""
    if len(data) == 1:
        mode = MODES.get(data[0])
        return {"mode": mode} if mode else None
    if len(data) == 4 and data[3] == ACTUATOR_ACK:
        return {
            "setpoint": round(data[1] * 40 / 255, 1),
            "temperature": round((255 - data[2]) * 40 / 255, 1),
        }
    return None


def encode_controller(setpoint: float, temperature: float, night_setback: int = 0) -> bytes:
    def raw(value: float) -> int:
        return max(0, min(255, round(value * 255 / 40)))

    setback = (0x00, 0x06, 0x0C, 0x13, 0x19, 0x1F)[max(0, min(5, night_setback))]
    return bytes([setback, raw(setpoint), 255 - raw(temperature), PRIORITY_CONTROLLER])
