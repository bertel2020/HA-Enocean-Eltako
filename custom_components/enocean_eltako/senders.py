"""Persistence of sender ID pools: one per radio gateway entry, one per bus group."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .protocol.sender_pool import SenderPool

STORAGE_VERSION = 1
SAVE_DELAY = 5  # seconds


def radio_key(entry_id: str) -> str:
    return entry_id


def bus_key(group: str) -> str:
    return f"bus_{group}"


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
