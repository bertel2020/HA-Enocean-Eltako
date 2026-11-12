"""What Home Assistant sends to Eltako actuators, read back for the telegram log.

The layouts are the ones the encoders in switching.py, shutter.py and heating.py write, so
a telegram is read exactly as it was built. None for anything that is not such a command.

A5-38-08:eltako (central command): 4BS 00 00 00 08 asks the actuator to send its status,
    00 00 00 28 (DB0.5) unlocks the learn mode of the series 62 actuators (FL62, FR62, FD62,
    FJ62; source: Eltako "Inhalte der Eltako-Funktelegramme"), and the same telegram three times
    within 2 s deletes the sender ID of the actuator (teach-out),
    otherwise command 1 (switching) or 2 (dimming) as in switching.py, DB0.2 = lock.

H5-3F-7F (shutter command): see shutter.py. DB1 = command, DB2 (or DB3/DB2 with DB0.1) = run time.

A5-10-06:eltako (room controller command to a heating actuator): DB3 = night setback step,
    DB2 = setpoint, DB1 = temperature, inverted; 0x00 = the controller has none, the room
    temperature comes from the thermostat taught into the actuator (see heating.py).
"""

from __future__ import annotations

from typing import Any

from . import shutter, switching

STATUS_REQUEST = bytes.fromhex("00000008")
LEARN_UNLOCK = bytes.fromhex("00000028")
TEACH_OUT_REPEATS = 3  # LEARN_UNLOCK this many times within TEACH_OUT_WINDOW seconds
TEACH_OUT_WINDOW = 2.0
COMMANDS = {shutter.STOP: "stop", shutter.UP: "up", shutter.DOWN: "down"}
NIGHT_SETBACK_STEPS = (0x00, 0x06, 0x0C, 0x13, 0x19, 0x1F)


def decode_central(data: bytes) -> dict[str, Any] | None:
    if data == STATUS_REQUEST:
        return {"command": "status_request"}
    if data == LEARN_UNLOCK:
        return {"command": "learn_unlock"}
    if len(data) != 4 or data[0] not in (0x01, 0x02):
        return None
    values = switching.decode_dim_status(data)
    if values is None:
        return None
    if "brightness" in values:
        values["dim"] = values.pop("brightness")
    if data[3] & 0x04:
        values["lock"] = True
    return values


def decode_shutter(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or not data[3] & 0x08 or data[2] not in COMMANDS:
        return None
    values: dict[str, Any] = {"command": COMMANDS[data[2]]}
    if data[2] != shutter.STOP:
        tenths = bool(data[3] & 0x02)
        run_time = ((data[0] << 8) | data[1]) / 10 if tenths else data[1]
        values["run_time"] = run_time
    if data[3] & 0x04:
        values["lock"] = True
    return values


def decode_heating_controller(data: bytes) -> dict[str, Any] | None:
    if len(data) != 4 or data[3] != 0x08 or data[0] not in NIGHT_SETBACK_STEPS:
        return None
    values: dict[str, Any] = {
        "night_setback": NIGHT_SETBACK_STEPS.index(data[0]),
        "setpoint": round(data[1] * 40 / 255, 1),
    }
    if data[2]:
        values["temperature"] = round((255 - data[2]) * 40 / 255, 1)
    return values
