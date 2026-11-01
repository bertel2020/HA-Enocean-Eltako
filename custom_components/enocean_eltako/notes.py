"""Notes for the installation documentation: free text per gateway and per device.

Home Assistant cannot know where an actuator sits in the cabinet or when a battery was changed,
so the user writes it down. Kept in a store of its own per gateway (not in the subentries, so
no schema step), keyed by the device address, which survives deleting and adding a device again.
"""

from __future__ import annotations

import uuid
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
MAX_LOG = 500  # events per gateway
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
        # what happened to the installation, oldest first: {"time", "kind", "device", "detail"}
        self.log: list[dict[str, str]] = []
        # the devices as they were at the last load, to tell what was added or removed since
        self.known: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        self.gateway = str(stored.get("gateway", ""))
        self.devices = {str(k): str(v) for k, v in stored.get("devices", {}).items()}
        self.tests = {str(k): dict(v) for k, v in stored.get("tests", {}).items()}
        self.manual = [{k: str(v) for k, v in e.items()} for e in stored.get("manual", [])]
        self.log = [{k: str(v) for k, v in e.items()} for e in stored.get("log", [])]
        self.known = {str(k): dict(v) for k, v in stored.get("known", {}).items()}

    def _data(self) -> dict[str, Any]:
        return {
            "gateway": self.gateway,
            "devices": self.devices,
            "tests": self.tests,
            "manual": self.manual,
            "log": self.log,
            "known": self.known,
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._data, SAVE_DELAY)

    def add_log(self, kind: str, device: str = "", detail: str = "") -> None:
        """Note an event of the installation (not every edit): the newest MAX_LOG are kept."""
        self.log.append(
            {
                "time": dt_util.utcnow().isoformat(timespec="seconds"),
                "kind": kind,
                "device": device,
                "detail": detail,
            }
        )
        del self.log[:-MAX_LOG]
        self._save()

    def sync_known(self, devices: dict[str, tuple[str, list[str]]]) -> None:
        """Compare the devices now with those at the last load and log the differences.

        devices: key -> (name, sender IDs). The first load only takes the baseline.
        """
        if self.known:
            for key, (name, senders) in devices.items():
                before = self.known.get(key)
                if before is None:
                    self.add_log("device_added", key, name)
                    continue
                for sender in sorted(set(senders) - set(before.get("senders", []))):
                    self.add_log("sender_assigned", key, f"{name}: {sender}")
                for sender in sorted(set(before.get("senders", [])) - set(senders)):
                    self.add_log("sender_removed", key, f"{name}: {sender}")
            for key, before in self.known.items():
                if key not in devices:
                    self.add_log("device_removed", key, str(before.get("name", "")))
        known = {
            k: {"name": name, "senders": list(senders)} for k, (name, senders) in devices.items()
        }
        if known != self.known:
            self.known = known
            self._save()

    def set_gateway(self, text: str) -> None:
        self.gateway = text.strip()[:MAX_NOTE]
        self._save()

    def set_device(self, key: str, text: str) -> None:
        if text := text.strip()[:MAX_NOTE]:
            self.devices[key] = text
        else:
            self.devices.pop(key, None)
        self._save()

    def import_from(self, gateway: dict[str, Any], *, overwrite: bool) -> tuple[int, int]:
        """Take over the notes and manual entries of a documentation export of this gateway.

        Without overwrite only what is empty here is filled in. Returns how many notes
        (gateway and devices) and manual entries were taken.
        """
        notes = 0
        if (text := str(gateway.get("note") or "").strip()) and (overwrite or not self.gateway):
            if text[:MAX_NOTE] != self.gateway:
                notes += 1
            self.gateway = text[:MAX_NOTE]
        for device in gateway.get("devices", []):
            # a two-channel actuator's second channel has its own key; exports of 1.4.1 and
            # before carry only the address
            key = str(device.get("note_key") or device.get("id") or "")
            text = str(device.get("note") or "").strip()
            if key and text and (overwrite or key not in self.devices):
                if text[:MAX_NOTE] != self.devices.get(key):
                    notes += 1
                self.devices[key] = text[:MAX_NOTE]
        entries = [e for e in gateway.get("manual", []) if isinstance(e, dict)]
        if overwrite:
            self.manual = []
        known = {(e["name"], e["address"]) for e in self.manual}
        taken = []
        for entry in entries:
            name, address = str(entry.get("name") or ""), str(entry.get("address") or "")
            if (name, address) in known:
                continue
            known.add((name, address))
            taken.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "name": name,
                    "address": address,
                    "function": str(entry.get("function") or ""),
                }
            )
        self.set_manual([*self.manual, *taken])
        return notes, len(taken)

    def orphans(self, keys: set[str]) -> set[str]:
        """Keys of notes and test results whose device is gone (they return with the address)."""
        return (set(self.devices) | set(self.tests)) - keys

    def prune(self, keys: set[str]) -> int:
        """Drop the notes and test results of devices that are gone; how many notes went."""
        gone = self.orphans(keys)
        removed = len(gone & set(self.devices))
        for key in gone:
            self.devices.pop(key, None)
            self.tests.pop(key, None)
        if gone:
            self._save()
        return removed

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
