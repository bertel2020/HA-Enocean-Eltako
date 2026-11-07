"""Persistence of sender ID pools: one per radio gateway entry, one per bus group."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .protocol.ids import format_id, parse_id
from .protocol.sender_pool import Allocation, SenderPool, SenderState

STORAGE_VERSION = 1
SAVE_DELAY = 5  # seconds


def radio_key(entry_id: str) -> str:
    return entry_id


def bus_key(group: str) -> str:
    return f"bus_{group}"


def retired_key(base_id: int) -> str:
    """The IDs of a removed gateway wait here, by its base ID, for the next gateway of that base."""
    return f"retired_{format_id(base_id)}"


def _store(hass: HomeAssistant, key: str) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.senders.{key}")


class SenderStore:
    """Loads a pool on setup and saves it (debounced) after every change."""

    def __init__(self, hass: HomeAssistant, key: str, pool: SenderPool) -> None:
        self.pool = pool
        self._store = _store(hass, key)

    async def async_load(self) -> None:
        if (data := await self._store.async_load()) is not None:
            self.pool.load(data)

    async def async_save(self) -> None:
        await self._store.async_save(self.pool.as_dict())

    def async_schedule_save(self) -> None:
        self._store.async_delay_save(self.pool.as_dict, SAVE_DELAY)


async def async_remove_store(hass: HomeAssistant, key: str) -> None:
    await _store(hass, key).async_remove()


async def async_retire_pool(hass: HomeAssistant, entry_id: str, base_id: int) -> None:
    """A gateway entry is removed: its IDs stay blocked, as the actuators still react to them.

    Assigned and blocked IDs move to a store by base ID; a gateway added again with that base
    ID takes them over (async_adopt_retired) and the user confirms each teach-out there.
    """
    store = _store(hass, radio_key(entry_id))
    if (data := await store.async_load()) is not None:
        retired = _store(hass, retired_key(base_id))
        allocations = dict((await retired.async_load() or {}).get("allocations", {}))
        for text, item in data.get("allocations", {}).items():
            allocations.setdefault(text, {"owner": item["owner"], "state": "blocked"})
        if allocations:
            await retired.async_save({"allocations": allocations})
    await store.async_remove()


async def async_adopt_retired(hass: HomeAssistant, store: SenderStore, base_id: int) -> None:
    """Take over the blocked IDs of a gateway with this base ID that was removed before."""
    retired = _store(hass, retired_key(base_id))
    if (data := await retired.async_load()) is None:
        return
    for text, item in data.get("allocations", {}).items():
        sender = parse_id(text)
        if sender in store.pool and store.pool.get(sender) is None:
            store.pool.restore(sender, Allocation(item["owner"], SenderState.BLOCKED))
    await store.async_save()
    await retired.async_remove()
