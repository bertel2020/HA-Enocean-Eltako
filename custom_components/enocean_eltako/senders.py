"""Persistence of the sender ID pool of one gateway entry."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .protocol.sender_pool import SenderPool

STORAGE_VERSION = 1
SAVE_DELAY = 5  # seconds


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.senders.{entry_id}")


class SenderStore:
    """Loads a pool on setup and saves it (debounced) after every change."""

    def __init__(self, hass: HomeAssistant, entry_id: str, pool: SenderPool) -> None:
        self.pool = pool
        self._store = _store(hass, entry_id)

    async def async_load(self) -> None:
        if (data := await self._store.async_load()) is not None:
            self.pool.load(data)

    def async_schedule_save(self) -> None:
        self._store.async_delay_save(self.pool.as_dict, SAVE_DELAY)


async def async_remove_store(hass: HomeAssistant, entry_id: str) -> None:
    await _store(hass, entry_id).async_remove()
