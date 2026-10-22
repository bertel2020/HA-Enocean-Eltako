"""Websocket API of the panel's takeover view: preview, take over, old -> new entity IDs,
and carrying settings of the old integration over to devices already set up."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_BASE_ID, DOMAIN
from .protocol.ids import format_id, parse_id
from .takeover import (
    CARRY_OPTIONS,
    Carried,
    apply_carried,
    async_old_config,
    async_predicted_ids,
    async_take_over,
    async_takeover_available,
    carried_from,
    find_gateway,
    missing_carried,
    new_entity,
    old_active,
    old_entities,
    plan,
    primary_entity,
    registered_device,
)
from .usage import KINDS, Usage, async_usage

CARRY = [vol.In(CARRY_OPTIONS)]


@callback
def async_setup_takeover_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_takeover_status)
    websocket_api.async_register_command(hass, ws_takeover_preview)
    websocket_api.async_register_command(hass, ws_takeover_run)
    websocket_api.async_register_command(hass, ws_takeover_mapping)
    websocket_api.async_register_command(hass, ws_takeover_carry)


def _loaded_entry(hass: HomeAssistant, entry_id: str) -> Any:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        return None
    return entry


async def _plan(hass: HomeAssistant, entry: Any) -> tuple[list[Any] | None, str | None]:
    """The devices of the old gateway with this entry's base ID, or the error code."""
    if (config := await async_old_config(hass)) is None:
        return None, "no_config"
    try:
        base_id = parse_id(entry.data.get(CONF_BASE_ID, ""))
    except ValueError:
        base_id = -1
    if (gateway := find_gateway(config, base_id)) is None:
        return None, "no_gateway"
    existing = {s.unique_id for s in entry.subentries.values()}
    devices = plan(gateway)
    for device in devices:
        if device.model is not None and format_id(device.target_id) in existing:
            device.model, device.reason = None, "takeover_exists"
    return devices, None


