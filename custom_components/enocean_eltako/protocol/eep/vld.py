"""Commands and status of VLD actuators, encoded from the standard profiles.

D2-01 (switches and dimmers): command 1 sets the output of channel I/O to OV (0 off,
1...100 %), command 3 asks for the status, command 4 is the actuator's status response.
D2-05 (blinds): command 1 drives channel CHN to POS (0 = open ... 100 = closed; 127 = keep)
with the slats at ANG, command 2 stops, command 3 asks for the position, command 4 replies.
All D2-01 types share one layout (D2-01-09 points to D2-01-00), so D2-01-00 encodes them.
"""

from __future__ import annotations

from typing import Any

from .model import encode
from .std.profiles import PROFILES

SWITCH = PROFILES["D2-01-00"]
BLIND = PROFILES["D2-05-00"]
KEEP = 127  # D2-05: leave position or slat angle unchanged
UNKNOWN = 127  # D2-01/D2-05 status: value not known


def _case(profile: Any, command: int) -> int:
    return next(
        i
        for i, c in enumerate(profile.cases)
        if any(cond.value == command and cond.size == 4 for cond in c.conditions)
    )


def encode_set_output(channel: int, percent: int) -> bytes:
    return encode(
        SWITCH,
        {"CMD": 1, "DV": 0, "I/O": channel, "OV": max(0, min(100, percent))},
        _case(SWITCH, 1),
    )


def encode_switch_query(channel: int) -> bytes:
    return encode(SWITCH, {"CMD": 3, "I/O": channel}, _case(SWITCH, 3))


def switch_status(values: dict[str, Any], channel: int) -> int | None:
    """Output value 0...100 of the channel from a status response, None otherwise."""
    if values.get("CMD") != 4 or values.get("I/O") not in (channel, 0x1E):
        return None
    output = values.get("OV")
    return None if output is None or output > 100 else int(output)


def encode_blind_position(channel: int, closed: int, angle: int = KEEP) -> bytes:
    """Drive to closed percent (0 open ... 100 closed)."""
    values = {"POS": max(0, min(100, closed)), "ANG": angle, "REPO": 0, "LOCK": 0}
    return encode(BLIND, {**values, "CHN": channel, "CMD": 1}, _case(BLIND, 1))


def encode_blind_stop(channel: int) -> bytes:
    return encode(BLIND, {"CHN": channel, "CMD": 2}, _case(BLIND, 2))


def encode_blind_query(channel: int) -> bytes:
    return encode(BLIND, {"CHN": channel, "CMD": 3}, _case(BLIND, 3))


def blind_status(values: dict[str, Any], channel: int) -> int | None:
    """Closed percent 0...100 from a position reply, None if unknown or another channel."""
    if values.get("CMD") != 4 or values.get("CHN") not in (channel, 0xF):
        return None
    position = values.get("POS")
    return None if position is None or position > 100 else int(position)
