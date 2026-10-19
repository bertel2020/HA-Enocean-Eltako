"""Protocol-neutral radio telegram shared by ESP2 and ESP3."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .ids import BROADCAST, format_id


class Rorg(IntEnum):
    """Radio telegram types (ESP3 RORG values)."""

    RPS = 0xF6
    BS1 = 0xD5
    BS4 = 0xA5
    VLD = 0xD2
    MSC = 0xD1
    UTE = 0xD4


@dataclass(frozen=True, slots=True)
class RadioTelegram:
    """One radio telegram; data is the payload without RORG, sender and status."""

    rorg: int
    data: bytes
    sender: int
    status: int = 0
    destination: int = BROADCAST
    dbm: int | None = None

    def __str__(self) -> str:
        return (
            f"{self.rorg:02X} {self.data.hex(' ').upper()} from {format_id(self.sender)}"
            f" status {self.status:02X}" + (f" {self.dbm} dBm" if self.dbm is not None else "")
        )
