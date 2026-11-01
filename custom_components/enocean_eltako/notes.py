"""What the user writes down for the installation documentation, and its event log.

Home Assistant cannot know where an actuator sits in the cabinet, which fuse feeds it or when a
battery was changed. Kept in a store of its own per gateway (not in the subentries), keyed by the
device address, which survives deleting and adding a device again. Store version 2: a device's
note became a dict of typed fields; version 1 held its note as a plain string.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

STORAGE_VERSION = 2
MAX_NOTE = 500
# the typed fields of a device and their longest text; installed is a date (YYYY-MM-DD)
FIELDS = {
    "location": 120,
    "circuit": 80,
    "fuse": 40,
    "installed": 10,
    "revision": 40,
    "power": 80,
    "note": MAX_NOTE,
}
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
MAX_MANUAL = 200  # entries per gateway
MANUAL_FIELDS = {"name": 80, "address": 40, "function": 200}
MAX_LOG = 500  # events per gateway
MAX_LINKS = 500  # links entered by hand per gateway
# the fields of a link entered by hand and their longest text
LINK_FIELDS = {"from_id": 40, "from_name": 80, "to_key": 64, "to_name": 80, "role": 60, "learn": 80}
SAVE_DELAY = 2  # seconds: typing makes one write, not one per key


def device_key(subentry: ConfigSubentry) -> str:
    """The key of a device's note: its address, which a deleted and re-added device keeps."""
    return subentry.unique_id or subentry.subentry_id


class _NotesStore(Store[dict[str, Any]]):
    """Version 1 kept a device's note as a string; version 2 keeps a dict of typed fields."""

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        if old_major_version < 2:
            old_data["devices"] = {
                key: {"note": value} if isinstance(value, str) else value
                for key, value in old_data.get("devices", {}).items()
            }
        return old_data


