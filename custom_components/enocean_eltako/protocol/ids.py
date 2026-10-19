"""EnOcean IDs: 32-bit integers in code, "FF-AA-80-00" in config and UI."""

from __future__ import annotations

import re

_ID_RE = re.compile(r"^[0-9A-Fa-f]{2}([-:]?[0-9A-Fa-f]{2}){3}$")

BASE_ID_MIN = 0xFF800000
BASE_ID_MAX = 0xFFFFFF80
BROADCAST = 0xFFFFFFFF


def parse_id(text: str) -> int:
    """Parse "FF-AA-80-00", "FF:AA:80:00" or "FFAA8000"; raise ValueError otherwise."""
    text = text.strip()
    if not _ID_RE.match(text):
        raise ValueError(f"invalid EnOcean ID: {text!r}")
    return int(re.sub(r"[-:]", "", text), 16)


def format_id(value: int) -> str:
    """Format a 32-bit ID as "FF-AA-80-00"."""
    return "-".join(f"{b:02X}" for b in value.to_bytes(4, "big"))


def is_valid_base_id(value: int) -> bool:
    """A base ID lies in FF-80-00-00 ... FF-FF-FF-80 and is a multiple of 0x80."""
    return BASE_ID_MIN <= value <= BASE_ID_MAX and value & 0x7F == 0
