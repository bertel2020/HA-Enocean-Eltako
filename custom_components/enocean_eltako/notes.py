"""Notes for the installation documentation: free text per gateway and per device.

Home Assistant cannot know where an actuator sits in the cabinet or when a battery was changed,
so the user writes it down. Kept in a store of its own per gateway (not in the subentries, so
no schema step), keyed by the device address, which survives deleting and adding a device again.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_VERSION = 1
MAX_NOTE = 500
SAVE_DELAY = 2  # seconds: typing makes one write, not one per key


class Notes:
    """The notes of one gateway."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.notes.{entry_id}"
        )
        self.gateway = ""
        self.devices: dict[str, str] = {}

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        self.gateway = str(stored.get("gateway", ""))
        self.devices = {str(k): str(v) for k, v in stored.get("devices", {}).items()}

    def _data(self) -> dict[str, Any]:
        return {"gateway": self.gateway, "devices": self.devices}

    def _save(self) -> None:
        self._store.async_delay_save(self._data, SAVE_DELAY)

    def set_gateway(self, text: str) -> None:
        self.gateway = text.strip()[:MAX_NOTE]
        self._save()

    def set_device(self, key: str, text: str) -> None:
        if text := text.strip()[:MAX_NOTE]:
            self.devices[key] = text
        else:
            self.devices.pop(key, None)
        self._save()

    async def async_flush(self) -> None:
        """Write what is waiting (on unload)."""
        await self._store.async_save(self._data())

    async def async_remove(self) -> None:
        await self._store.async_remove()
