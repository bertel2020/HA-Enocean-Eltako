"""Shared state of all gateway entries: dispatcher, sender IDs, monitor, bus groups."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN
from .protocol.bus_group import BusGroup, BusMember
from .protocol.dispatcher import Dispatcher, ReceivedTelegram
from .protocol.monitor import TelegramMonitor
from .protocol.sender_pool import BUS_POOL_START, SenderRegistry
from .senders import SenderStore, bus_key


@dataclass
class BusGroupRuntime:
    group: BusGroup
    senders: SenderStore  # bus sender IDs (00-00-B0-xx), shared by all members


@dataclass
class Hub:
    """One per Home Assistant instance; every gateway entry feeds its dispatcher."""

    dispatcher: Dispatcher = field(default_factory=Dispatcher)
    senders: SenderRegistry = field(default_factory=SenderRegistry)
    monitor: TelegramMonitor = field(default_factory=TelegramMonitor)
    bus_groups: dict[str, BusGroupRuntime] = field(default_factory=dict)
    # unknown senders heard (last telegram each), offered under "Add device"
    discovered: dict[int, ReceivedTelegram] = field(default_factory=dict)
    hidden: dict[str, set[int]] = field(default_factory=dict)  # per gateway entry, stored
    _bus_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def __post_init__(self) -> None:
        self.dispatcher.add_monitor(self.monitor.received)

    async def async_join_bus_group(
        self, hass: HomeAssistant, key: str, member: BusMember
    ) -> BusGroupRuntime:
        """Add a gateway to its bus group, creating the group and its sender pool."""
        async with self._bus_lock:
            if (runtime := self.bus_groups.get(key)) is None:
                pool = self.senders.create_pool(bus_key(key), BUS_POOL_START)
                store = SenderStore(hass, bus_key(key), pool)
                await store.async_load()
                runtime = self.bus_groups[key] = BusGroupRuntime(BusGroup(key), store)
            runtime.group.add(member)
            return runtime

    def leave_bus_group(self, key: str, member_key: str) -> None:
        if (runtime := self.bus_groups.get(key)) is None:
            return
        runtime.group.remove(member_key)
        if not len(runtime.group):
            del self.bus_groups[key]
            self.senders.remove_pool(bus_key(key))


DATA_HUB: HassKey[Hub] = HassKey(DOMAIN)


def async_get_hub(hass: HomeAssistant) -> Hub:
    if (hub := hass.data.get(DATA_HUB)) is None:
        hub = hass.data[DATA_HUB] = Hub()
    return hub
