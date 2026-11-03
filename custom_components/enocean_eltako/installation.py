"""The installation store: the Eltako bus as the user documents it, one for all gateways.

A bus does not belong to one gateway (a FAM-USB reaches it by radio, an FGW14-USB sits on it), so
its buses, cabinets with their rows and modules with their channels live in a store of their own
(enocean_eltako.installation, version 1), not in the notes of a gateway. What the notes held for
the bus before (notes version 7: bus address, feedback ID and power of a device, power supplies
with address ranges, bus entries by hand) is taken over once per gateway; the notes keep those
fields as a copy that this store writes back, so the older views, the print and the CSV read
the same values, and an edit there is taken over here. Config entry and subentry data stay as
they are: this is documentation, not configuration.
"""

from __future__ import annotations

import asyncio
import copy
from dataclasses import asdict
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util.hass_dict import HassKey

from .bus_devices import BUS_TYPES, is_bus_model
from .const import CONF_BUS_GROUP, CONF_MODEL, DOMAIN
from .installation_checks import run_checks
from .installation_data import (
    BUS_FIELDS,
    absorb,
    apply_device,
    channel_values,
    check_bus,
    check_cabinet,
    check_module,
    empty,
    ensure_master,
    manual_values,
    move_module,
    normalize,
    remove_module,
    supply_values,
    sync_manual,
    sync_supplies,
)
from .notes import SAVE_DELAY, Notes, device_key
from .protocol.models import MODELS

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.installation"
DATA_INSTALLATION: HassKey[Installation] = HassKey(f"{DOMAIN}_installation")
_LOCK: HassKey[asyncio.Lock] = HassKey(f"{DOMAIN}_installation_lock")
# the catalog of the series 14 as the panel gets it
TYPES = {key: {**asdict(found), "assumed": list(found.assumed)} for key, found in BUS_TYPES.items()}


def gateway_of(entry: ConfigEntry) -> dict[str, Any]:
    """What the pure functions need to know of a gateway."""
    model = MODELS.get(entry.data.get(CONF_MODEL, ""))
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "wired": bool(model and model.bus),
        "bus_group": entry.data.get(CONF_BUS_GROUP),
    }


def device_of(device: Any, notes: Notes) -> dict[str, Any]:
    key = device_key(device.subentry)
    fields = notes.device(key)
    return {
        "key": key,
        "name": device.subentry.title,
        "model": device._model_label or "",
        "group": fields["group"],
        "location": fields["location"],
        **{f: fields[f] for f in BUS_FIELDS},
    }


