"""4BS teach-in telegrams (variant 2: EEP and manufacturer in the telegram)."""

from __future__ import annotations

from dataclasses import dataclass

MANUFACTURER_ELTAKO = 0x00D


@dataclass(frozen=True, slots=True)
class TeachIn4BS:
    func: int
    type: int
    manufacturer: int

    @property
    def eep(self) -> str:
        return f"A5-{self.func:02X}-{self.type:02X}"


def encode_teach_in_4bs(eep: str, manufacturer: int = MANUFACTURER_ELTAKO) -> bytes:
    """DB3 = FUNC(6) TYPE(7..6), DB2 = TYPE(4..0) MANUF(10..8), DB1 = MANUF(7..0), DB0 = 0x80.

    A5-38-08 with Eltako -> E0 40 0D 80, A5-3F-7F -> FF F8 0D 80.
    """
    _, func, type_ = (int(part, 16) for part in eep.split("-"))
    value = (func << 26) | (type_ << 19) | (manufacturer << 8) | 0x80
    return value.to_bytes(4, "big")


def decode_teach_in_4bs(data: bytes) -> TeachIn4BS | None:
    """EEP and manufacturer of a variant-2 teach-in telegram (LRN bit 0, LRN type 1)."""
    if len(data) != 4 or data[3] & 0x08 or not data[3] & 0x80:
        return None
    value = int.from_bytes(data, "big")
    return TeachIn4BS(
        func=value >> 26, type=(value >> 19) & 0x7F, manufacturer=(value >> 8) & 0x7FF
    )
