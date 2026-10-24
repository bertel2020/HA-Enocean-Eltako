"""The takeover reports: what each device was in the old integration and its old -> new IDs.

Kept in the integration's own storage, so the mapping stays readable once the old integration
and its "eltako:" section are gone. Each takeover is a run with its own report: when, which
settings came along and a snapshot per device; devices set up by hand that the old integration
had go into one report of their own. A snapshot is refreshed while the old entities exist. A
report can be deleted. The reports also restore old entity IDs on request (the new entity gets
the old ID, so references go on working): only once the old integration's entities are gone.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util.hass_dict import HassKey
from homeassistant.util.ulid import ulid_now

from .const import DOMAIN
from .protocol.ids import format_id
from .takeover import (
    TakeoverDevice,
    carried_from,
    carry_details,
    label_names,
    new_entity,
    new_ids,
    old_entities,
    primary_entity,
    registered_device,
)
from .usage import KINDS, async_usage

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

STORAGE_VERSION = 2
DATA_REPORT: HassKey[TakeoverReport] = HassKey(f"{DOMAIN}_takeover_report")
# how the old entity IDs are dealt with: given back to the new entities, or the places switched
STRATEGIES = ("keep", "new")


def migrate_v1(data: Mapping[str, Any]) -> dict[str, Any]:
    """Version 1 kept one snapshot per device; now each takeover is a report of its own.

    The devices of one gateway taken over on the same day become one report, the ones set up
    by hand (no takeover date) another.
    """
    runs: dict[str, dict[str, Any]] = {}
    slots: dict[tuple[str, str | None], str] = {}
    for entry_id, devices in (data.get("entries") or {}).items():
        for key, old in devices.items():
            at = old.get("taken_at")
            slot = (entry_id, at[:10] if at else None)
            if slot not in slots:
                slots[slot] = ulid_now()
                runs[slots[slot]] = {
                    "entry_id": entry_id,
                    "at": at,
                    "manual": at is None,
                    "carry": [],
                    "devices": {},
                }
            run = runs[slots[slot]]
            snap = {k: v for k, v in old.items() if k not in ("taken_at", "carried")}
            run["carry"] = sorted({*run["carry"], *(old.get("carried") or [])})
            run["devices"][key] = snap
    return {"runs": runs, "strategy": {}}


class _ReportStore(Store[dict[str, Any]]):
    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        return migrate_v1(old_data) if old_major_version < 2 else old_data


class TakeoverReport:
    """{"runs": {run ID: report}, "strategy": {entry ID: "keep" | "new"}} in .storage.

    A report: {"entry_id", "at" (None when set up by hand), "manual", "carry": options,
    "devices": {old device ID: snapshot}}.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._store = _ReportStore(hass, STORAGE_VERSION, f"{DOMAIN}.takeover")
        self.runs: dict[str, dict[str, Any]] = {}
        self.strategy: dict[str, str] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.runs = data.get("runs") or {}
        self.strategy = data.get("strategy") or {}

    async def async_save(self) -> None:
        await self._store.async_save({"runs": self.runs, "strategy": self.strategy})

    def runs_of(self, entry_id: str) -> list[tuple[str, dict[str, Any]]]:
        """The gateway's reports, oldest first (the one set up by hand last)."""
        mine = [(i, r) for i, r in self.runs.items() if r["entry_id"] == entry_id]
        return sorted(mine, key=lambda item: (item[1]["at"] is None, item[1]["at"] or ""))

    def devices(self, entry_id: str) -> dict[str, dict[str, Any]]:
        """The snapshots of one gateway, with when they were taken over and what came along."""
        found: dict[str, dict[str, Any]] = {}
        for run_id, run in self.runs_of(entry_id):
            for key, snap in run["devices"].items():
                found[key] = {**snap, "taken_at": run["at"], "carried": run["carry"], "run": run_id}
        return found

    def holder(self, entry_id: str, key: str) -> dict[str, Any] | None:
        return next((r for _, r in self.runs_of(entry_id) if key in r["devices"]), None)

    @property
    def empty(self) -> bool:
        return not self.runs

    def pending_restore(self, hass: HomeAssistant) -> bool:
        """An entry whose old IDs are to be given back still has entities without theirs."""
        for entry_id, strategy in self.strategy.items():
            if strategy != "keep":
                continue
            for device in self.devices(entry_id).values():
                for row in device["entities"]:
                    now = current_new(hass, row)
                    if _restorable(row, now):
                        return True
        return False