class Installation:
    """The store and every change of it; a change is written back to the notes' copy."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = empty()

    async def async_load(self) -> None:
        self.data = normalize(await self._store.async_load())

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self.data, SAVE_DELAY)

    async def async_flush(self) -> None:
        await self._store.async_save(self.data)

    # ---- the notes of the gateways ------------------------------------------------------------

    def _notes(self, entry_id: str) -> Notes | None:
        """The notes of a loaded gateway whose bus fields were taken over."""
        entry = self._hass.config_entries.async_get_entry(entry_id)
        runtime = getattr(entry, "runtime_data", None) if entry else None
        notes = runtime.hub.notes.get(entry_id) if runtime is not None else None
        return notes if notes is not None and notes.migrated else None

    def _legacy(self, entry: ConfigEntry, notes: Notes) -> dict[str, Any]:
        devices = [
            device_of(d, notes) for d in entry.runtime_data.devices.values() if d.virtual is None
        ]
        return {
            **gateway_of(entry),
            "devices": devices,
            "supplies": notes.supplies,
            "manual": notes.manual,
        }

    def absorb_entry(self, entry: ConfigEntry, notes: Notes) -> int:
        """Take over what a gateway's notes hold for the bus, once (notes version 7 to 8)."""
        if notes.migrated:
            return 0
        added = absorb(self.data, self._legacy(entry, notes))
        notes.set_migrated()
        if added:
            self._save()
        return added

    def reconcile_entry(self, entry: ConfigEntry, notes: Notes) -> int:
        """After an import into the notes: what they hold now is taken over (the same way as
        the first time); how many modules were added."""
        before = copy.deepcopy(self.data)
        count = len(self.data["modules"])
        gateway = self._legacy(entry, notes)
        for device in gateway["devices"]:
            values = {f: device[f] for f in BUS_FIELDS}
            apply_device(self.data, gateway, device, values, create=False)
        sync_supplies(self.data, gateway, notes.supplies)
        sync_manual(self.data, gateway, notes.manual)
        absorb(self.data, gateway, models=False)
        notes.set_migrated()
        self._commit(before, delete_manual=False)
        return max(0, len(self.data["modules"]) - count)

    def legacy_device(self, entry: ConfigEntry, device: Any, values: dict[str, str]) -> None:
        """Bus fields of a device written in an older view: its channel follows."""
        notes = self._notes(entry.entry_id)
        values = {f: v for f, v in values.items() if f in BUS_FIELDS}
        if notes is None or not values:
            return
        before = copy.deepcopy(self.data)
        if apply_device(self.data, gateway_of(entry), device_of(device, notes), values):
            self._commit(before, delete_manual=False)

    def legacy_supplies(self, entry: ConfigEntry) -> None:
        """The power supplies as the older bus view writes them: their modules follow."""
        if (notes := self._notes(entry.entry_id)) is None:
            return
        if sync_supplies(self.data, gateway_of(entry), notes.supplies):
            self._save()

    def legacy_manual(self, entry: ConfigEntry) -> None:
        """Entries by hand as the older views write them: one with a bus address is a channel."""
        if (notes := self._notes(entry.entry_id)) is None:
            return
        if sync_manual(self.data, gateway_of(entry), notes.manual):
            self._save()

    def _commit(self, before: dict[str, Any], *, delete_manual: bool = True) -> None:
        """Save, and write what changed back to the notes' copy (only real changes)."""
        self._mirror(before, delete_manual=delete_manual)
        self._save()

    def _mirror(self, before: dict[str, Any], *, delete_manual: bool) -> None:
        blank = dict.fromkeys(BUS_FIELDS, "")
        old, new = channel_values(before), channel_values(self.data)
        for entry_id, key in old.keys() | new.keys():
            want = new.get((entry_id, key), blank)
            if old.get((entry_id, key)) == want or (notes := self._notes(entry_id)) is None:
                continue
            have = notes.device(key)
            if changed := {f: want[f] for f in BUS_FIELDS if have[f] != want[f]}:
                notes.set_fields(key, changed)
        old_manual, new_manual = manual_values(before), manual_values(self.data)
        for entry_id in {e for e, _ in old_manual.keys() | new_manual.keys()}:
            if (notes := self._notes(entry_id)) is None:
                continue
            entries, dirty = [], False
            for item in notes.manual:
                ref = (entry_id, item["id"])
                if ref in new_manual:
                    merged = {**item, **new_manual[ref]}
                    dirty |= merged != item
                    entries.append(merged)
                elif ref in old_manual and delete_manual:
                    dirty = True  # its module was removed: the entry goes with it
                else:
                    entries.append(item)
            if dirty:
                notes.set_manual(entries)
        old_supply, new_supply = supply_values(before), supply_values(self.data)
        for entry_id in {e for e, _ in old_supply.keys() | new_supply.keys()}:
            if (notes := self._notes(entry_id)) is None:
                continue
            supplies, dirty = [], False
            for item in notes.supplies:
                ref = (entry_id, item["id"])
                if ref in new_supply:
                    merged = {**item, **new_supply[ref]}
                    dirty |= merged != item
                    supplies.append(merged)
                elif ref in old_supply:
                    dirty = True
                else:
                    supplies.append(item)
            if dirty:
                notes.set_supplies(supplies)

    # ---- edits from the panel -----------------------------------------------------------------

    def set_module(self, raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        module, reason = check_module(self.data, raw)
        if module is None:
            return None, reason
        before = copy.deepcopy(self.data)
        old = next((m for m in self.data["modules"] if m["id"] == module["id"]), None)
        if old is not None:
            # what the panel does not edit stays: where it came from in the notes
            module |= {k: old[k] for k in ("origin", "supply_id", "placeholder")}
            if module["type"] != old["type"] or module["row"]:
                module["placeholder"] = False
            self.data["modules"][self.data["modules"].index(old)] = module
        else:
            self.data["modules"].append(module)
        self._commit(before)
        return module, ""

    def move_module(self, module_id: str, direction: int) -> str:
        """Arrange on the rail (swap with the neighbour, or half a TE at the end of the row)."""
        before = copy.deepcopy(self.data)
        if reason := move_module(self.data, module_id, direction):
            return reason
        self._commit(before)
        return ""

    def remove_module(self, module_id: str) -> bool:
        before = copy.deepcopy(self.data)
        if remove_module(self.data, module_id) is None:
            return False
        self._commit(before)
        return True

    def set_cabinet(self, raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        cabinet, reason = check_cabinet(self.data, raw)
        if cabinet is None:
            return None, reason
        before = copy.deepcopy(self.data)
        old = next((c for c in self.data["cabinets"] if c["id"] == cabinet["id"]), None)
        if old is not None:
            kept = {r["id"] for r in cabinet["rows"]}
            for module in self.data["modules"]:
                if module["row"] in {r["id"] for r in old["rows"]} - kept:
                    module["row"], module["slot"] = None, None
            self.data["cabinets"][self.data["cabinets"].index(old)] = cabinet
        else:
            self.data["cabinets"].append(cabinet)
        self._commit(before)
        return cabinet, ""

    def remove_cabinet(self, cabinet_id: str) -> bool:
        old = next((c for c in self.data["cabinets"] if c["id"] == cabinet_id), None)
        if old is None:
            return False
        before = copy.deepcopy(self.data)
        rows = {r["id"] for r in old["rows"]}
        for module in self.data["modules"]:
            if module["row"] in rows:
                module["row"], module["slot"] = None, None
        self.data["cabinets"].remove(old)
        self._commit(before)
        return True

    def set_bus(self, raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        bus, reason = check_bus(self.data, raw)
        if bus is None:
            return None, reason
        old = next((b for b in self.data["buses"] if b["id"] == bus["id"]), None)
        if old is not None:
            self.data["buses"][self.data["buses"].index(old)] = bus
        else:
            self.data["buses"].append(bus)
            ensure_master(self.data, bus)
        self._save()
        return bus, ""

    def remove_bus(self, bus_id: str) -> str:
        """Remove an empty bus (its placeholder master goes with it); "" or the reason not."""
        bus = next((b for b in self.data["buses"] if b["id"] == bus_id), None)
        if bus is None:
            return "not_found"
        mine = [m for m in self.data["modules"] if m["bus"] == bus_id]
        if any(not m["placeholder"] for m in mine):
            return "not_empty"
        self.data["modules"] = [m for m in self.data["modules"] if m["bus"] != bus_id]
        self.data["buses"].remove(bus)
        self._save()
        return ""

    def remove_entry(self, entry_id: str) -> None:
        """A gateway was deleted: it no longer reaches a bus (its channels stay documented)."""
        changed = False
        for bus in self.data["buses"]:
            access = [a for a in bus["access"] if a["entry_id"] != entry_id]
            changed |= access != bus["access"]
            bus["access"] = access
        if changed:
            self._save()

    def import_block(self, block: Any, entry_map: dict[str, str], *, overwrite: bool) -> int:
        """The installation of an export (version 3): taken when overwriting or when nothing is
        documented here yet; gateways of the file are mapped to the ones set up here. How many
        modules were taken."""
        mapped = normalize(block)
        real = [m for m in self.data["modules"] if not m["placeholder"]]
        if not mapped["modules"] or (real and not overwrite):
            return 0

        def map_id(entry_id: str | None) -> str | None:
            return entry_map.get(entry_id or "", entry_id)

        for bus in mapped["buses"]:
            for item in bus["access"]:
                item["entry_id"] = map_id(item["entry_id"])
        for module in mapped["modules"]:
            module["origin"] = map_id(module["origin"])
            for channel in module["channels"]:
                channel["entry_id"] = map_id(channel["entry_id"])
        before = copy.deepcopy(self.data)
        self.data = mapped
        self._commit(before, delete_manual=False)
        return len(mapped["modules"])

    # ---- what the panel shows -----------------------------------------------------------------

    def ha_devices(self) -> tuple[dict[tuple[str, str], dict[str, Any]], set[str]]:
        """The devices of the loaded gateways for the checks, and those gateways."""
        devices: dict[tuple[str, str], dict[str, Any]] = {}
        loaded = set()
        for entry in self._hass.config_entries.async_loaded_entries(DOMAIN):
            loaded.add(entry.entry_id)
            for device in entry.runtime_data.devices.values():
                if device.virtual is not None:
                    continue
                model = device._model_label or ""
                devices[(entry.entry_id, device_key(device.subentry))] = {
                    "name": device.subentry.title,
                    "model": model,
                    "bus": is_bus_model(model),
                }
        return devices, loaded

    def checks(self) -> dict[str, Any]:
        devices, loaded = self.ha_devices()
        return run_checks(self.data, devices, loaded)

    def payload(self) -> dict[str, Any]:
        """The store, its checks and the catalog: what the panel's bus view is drawn from."""
        return {"installation": self.data, "checks": self.checks(), "types": TYPES}


async def async_get_installation(hass: HomeAssistant) -> Installation:
    """The one installation store, loaded on first use."""
    lock = hass.data.setdefault(_LOCK, asyncio.Lock())
    async with lock:
        if (installation := hass.data.get(DATA_INSTALLATION)) is None:
            installation = Installation(hass)
            await installation.async_load()
            hass.data[DATA_INSTALLATION] = installation
    return installation


def get_installation(hass: HomeAssistant) -> Installation | None:
    """The installation store if it is loaded (it is once a gateway was set up)."""
    return hass.data.get(DATA_INSTALLATION)
