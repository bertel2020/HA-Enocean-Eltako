"""Eltako shutter actuators (FSB14, FSB61, FSB71, FJ62).

G5-3F-7F (status, not an official profile), same sender ID for both forms:
    RPS 0x70 = upper end position reached, 0x50 = lower end position reached,
        0x01 = started moving up, 0x02 = started moving down.
    4BS after a stop: DB3/DB2 = driven time in 100 ms (MSB/LSB), DB1 = direction
        0x01 up / 0x02 down, DB0 = 0x0A.

H5-3F-7F = A5-3F-7F:eltako (command; officially A5-3F-7F is manufacturer specific):
    DB2 = run time in seconds 1...255 (DB0.1 = 0) or DB3/DB2 = run time in 100 ms (DB0.1 = 1),
    DB1 = command 0x00 stop, 0x01 up, 0x02 down, DB0.2 = lock, DB0.3 = LRN (1 = data).
    Teach-in: 4BS FF F8 0D 80 (teach-in function 180/200 on the FSB14).
"""

from __future__ import annotations

from typing import Any

from ..teach_in import encode_teach_in_4bs

TEACH_IN = encode_teach_in_4bs("A5-3F-7F")

STOP, UP, DOWN = 0x00, 0x01, 0x02
STATUS_RPS = {0x70: "open", 0x50: "closed", 0x01: "opening", 0x02: "closing"}


def decode_status(data: bytes) -> dict[str, Any] | None:
    if len(data) == 1:
        state = STATUS_RPS.get(data[0])
        return {"state": state} if state else None
    if len(data) == 4 and data[3] == 0x0A and data[2] in (UP, DOWN):
        return {
            "driven_time": ((data[0] << 8) | data[1]) / 10,
            "direction": "up" if data[2] == UP else "down",
        }
    return None


def encode_command(command: int, seconds: float = 0, *, lock: bool = False) -> bytes:
    """Stop/up/down; times above 25.5 s or with tenths use the 100 ms form."""
    db0 = 0x08 | (0x04 if lock else 0)
    if command == STOP:
        return bytes([0, 0, STOP, db0])
    tenths = round(seconds * 10)
    if tenths % 10 == 0 and 1 <= tenths // 10 <= 255:
        return bytes([0, tenths // 10, command, db0])
    tenths = max(1, min(0xFFFF, tenths))
    return bytes([tenths >> 8, tenths & 0xFF, command, db0 | 0x02])
