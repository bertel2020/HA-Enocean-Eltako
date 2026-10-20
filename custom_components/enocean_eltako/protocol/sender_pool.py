"""Sender ID pool (E3): IDs are handed out, never typed in by hand.

Radio gateways send only from base ID + 0...127 (TCM limit). Bus groups use a freely chosen
range, default 00-00-B0-00 ... 00-00-B0-7F, entered into the actuators with PCT14.
A released ID stays blocked until its teach-out is confirmed, so it cannot be handed to a new
device while an old actuator still reacts to it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .ids import format_id, parse_id

POOL_SIZE = 128
BUS_POOL_START = 0x0000B000


class SenderState(StrEnum):
    ASSIGNED = "assigned"
    BLOCKED = "blocked"  # released, teach-out not yet confirmed


class SenderIdError(ValueError):
    """An ID cannot be assigned; reason is a translation key."""

    def __init__(self, sender: int, reason: str) -> None:
        super().__init__(f"{format_id(sender)}: {reason}")
        self.sender = sender
        self.reason = reason


@dataclass(frozen=True, slots=True)
class Allocation:
    owner: str  # e.g. subentry ID + sender profile
    state: SenderState = SenderState.ASSIGNED


class SenderPool:
    """IDs start ... start + size - 1 of one gateway or bus group."""

    def __init__(
        self,
        start: int,
        size: int = POOL_SIZE,
        *,
        is_taken_elsewhere: Callable[[int], bool] = lambda _: False,
    ) -> None:
        self.start = start
        self.size = size
        self._taken_elsewhere = is_taken_elsewhere
        self._allocations: dict[int, Allocation] = {}

    def __contains__(self, sender: int) -> bool:
        return self.start <= sender < self.start + self.size

    def get(self, sender: int) -> Allocation | None:
        return self._allocations.get(sender)

    def allocations(self) -> list[tuple[int, Allocation]]:
        return sorted(self._allocations.items())

    def owner_ids(self, owner: str) -> list[int]:
        return sorted(s for s, a in self._allocations.items() if a.owner == owner)

    def next_free(self) -> int | None:
        for sender in range(self.start, self.start + self.size):
            if self._is_free(sender):
                return sender
        return None

    def free_count(self) -> int:
        return sum(self._is_free(s) for s in range(self.start, self.start + self.size))

    def allocate(self, owner: str) -> int:
        """Assign the next free ID; raises SenderIdError('pool_exhausted')."""
        if (sender := self.next_free()) is None:
            raise SenderIdError(self.start, "pool_exhausted")
        self._allocations[sender] = Allocation(owner)
        return sender

    def assign(self, sender: int, owner: str) -> None:
        """Assign a chosen ID (e.g. kept from the old integration)."""
        if sender not in self:
            raise SenderIdError(sender, "out_of_range")
        current = self._allocations.get(sender)
        if current is not None and current.state is SenderState.BLOCKED:
            raise SenderIdError(sender, "blocked")
        if (current is not None and current.owner != owner) or (
            current is None and self._taken_elsewhere(sender)
        ):
            raise SenderIdError(sender, "in_use")
        self._allocations[sender] = Allocation(owner)

    def release(self, sender: int) -> None:
        """Owner removed: block the ID until the teach-out is confirmed."""
        current = self._allocations.get(sender)
        if current is not None and current.state is SenderState.ASSIGNED:
            self._allocations[sender] = Allocation(current.owner, SenderState.BLOCKED)

    def confirm_teach_out(self, sender: int) -> None:
        current = self._allocations.get(sender)
        if current is not None and current.state is SenderState.BLOCKED:
            del self._allocations[sender]

    def _is_free(self, sender: int) -> bool:
        return sender not in self._allocations and not self._taken_elsewhere(sender)

    def as_dict(self) -> dict[str, Any]:
        return {
            "start": format_id(self.start),
            "size": self.size,
            "allocations": {
                format_id(s): {"owner": a.owner, "state": a.state.value}
                for s, a in sorted(self._allocations.items())
            },
        }

    def load(self, data: dict[str, Any]) -> None:
        """Restore allocations saved with as_dict(); IDs outside the range are dropped."""
        self._allocations = {}
        for text, item in data.get("allocations", {}).items():
            sender = parse_id(text)
            if sender in self:
                self._allocations[sender] = Allocation(item["owner"], SenderState(item["state"]))


class SenderRegistry:
    """All pools plus reserved IDs (device IDs, radio aliases): no ID twice anywhere."""

    def __init__(self) -> None:
        self._pools: dict[str, SenderPool] = {}
        self._reserved: dict[int, str] = {}

    def create_pool(self, key: str, start: int, size: int = POOL_SIZE) -> SenderPool:
        pool = SenderPool(start, size, is_taken_elsewhere=lambda s: self._taken(s, key))
        self._pools[key] = pool
        return pool

    def remove_pool(self, key: str) -> None:
        self._pools.pop(key, None)

    def reserve(self, sender: int, owner: str) -> Callable[[], None]:
        """Mark a foreign ID (a device's own ID, a bus alias) as unusable as sender."""
        self._reserved[sender] = owner
        return lambda: self._reserved.pop(sender, None)

    def in_pool(self, sender: int) -> bool:
        """The ID lies in one of our pools (our own sender, not a foreign device)."""
        return any(sender in pool for pool in self._pools.values())

    def _taken(self, sender: int, pool_key: str) -> bool:
        if sender in self._reserved:
            return True
        return any(
            key != pool_key and pool.get(sender) is not None for key, pool in self._pools.items()
        )
