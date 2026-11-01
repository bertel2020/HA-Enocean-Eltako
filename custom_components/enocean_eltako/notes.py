"""Notes for the installation documentation: free text per gateway and per device.

Home Assistant cannot know where an actuator sits in the cabinet or when a battery was changed,
so the user writes it down. Kept in a store of its own per gateway (not in the subentries, so
no schema step), keyed by the device address, which survives deleting and adding a device again.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

STORAGE_VERSION = 1
MAX_NOTE = 500
MAX_MANUAL = 200  # entries per gateway
MANUAL_FIELDS = {"name": 80, "address": 40, "function": 200}
SAVE_DELAY = 2  # seconds: typing makes one write, not one per key


def device_key(subentry: ConfigSubentry) -> str:
    """The key of a device's note: its address, which a deleted and re-added device keeps."""
    return subentry.unique_id or subentry.subentry_id


class Notes:
    """The notes of one gateway."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.notes.{entry_id}"
        )
        self.gateway = ""
        self.devices: dict[str, str] = {}
        # the last sender test of a device: {"time": ..., "results": {profile: result}}
        self.tests: dict[str, dict[str, Any]] = {}
        # devices Home Assistant cannot see (buttons taught in directly ...), written by hand
        self.manual: list[dict[str, str]] = []

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        self.gateway = str(stored.get("gateway", ""))
        self.devices = {str(k): str(v) for k, v in stored.get("devices", {}).items()}
        self.tests = {str(k): dict(v) for k, v in stored.get("tests", {}).items()}
        self.manual = [{k: str(v) for k, v in e.items()} for e in stored.get("manual", [])]

    def _data(self) -> dict[str, Any]:
        return {
            "gateway": self.gateway,
            "devices": self.devices,
            "tests": self.tests,
            "manual": self.manual,
        }

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

    def set_manual(self, entries: list[dict[str, str]]) -> None:
        """Replace the entries made by hand; one without any text is dropped."""
        self.manual = [
            {"id": e["id"], **{k: e.get(k, "").strip()[:n] for k, n in MANUAL_FIELDS.items()}}
            for e in entries[:MAX_MANUAL]
            if any(e.get(k, "").strip() for k in MANUAL_FIELDS)
        ]
        self._save()

    def set_test(self, key: str, results: dict[str, str]) -> None:
        self.tests[key] = {
            "time": dt_util.utcnow().isoformat(timespec="seconds"),
            "results": results,
        }
        self._save()

    async def async_flush(self) -> None:
        """Write what is waiting (on unload)."""
        await self._store.async_save(self._data())

    async def async_remove(self) -> None:
        await self._store.async_remove()
