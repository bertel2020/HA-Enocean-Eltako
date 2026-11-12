"""What the telegrams heard tell of a FAM14 bus: which device addresses answer, and from which
base ID. Read only: this module looks at telegrams that arrived anyway, it never sends.

Published facts it rests on (Eltako, "Inhalte der Eltako-Funktelegramme", section
"Bestätigungs-Telegramme der Baureihe 14", and the manuals of FAM14 and FGW14):

- Once series 14 actuators have a device address, the FAM14 queries their confirmation
  telegrams (rotary switch BA at 2, 4, 5 or 7; up to about 10 seconds per round) and sends them
  by radio. The ID of such a radio telegram is the base ID of the TCM300 in the FAM14 plus the
  device address; a multi-channel actuator has consecutive device addresses, one per channel.
- Device addresses are 1 to 126.
- A base ID lies in FF-80-00-00 ... FF-FF-FF-80 and is a multiple of 0x80 (EnOcean).

NOT confirmed with hardware (no FAM14 was available while writing this):
- that a FAM14 whose base ID is not written down can be told by the IDs alone (the block of
  128 IDs that holds them is only a candidate: another gateway's senders may lie there too);
- what ID a confirmation telegram carries on the wire of the bus (an FGW14-USB or a FAM14 on
  USB). The FGW14 manual only says that "answers of the series 14 actuators take the ID range
  1-254"; that the ID there is the plain device address is an assumption (WIRED_ASSUMED).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..ids import BASE_ID_MAX, BASE_ID_MIN, format_id

ADDRESSES = 126
BLOCK = 0x80  # a base ID and the 127 IDs above it
WIRED_ASSUMED = True  # the ID on the wire is the device address: an assumption, see above


@dataclass(frozen=True)
class Heard:
    """One sender heard: its ID, the gateway that heard it and how, its last telegram."""

    sender: int
    gateway: str
    wired: bool  # heard by a gateway on the bus (FGW14-USB, FAM14 on USB)
    rorg: int
    data: bytes
    time: float


@dataclass(frozen=True)
class Answer:
    """A device address that answered, and what it sent last."""

    address: int
    sender: int
    gateway: str
    wired: bool
    rorg: int
    data: bytes
    time: float
    kind: str  # see telegram_kind


def telegram_kind(rorg: int, data: bytes) -> str:
    """What a confirmation telegram of the series 14 says (Eltako, "Inhalte der Eltako-
    Funktelegramme"): on/off of a switch, an end position or start of a cover, a 4BS value
    (dim value, travel time, meter), else unknown."""
    if rorg == 0xF6 and data:
        return {
            0x70: "on",
            0x50: "off",
            0x01: "up",
            0x02: "down",
            0x30: "rocker",
            0x10: "rocker",
        }.get(data[0], "rps")
    if rorg == 0xA5:
        return "4bs"
    return "other"


def base_of(sender: int) -> tuple[int, int] | None:
    """(base ID, offset) of an ID in the base ID range with an offset that is a device address."""
    if not BASE_ID_MIN <= sender <= BASE_ID_MAX + BLOCK - 1:
        return None
    base, offset = sender & ~(BLOCK - 1) & 0xFFFFFFFF, sender & (BLOCK - 1)
    return (base, offset) if 1 <= offset <= ADDRESSES else None


def base_candidates(heard: Iterable[Heard], own: Iterable[int]) -> list[tuple[int, int]]:
    """Blocks of base IDs whose IDs were heard by radio, most first, without the gateways' own
    blocks (their senders are Home Assistant's): a hint for the FAM14's base ID, not proof."""
    own_blocks = {o & ~(BLOCK - 1) & 0xFFFFFFFF for o in own}
    counts: dict[int, set[int]] = {}
    for item in heard:
        if item.wired or (found := base_of(item.sender)) is None or found[0] in own_blocks:
            continue
        counts.setdefault(found[0], set()).add(found[1])
    return sorted(((b, len(o)) for b, o in counts.items()), key=lambda x: (-x[1], x[0]))


def answers(heard: Iterable[Heard], base: int | None) -> dict[int, Answer]:
    """The device addresses heard: by radio base + address (with the FAM14's base ID known),
    on the wire the address itself (assumed). The newest telegram of each address wins."""
    found: dict[int, Answer] = {}
    for item in heard:
        address = None
        if item.wired and 1 <= item.sender <= ADDRESSES:
            address = item.sender
        elif not item.wired and base is not None and 1 <= item.sender - base <= ADDRESSES:
            address = item.sender - base
        if address is None:
            continue
        if address in found and found[address].time >= item.time:
            continue
        found[address] = Answer(
            address,
            item.sender,
            item.gateway,
            item.wired,
            item.rorg,
            item.data,
            item.time,
            telegram_kind(item.rorg, item.data),
        )
    return found


def bus_address(sender: int, base: int) -> int | None:
    """The device address of a radio ID in the block of a FAM14 base ID, else None.

    Only base + 1 ... base + 126 are device addresses: the base ID itself and base + 127 are not.
    """
    return offset if 1 <= (offset := sender - base) <= ADDRESSES else None


def feedback_id(base: int, address: int) -> str:
    """The radio ID of a channel's confirmation telegrams: the FAM14's base ID plus its address."""
    if not 1 <= address <= ADDRESSES:
        raise ValueError(f"not a device address: {address}")
    return format_id(base + address)
