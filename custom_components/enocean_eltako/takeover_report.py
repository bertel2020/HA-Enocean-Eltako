"""The takeover report: what each device was in the old integration and its old -> new IDs.

Kept in the integration's own storage, so the mapping stays readable once the old integration
and its "eltako:" section are gone. A snapshot is written for every device set up here that the
old integration had, taken over or set up by hand; it is refreshed while the old entities exist.
The report also restores old entity IDs on request (the new entity gets the old ID, so
references go on working): only once the old integration's entities are gone.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.storage import Store
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN
from .protocol.ids import format_id
from .takeover import (
    TakeoverDevice,
    carried_from,
    new_entity,
    old_entities,
    primary_entity,
    registered_device,
)

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

STORAGE_VERSION = 1
DATA_REPORT: HassKey[TakeoverReport] = HassKey(f"{DOMAIN}_takeover_report")


class TakeoverReport:
    """{"closed": bool, "entries": {entry_id: {old device ID: snapshot}}} in .storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.takeover")
        self.closed = False
        self.entries: dict[str, dict[str, dict[str, Any]]] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.closed = bool(data.get("closed"))
        self.entries = data.get("entries") or {}

    async def async_save(self) -> None:
        await self._store.async_save({"closed": self.closed, "entries": self.entries})

    def devices(self, entry_id: str) -> dict[str, dict[str, Any]]:
        return self.entries.get(entry_id, {})

    @property
    def empty(self) -> bool:
        return not any(self.entries.values())


async def async_get_report(hass: HomeAssistant) -> TakeoverReport:
    if (report := hass.data.get(DATA_REPORT)) is None:
        report = TakeoverReport(hass)
        await report.async_load()
        hass.data[DATA_REPORT] = report
    return report


def area_name(hass: HomeAssistant, area_id: str) -> str:
    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else area_id


def label_names(hass: HomeAssistant, label_ids: set[str]) -> list[str]:
    registry = lr.async_get(hass)
    return [label.name if (label := registry.async_get_label(i)) else i for i in label_ids]


def set_up_entities(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> dict[int, list[er.RegistryEntry]]:
    """The registry entries of the devices set up here, by device ID (first channel only)."""
    registry = er.async_get(hass)
    found: dict[int, list[er.RegistryEntry]] = {}
    for device in entry.runtime_data.devices.values():
        if device.channel != 1:
            continue
        if (registered := registered_device(hass, entry, device)) is None:
            continue
        found[device.device_id] = er.async_entries_for_device(
            registry, registered.id, include_disabled_entities=True
        )
    return found


def _old_device(hass: HomeAssistant, entries: list[er.RegistryEntry]) -> Any:
    devices = dr.async_get(hass)
    for entity in entries:
        if entity.device_id and (device := devices.async_get(entity.device_id)) is not None:
            return device
    return None


def snapshot(
    hass: HomeAssistant,
    entries: list[er.RegistryEntry],
    new: list[er.RegistryEntry],
    name: str,
    planned: TakeoverDevice | None,
) -> dict[str, Any]:
    """What the old integration had for one device, and its old -> new entities."""
    main = primary_entity(entries)
    carried = carried_from(hass, entries)
    old_device = _old_device(hass, entries)
    labels = carried.labels.union(*(e.labels for e in entries))
    rows = []
    for old in sorted(entries, key=lambda e: (e is not main, e.entity_id)):
        target = new_entity(old, main, new)
        rows.append(
            {
                "old": old.entity_id,
                "new": target.entity_id if target else None,
                # the new entity by its unique ID: its entity ID may be changed later on
                "uid": [target.domain, target.unique_id] if target else None,
                "primary": old is main,
                "restored": False,
            }
        )
    return {
        "name": name,
        "taken_at": None,
        "carried": [],
        "old": {
            "config": planned.old if planned else None,
            "name": planned.name if planned else None,
            "senders": [format_id(s) for s in planned.senders.values()] if planned else [],
            "device_name": (old_device.name_by_user or old_device.name) if old_device else None,
            "area": area_name(hass, carried.area_id) if carried.area_id else None,
            "labels": sorted(label_names(hass, labels)),
        },
        "entities": rows,
    }


async def async_record(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    planned: list[TakeoverDevice] | None,
    taken: Mapping[int, list[str]] | None = None,
) -> None:
    """Refresh the snapshots of the devices set up here that the old integration still has.

    taken: the devices just taken over, with the options carried over.
    """
    report = await async_get_report(hass)
    stored = report.entries.setdefault(entry.entry_id, {})
    new = set_up_entities(hass, entry)
    by_id: dict[int, TakeoverDevice] = {}
    for planned_device in planned or []:
        by_id.setdefault(planned_device.device_id, planned_device)  # listed twice: the first
    titles = {d.device_id: d.subentry.title for d in entry.runtime_data.devices.values()}
    now = datetime.now(UTC).isoformat()
    changed = False
    for device_id, entries in old_entities(hass).items():
        if (mine := new.get(device_id)) is None:
            continue
        key = format_id(device_id)
        fresh = snapshot(hass, entries, mine, titles.get(device_id, key), by_id.get(device_id))
        if (before := stored.get(key)) is not None:
            fresh["taken_at"], fresh["carried"] = before["taken_at"], before["carried"]
            restored = {r["old"] for r in before["entities"] if r["restored"]}
            for row in fresh["entities"]:
                row["restored"] = row["old"] in restored
        if taken is not None and device_id in taken:
            fresh["taken_at"], fresh["carried"] = now, sorted(taken[device_id])
        if fresh != before:
            stored[key] = fresh
            changed = True
    if taken:
        report.closed = False  # something new was taken over: the view is back
        changed = True
    if changed:
        await report.async_save()


def current_new(hass: HomeAssistant, row: Mapping[str, Any]) -> str | None:
    """The new entity's ID now: found by its unique ID, so a later rename shows."""
    if row.get("uid") is None:
        return row.get("new")
    domain, unique_id = row["uid"]
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id)


async def async_restore_ids(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> tuple[int, int]:
    """Give the new entities the old entity IDs; (restored, still taken).

    Home Assistant moves the recorded history along with a renamed entity ID unless the
    target ID has history of its own: then the new entity goes on with the old history.
    """
    report = await async_get_report(hass)
    registry = er.async_get(hass)
    restored = blocked = 0
    for device in report.devices(entry.entry_id).values():
        for row in device["entities"]:
            now = current_new(hass, row)
            if now is None or row["restored"]:
                continue
            if now == row["old"]:
                row["restored"] = True
                continue
            if now.split(".")[0] != row["old"].split(".")[0]:
                continue  # another kind of entity now (sensor -> binary_sensor): keeps its ID
            if registry.async_is_registered(row["old"]) or hass.states.get(row["old"]):
                blocked += 1
                continue
            registry.async_update_entity(now, new_entity_id=row["old"])
            row["restored"] = True
            restored += 1
    if restored:
        await report.async_save()
    return restored, blocked