@websocket_api.websocket_command({vol.Required("type"): "enocean_eltako/takeover/status"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_status(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Whether there is anything to take over: the panel shows the view only then."""
    connection.send_result(msg["id"], {"available": await async_takeover_available(hass)})


@websocket_api.websocket_command(
    {vol.Required("type"): "enocean_eltako/takeover/preview", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_preview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The old devices, what each becomes, and what would be carried over."""
    if (entry := _loaded_entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], "gateway_not_loaded", "gateway not loaded")
        return
    devices, error = await _plan(hass, entry)
    if devices is None:
        connection.send_error(msg["id"], error or "no_config", "nothing to take over")
        return
    old = old_entities(hass)
    usage = await async_usage(
        hass, [e.entity_id for d in devices for e in old.get(d.device_id, [])]
    )
    predicted = await async_predicted_ids(hass, entry, devices, old)
    result = []
    for device in devices:
        entries = old.get(device.device_id, [])
        main = primary_entity(entries)
        entries = sorted(entries, key=lambda e: (e is not main, e.entity_id))
        carried = carried_from(hass, entries)
        places = _places([usage[e.entity_id] for e in entries])
        labels = carried.labels.union(*(e.labels for e in entries))
        result.append(
            {
                "id": format_id(device.device_id),
                "name": device.name,
                "old": device.old,
                "ready": device.model is not None,
                "reason": device.reason,
                "area": _area_name(hass, carried.area_id) if carried.area_id else None,
                "labels": sorted(_label_names(hass, labels)),
                "carry": sorted(carried.available()),
                "used": len(places),
                # the confirmation: old -> probable new entity ID (None: known only afterwards)
                "entities": [
                    {"old": e.entity_id, "new": predicted.get(e.entity_id)} for e in entries
                ],
                "places": places,
            }
        )
    connection.send_result(
        msg["id"], {"devices": result, "old_active": old_active(hass), "old_devices": len(old)}
    )


def _places(usages: list[Usage]) -> list[str]:
    """The automations, scripts, scenes and dashboards using any of these entities."""
    return sorted({f"{k}:{p['name']}" for u in usages for k, places in u.items() for p in places})


def _area_name(hass: HomeAssistant, area_id: str) -> str:
    from homeassistant.helpers import area_registry as ar

    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else area_id


def _label_names(hass: HomeAssistant, label_ids: set[str]) -> list[str]:
    from homeassistant.helpers import label_registry as lr

    registry = lr.async_get(hass)
    return [label.name if (label := registry.async_get_label(i)) else i for i in label_ids]


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/takeover/run",
        vol.Required("entry_id"): str,
        vol.Required("devices"): [str],
        vol.Optional("carry", default=[]): CARRY,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_run(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Take the chosen devices over; the gateway reloads once at the end."""
    if (entry := _loaded_entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], "gateway_not_loaded", "gateway not loaded")
        return
    devices, error = await _plan(hass, entry)
    if devices is None:
        connection.send_error(msg["id"], error or "no_config", "nothing to take over")
        return
    chosen = set(msg["devices"])
    ready = [d for d in devices if d.model is not None and format_id(d.device_id) in chosen]
    result = await async_take_over(hass, entry, ready, carry=set(msg["carry"]))
    connection.send_result(
        msg["id"],
        {"count": result.count, "skipped": result.skipped, "carried": result.carried},
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "enocean_eltako/takeover/mapping", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_mapping(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Old entity ID -> new entity ID per device, with where each old ID is still used."""
    if (entry := _loaded_entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], "gateway_not_loaded", "gateway not loaded")
        return
    registry = er.async_get(hass)
    taken: dict[int, list[er.RegistryEntry]] = {}
    for device in entry.runtime_data.devices.values():
        if device.channel != 1:
            continue
        if (registered := registered_device(hass, entry, device)) is None:
            continue
        taken[device.device_id] = er.async_entries_for_device(
            registry, registered.id, include_disabled_entities=True
        )
    titles = {d.device_id: d.subentry.title for d in entry.runtime_data.devices.values()}
    rows: list[dict[str, Any]] = []
    olds: dict[int, Carried] = {}
    for device_id, entries in sorted(old_entities(hass).items()):
        new = taken.get(device_id)
        main = primary_entity(entries)
        carried: Carried = carried_from(hass, entries)
        if new is not None:
            olds[device_id] = carried
        name = titles.get(device_id) or _old_device_name(hass, entries) or format_id(device_id)
        for old in sorted(entries, key=lambda e: (e is not main, e.entity_id)):
            replacement = new_entity(old, main, new) if new is not None else None
            rows.append(
                {
                    "device": name,
                    "id": format_id(device_id),
                    "area": _area_name(hass, carried.area_id) if carried.area_id else None,
                    "taken": new is not None,
                    "old": old.entity_id,
                    "new": replacement.entity_id if replacement is not None else None,
                    "primary": old is main,
                }
            )
    usage = await async_usage(hass, [r["old"] for r in rows])
    for row in rows:
        row["usage"] = usage[row["old"]]
    totals = {kind: len({n for u in usage.values() for n in u[kind]}) for kind in KINDS}
    # per set-up device what the old integration had that it still lacks
    missing = {
        format_id(device_id): sorted(changes)
        for device_id, changes in missing_carried(hass, entry, olds).items()
    }
    connection.send_result(
        msg["id"],
        {"rows": rows, "totals": totals, "missing": missing, "old_active": old_active(hass)},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/takeover/carry",
        vol.Required("entry_id"): str,
        vol.Required("carry"): CARRY,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_carry(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Carry the chosen settings over to the devices already set up; set values stay."""
    if (entry := _loaded_entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], "gateway_not_loaded", "gateway not loaded")
        return
    carried = {i: carried_from(hass, entries) for i, entries in old_entities(hass).items()}
    connection.send_result(
        msg["id"], {"carried": apply_carried(hass, entry, carried, set(msg["carry"]))}
    )


def _old_device_name(hass: HomeAssistant, entries: list[er.RegistryEntry]) -> str | None:
    devices = dr.async_get(hass)
    for entry in entries:
        if entry.device_id and (device := devices.async_get(entry.device_id)) is not None:
            return device.name_by_user or device.name
    return None
