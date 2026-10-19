"""EnOcean IDs: 32-bit integers in code, "FF-AA-80-00" in config and UI."""

from __future__ import annotations

import re

# four hex bytes with one separator used throughout ("-", ":" or " "), or none ("0x" allowed)
_ID_RE = re.compile(
    r"^(?:0[xX])?[0-9A-Fa-f]{8}$|^[0-9A-Fa-f]{2}([-: ])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){2}$"
)

BASE_ID_MIN = 0xFF800000
BASE_ID_MAX = 0xFFFFFF80
BROADCAST = 0xFFFFFFFF


def parse_id(text: str) -> int:
    """Parse "FF-AA-80-00", "FF:AA:80:00", "FF AA 80 00", "FFAA8000" or "0xFFAA8000".

    Mixed separators are refused so that typing errors show; raises ValueError.
    """
    text = text.strip()
    if not _ID_RE.match(text):
        raise ValueError(f"invalid EnOcean ID: {text!r}")
    return int(re.sub(r"[-: ]|^0[xX]", "", text), 16)


def format_id(value: int) -> str:
    """Format a 32-bit ID as "FF-AA-80-00"."""
    return "-".join(f"{b:02X}" for b in value.to_bytes(4, "big"))


def is_valid_base_id(value: int) -> bool:
    """A base ID lies in FF-80-00-00 ... FF-FF-FF-80 and is a multiple of 0x80."""
    return BASE_ID_MIN <= value <= BASE_ID_MAX and value & 0x7F == 0
