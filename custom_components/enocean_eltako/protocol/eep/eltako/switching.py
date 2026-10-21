"""Eltako switching and dimming actuators.

M5-38-08 (status of switching actuators, e.g. FSR61, FSR14 via FAM14):
    RPS like a PTM200 rocker without release telegram: data 0x70 = on, 0x50 = off
    (bit 5 carries the state). Two-channel actuators with one ID (e.g. FSR71NP-2x) report
    channel 2 like the left rocker: 0x30 = on, 0x10 = off. Not an official profile.

A5-38-08:eltako (central command to switching and dimming actuators, and dimmer status):
    Command 1 (switching) as official. Command 2 (dimming) deviates:
    DB2 = dimming value 0...100 % absolute (official: EDIM with EDIMR range bit),
    DB1 = dimming speed 0x01 fast ... 0xFF slow, 0x00 = speed set on the actuator
    (official: ramping time), DB0.2 = lock the dimming value (official: EDIMR),
    DB0.0 = on/off, DB0.3 = LRN (1 = data). Dimmers report their state with the same
    command 2 layout. Teach-in: 4BS E0 40 0D 80.
"""

from __future__ import annotations

from typing import Any

from ..teach_in import encode_teach_in_4bs

TEACH_IN = encode_teach_in_4bs("A5-38-08")


STATUS_CODES = {0x70: (1, True), 0x50: (1, False), 0x30: (2, True), 0x10: (2, False)}


def decode_switch_status(data: bytes) -> dict[str, Any] | None:
    """M5-38-08: {"on": bool, "channel": 1 | 2} (0x70/0x50 channel 1, 0x30/0x10 channel 2)."""
    if len(data) != 1 or data[0] not in STATUS_CODES:
        return None
    channel, on = STATUS_CODES[data[0]]
    return {"on": on, "channel": channel}


def encode_switch_status(on: bool) -> bytes:
    return bytes([0x70 if on else 0x50])


def encode_switch(on: bool, *, lock: bool = False) -> bytes:
    """Command 1: switch on/off (no time function)."""
    return bytes([0x01, 0x00, 0x00, 0x08 | (0x04 if lock else 0) | (0x01 if on else 0)])


def encode_dim(brightness: int, *, on: bool = True, speed: int = 0, lock: bool = False) -> bytes:
    """Command 2: brightness 0...100 %, speed 0 = actuator setting, 1 fast ... 255 slow."""
    brightness = max(0, min(100, int(brightness)))
    return bytes(
        [0x02, brightness, max(0, min(255, speed)), 0x08 | (0x04 if lock else 0) | int(on)]
    )


def decode_dim_status(data: bytes) -> dict[str, Any] | None:
    """Dimmer status (command 2) or switching status (command 1) of an A5-38-08 actuator."""
    if len(data) != 4 or not data[3] & 0x08:
        return None
    if data[0] == 0x02:
        return {"on": bool(data[3] & 0x01), "brightness": min(data[1], 100)}
    if data[0] == 0x01:
        return {"on": bool(data[3] & 0x01)}
    return None