async def async_get_report(hass: HomeAssistant) -> TakeoverReport:
    if (report := hass.data.get(DATA_REPORT)) is None:
        report = TakeoverReport(hass)
        await report.async_load()
        hass.data[DATA_REPORT] = report
    return report


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
    details = carry_details(hass, carried)
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
    labels = carried.labels.union(*(e.labels for e in entries))
    return {
        "name": name,
        "old": {
            "config": planned.old if planned else None,
            "name": planned.name if planned else None,
            "senders": [format_id(s) for s in planned.senders.values()] if planned else [],
            "device_name": (old_device.name_by_user or old_device.name) if old_device else None,
            "area": details["area"],
            "labels": sorted(label_names(hass, labels)),
            "details": details,
        },
        "entities": rows,
    }


def _new_run(
    report: TakeoverReport, entry: EnOceanEltakoConfigEntry, at: str | None, carry: list[str]
) -> dict[str, Any]:
    run: dict[str, Any] = {
        "entry_id": entry.entry_id,
        "at": at,
        "manual": at is None,
        "carry": carry,
        "devices": {},
    }
    report.runs[ulid_now()] = run
    return run


async def async_record(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    planned: list[TakeoverDevice] | None,
    taken: Mapping[int, list[str]] | None = None,
) -> None:
    """Refresh the snapshots of the devices set up here that the old integration still has.

    taken: the devices just taken over, with the options carried over: they get a report of
    their own. Devices set up by hand go into the one report of that kind.
    """
    report = await async_get_report(hass)
    new = set_up_entities(hass, entry)
    by_id: dict[int, TakeoverDevice] = {}
    for planned_device in planned or []:
        by_id.setdefault(planned_device.device_id, planned_device)  # listed twice: the first
    ids = new_ids(planned)
    titles = {d.device_id: d.subentry.title for d in entry.runtime_data.devices.values()}
    old = old_entities(hass)
    # a device just taken over is recorded even when the old integration has nothing left
    wanted = {*old, *(taken or {})}
    run: dict[str, Any] | None = None
    changed = False
    for device_id in sorted(wanted):
        target = ids.get(device_id, device_id)
        if (mine := new.get(target)) is None:
            continue
        key = format_id(device_id)
        entries = old.get(device_id, [])
        fresh = snapshot(hass, entries, mine, titles.get(target, key), by_id.get(device_id))
        holder = report.holder(entry.entry_id, key)
        if holder is not None:
            restored = {r["old"] for r in holder["devices"][key]["entities"] if r["restored"]}
            for row in fresh["entities"]:
                row["restored"] = row["old"] in restored
        if taken is not None and device_id in taken:
            if run is None:
                carry = sorted({o for options in taken.values() for o in options})
                run = _new_run(report, entry, datetime.now(UTC).isoformat(), carry)
            home = run
        elif holder is not None:
            home = holder
        else:
            by_hand = [r for _, r in report.runs_of(entry.entry_id) if r["manual"]]
            home = by_hand[0] if by_hand else _new_run(report, entry, None, [])
        if holder is not None and holder is not home:
            del holder["devices"][key]
            changed = True
        if home["devices"].get(key) != fresh:
            home["devices"][key] = fresh
            changed = True
    if changed:
        await report.async_save()


def current_new(hass: HomeAssistant, row: Mapping[str, Any]) -> str | None:
    """The new entity's ID now: found by its unique ID, so a later rename shows."""
    if row.get("uid") is None:
        return row.get("new")
    domain, unique_id = row["uid"]
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, unique_id)


def _restorable(row: Mapping[str, Any], now: str | None) -> bool:
    """The new entity does not have the old ID yet, and is of the same kind as the old one."""
    if now is None or row["restored"] or now == row["old"]:
        return False
    return bool(now.split(".")[0] == row["old"].split(".")[0])


async def async_restore_ids(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> tuple[int, int, int]:
    """Give the new entities the old entity IDs; (restored, still taken, in use).

    Home Assistant moves the recorded history along with a renamed entity ID unless the
    target ID has history of its own: then the new entity goes on with the old history.
    A new ID that an automation, script, scene or dashboard uses stays: renaming it would
    break that place.
    """
    report = await async_get_report(hass)
    registry = er.async_get(hass)
    restored = blocked = in_use = 0
    candidates: list[tuple[dict[str, Any], str]] = []
    for device in report.devices(entry.entry_id).values():
        for row in device["entities"]:
            now = current_new(hass, row)
            if now is not None and not row["restored"] and now == row["old"]:
                row["restored"] = True
            elif now is not None and _restorable(row, now):
                candidates.append((row, now))
    usage = await async_usage(hass, [now for _, now in candidates])
    for row, now in candidates:
        if any(usage[now][kind] for kind in KINDS):
            in_use += 1
        elif registry.async_is_registered(row["old"]) or hass.states.get(row["old"]):
            blocked += 1
        else:
            registry.async_update_entity(now, new_entity_id=row["old"])
            row["restored"] = True
            restored += 1
    if restored:
        await report.async_save()
    return restored, blocked, in_use