class Notes:
    """The notes of one gateway."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = _NotesStore(hass, STORAGE_VERSION, f"{DOMAIN}.notes.{entry_id}")
        self.gateway = ""
        self.devices: dict[str, dict[str, str]] = {}  # key -> typed fields (only those set)
        # the last sender test of a device: {"time": ..., "results": {profile: result}}
        self.tests: dict[str, dict[str, Any]] = {}
        # devices Home Assistant cannot see (buttons taught in directly ...), written by hand
        self.manual: list[dict[str, str]] = []
        # what happened to the installation, oldest first: {"time", "kind", "device", "detail"}
        self.log: list[dict[str, str]] = []
        # links entered by hand, {id, from_id, from_name, to_key, to_name, role, learn}
        self.links: list[dict[str, str]] = []
        # what the user adds to a link that is derived (assigned, declared): its learn position
        self.link_info: dict[str, dict[str, str]] = {}
        # the devices as they were at the last load, to tell what was added or removed since
        self.known: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        stored = await self._store.async_load() or {}
        self.gateway = str(stored.get("gateway", ""))
        self.devices = {
            str(k): {f: str(v[f]) for f in FIELDS if v.get(f)}
            for k, v in stored.get("devices", {}).items()
            if isinstance(v, dict)
        }
        self.tests = {str(k): dict(v) for k, v in stored.get("tests", {}).items()}
        self.manual = [{k: str(v) for k, v in e.items()} for e in stored.get("manual", [])]
        self.log = [{k: str(v) for k, v in e.items()} for e in stored.get("log", [])]
        self.known = {str(k): dict(v) for k, v in stored.get("known", {}).items()}
        self.links = [{k: str(v) for k, v in e.items()} for e in stored.get("links", [])]
        self.link_info = {str(k): dict(v) for k, v in stored.get("link_info", {}).items()}

    def _data(self) -> dict[str, Any]:
        return {
            "gateway": self.gateway,
            "devices": self.devices,
            "tests": self.tests,
            "manual": self.manual,
            "log": self.log,
            "known": self.known,
            "links": self.links,
            "link_info": self.link_info,
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._data, SAVE_DELAY)

    def add_log(self, kind: str, device: str = "", detail: str = "", profile: str = "") -> None:
        """Note an event of the installation (not every edit): the newest MAX_LOG are kept."""
        self.log.append(
            {
                "time": dt_util.utcnow().isoformat(timespec="seconds"),
                "kind": kind,
                "device": device,
                "detail": detail,
                "profile": profile,
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

    def device(self, key: str) -> dict[str, str]:
        """All typed fields of a device, empty where nothing is written."""
        return {f: self.devices.get(key, {}).get(f, "") for f in FIELDS}

    def set_fields(self, key: str, values: dict[str, str]) -> bool:
        """Set typed fields of a device (an empty text clears one); False for a bad value."""
        clean = {}
        for field, value in values.items():
            value = value.strip()
            if field not in FIELDS or len(value) > FIELDS[field]:
                return False
            if field == "installed" and value and not _DATE.fullmatch(value):
                return False
            clean[field] = value
        current = self.devices.setdefault(key, {})
        for field, value in clean.items():
            if value:
                current[field] = value
            else:
                current.pop(field, None)
        if not current:
            del self.devices[key]
        self._save()
        return True

    def set_device(self, key: str, text: str) -> None:
        """A device's note."""
        self.set_fields(key, {"note": text[:MAX_NOTE]})

    def import_from(self, gateway: dict[str, Any], *, overwrite: bool) -> tuple[int, int, int]:
        """Take over the notes and manual entries of a documentation export of this gateway.

        Without overwrite only what is empty here is filled in. Returns how many notes
        (gateway and devices), manual entries and links (entered ones, learn positions) were taken.
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
            if not key:
                continue
            gained = {}
            for field in FIELDS:
                text = str(device.get(field) or "").strip()
                if text and (overwrite or not self.devices.get(key, {}).get(field)):
                    gained[field] = text[: FIELDS[field]]
            if "installed" in gained and not _DATE.fullmatch(gained["installed"]):
                del gained["installed"]
            fresh = {f: v for f, v in gained.items() if v != self.devices.get(key, {}).get(f)}
            if fresh and self.set_fields(key, fresh):
                notes += len(fresh)
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
        links = self._import_links(gateway.get("links", []), overwrite=overwrite)
        return notes, len(taken), links

    def _import_links(self, links: list[Any], *, overwrite: bool) -> int:
        """Entered links not here yet, and learn positions of derived links that have none."""
        if overwrite:
            self.links = []
        seen = {
            (e["from_id"], e["from_name"], e["to_key"], e["to_name"], e["role"]) for e in self.links
        }
        added, taken = [], 0
        for link in (e for e in links if isinstance(e, dict)):
            if link.get("source") == "entered":
                fields = {k: str(link.get(k) or "") for k in LINK_FIELDS}
                signature = (
                    fields["from_id"],
                    fields["from_name"],
                    fields["to_key"],
                    fields["to_name"],
                    fields["role"],
                )
                if signature not in seen:
                    seen.add(signature)
                    added.append({"id": uuid.uuid4().hex[:8], **fields})
            elif (learn := str(link.get("learn") or "").strip()) and (
                overwrite or not self.link_info.get(str(link.get("key")), {}).get("learn")
            ):
                if (key := str(link.get("key") or "")) and self.link_info.get(key, {}).get(
                    "learn"
                ) != learn:
                    self.set_link_learn(key, learn)
                    taken += 1
        if added or overwrite:
            self.set_links([*self.links, *added])
        return taken + len(added)

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

    def set_links(self, entries: list[dict[str, str]]) -> None:
        """Replace the links entered by hand; one needs a source and a target to stay."""
        links = []
        for e in entries[:MAX_LINKS]:
            link = {"id": e["id"], **{k: e.get(k, "").strip()[:n] for k, n in LINK_FIELDS.items()}}
            if (link["from_id"] or link["from_name"]) and (link["to_key"] or link["to_name"]):
                links.append(link)
        self.links = links
        self._save()

    def set_link_learn(self, key: str, learn: str) -> None:
        """The learn position written down for a derived link (an empty text clears it)."""
        if learn := learn.strip()[: LINK_FIELDS["learn"]]:
            self.link_info[key] = {"learn": learn}
        else:
            self.link_info.pop(key, None)
        self._save()

    def last_teach_in(self, device: str, profile: str) -> str | None:
        """When a teach-in of this sender profile was last sent from here."""
        for event in reversed(self.log):
            if (
                event["kind"] == "teach_in"
                and event["device"] == device
                and event.get("profile") == profile
            ):
                return event["time"]
        return None

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
