"""Bus group: all gateways on the same Eltako RS485 bus (FGW14-USB, FAM14).

Commands for bus actors go to the group, not to one gateway. The group sends over the first
usable member and fails over to the next one when a member is offline or the send fails.
An on-demand member (typically the FAM14) is connected only when the group needs it and is
disconnected again after IDLE_TIMEOUT without sends, so PCT14 can use it in between.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Hashable
from dataclasses import dataclass, field

from .gateway import Gateway
from .send_queue import DEFAULT_CONFIRM_TIMEOUT, Priority, SendQueue, SendResult
from .telegram import RadioTelegram

_LOGGER = logging.getLogger(__name__)

IDLE_TIMEOUT = 300.0  # seconds an on-demand member stays connected after its last send
CONNECT_TIMEOUT = 5.0

# results after which the next member is tried
FAILOVER_RESULTS = (SendResult.FAILED, SendResult.UNCONFIRMED)


@dataclass(eq=False)
class BusMember:
    key: str  # config entry ID
    name: str
    gateway: Gateway
    queue: SendQueue
    on_demand: bool = False
    idle_timeout: float = IDLE_TIMEOUT
    _idle: asyncio.TimerHandle | None = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @property
    def connected(self) -> bool:
        return self.gateway.connected

    async def ensure_connected(self) -> bool:
        """Connect an on-demand member; False when that fails."""
        async with self._lock:
            if not self.gateway.connected:
                try:
                    await self.gateway.connect(timeout=CONNECT_TIMEOUT)
                except (OSError, TimeoutError) as err:
                    _LOGGER.warning("Bus gateway %s not reachable: %s", self.name, err)
                    return False
                _LOGGER.debug("Bus gateway %s connected on demand", self.name)
        self._touch()
        return True

    def _touch(self) -> None:
        if not self.on_demand:
            return
        if self._idle is not None:
            self._idle.cancel()
        self._idle = asyncio.get_running_loop().call_later(self.idle_timeout, self._idle_out)

    def _idle_out(self) -> None:
        self._idle = None
        if self.gateway.connected and len(self.queue) == 0:
            _LOGGER.debug("Bus gateway %s idle, disconnecting", self.name)
            asyncio.get_running_loop().create_task(self.gateway.disconnect())

    def cancel_idle(self) -> None:
        if self._idle is not None:
            self._idle.cancel()
            self._idle = None


class BusGroup:
    def __init__(self, key: str) -> None:
        self.key = key
        self._members: dict[str, BusMember] = {}
        self.failovers = 0

    def __len__(self) -> int:
        return len(self._members)

    @property
    def members(self) -> list[BusMember]:
        return list(self._members.values())

    def add(self, member: BusMember) -> Callable[[], None]:
        self._members[member.key] = member
        return lambda: self.remove(member.key)

    def remove(self, key: str) -> None:
        if (member := self._members.pop(key, None)) is not None:
            member.cancel_idle()

    def candidates(self) -> list[BusMember]:
        """Connected always-on members first, then other always-on, then on-demand."""
        return sorted(self._members.values(), key=lambda m: (m.on_demand, not m.connected, m.name))

    async def submit(
        self,
        telegram: RadioTelegram,
        priority: Priority = Priority.USER,
        *,
        key: Hashable | None = None,
        expect: Callable[[RadioTelegram], bool] | None = None,
        timeout: float = DEFAULT_CONFIRM_TIMEOUT,
    ) -> SendResult:
        result = SendResult.FAILED
        for index, member in enumerate(self.candidates()):
            if index:
                self.failovers += 1
                _LOGGER.info("Bus group %s: failover to %s after %s", self.key, member.name, result)
            if member.on_demand:
                if not await member.ensure_connected():
                    continue
            elif not member.connected:
                continue
            result = await member.queue.submit(
                telegram, priority, key=key, expect=expect, timeout=timeout
            )
            member._touch()
            if result not in FAILOVER_RESULTS:
                return result
        return result

    def pause(self) -> None:
        """Hold back all sends to the bus (memory import)."""
        for member in self._members.values():
            member.queue.pause()

    def resume(self) -> None:
        for member in self._members.values():
            member.queue.resume()

    def as_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "failovers": self.failovers,
            "members": [
                {"name": m.name, "on_demand": m.on_demand, "connected": m.connected}
                for m in self.candidates()
            ],
        }
