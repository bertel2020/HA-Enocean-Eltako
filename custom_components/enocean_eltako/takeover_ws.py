"""Websocket API of the panel's takeover view: preview, take over, old -> new entity IDs,
carrying settings of the old integration over to devices already set up, and the reports."""

from __future__ import annotations

from collections.abc import Mapping
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
    area_name,
    async_old_config,
    async_predicted_ids,
    async_take_over,
    carried_from,
    carry_details,
    find_gateway,
    label_names,
    missing_carried,
    new_entity,
    new_ids,
    old_active,
    old_entities,
    plan,
    primary_entity,
)
from .takeover_report import (
    STRATEGIES,
    async_get_report,
    async_record,
    async_restore_ids,
    current_new,
    set_up_entities,
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
    websocket_api.async_register_command(hass, ws_takeover_strategy)
    websocket_api.async_register_command(hass, ws_takeover_restore)
    websocket_api.async_register_command(hass, ws_takeover_reports)
    websocket_api.async_register_command(hass, ws_takeover_report)
    websocket_api.async_register_command(hass, ws_takeover_report_delete)


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
    """Whether there is anything to do: the panel shows the wizard only then; the reports stay."""
    report = await async_get_report(hass)
    config = await async_old_config(hass)
    available = config is not None or bool(old_entities(hass)) or report.pending_restore(hass)
    connection.send_result(msg["id"], {"available": available, "reports": len(report.runs)})


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
        details = carry_details(hass, carried)
        extras = {e["old"]: e for e in details.pop("entities")}
        result.append(
            {
                "id": format_id(device.device_id),
                "name": device.name,
                "old": device.old,
                "ready": device.model is not None,
                "reason": device.reason,
                "area": area_name(hass, carried.area_id) if carried.area_id else None,
                "labels": sorted(label_names(hass, labels)),
                "carry": sorted(carried.available()),
                "used": len(places),
                # the values behind the options: the area and labels of the device itself
                "details": details,
                # the confirmation: old -> probable new entity ID (None: known only afterwards),
                # with what is set on the old entity
                "entities": [
                    {
                        **extras.get(e.entity_id, {}),
                        "old": e.entity_id,
                        "new": predicted.get(e.entity_id),
                    }
                    for e in entries
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
    if entry.state is ConfigEntryState.LOADED:
        taken = {d.device_id: msg["carry"] for d in ready}
        await async_record(hass, entry, devices, taken)
    connection.send_result(
        msg["id"],
        {"count": result.count, "skipped": result.skipped, "carried": result.carried},
    )


def _stored_rows(hass: HomeAssistant, devices: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The rows of the devices in a report: the new entity found by its unique ID."""
    rows = []
    for key, device in sorted(devices.items()):
        for row in device["entities"]:
            rows.append(
                {
                    "device": device["name"],
                    "id": key,
                    "area": device["old"]["area"],
                    "taken": True,
                    "old": row["old"],
                    "new": current_new(hass, row),
                    "primary": row["primary"],
                    "restored": row["restored"],
                }
            )
    return rows


async def _with_usage(hass: HomeAssistant, rows: list[dict[str, Any]]) -> dict[str, int]:
    """Where each old ID is used, set on the rows; the number of places by kind."""
    usage = await async_usage(hass, [r["old"] for r in rows])
    for row in rows:
        row["usage"] = usage[row["old"]]
    return {kind: len({n for u in usage.values() for n in u[kind]}) for kind in KINDS}


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
    planned, _ = await _plan(hass, entry)
    await async_record(hass, entry, planned)
    ids = new_ids(planned)
    taken = set_up_entities(hass, entry)
    report = await async_get_report(hass)
    stored = report.devices(entry.entry_id)
    rows: list[dict[str, Any]] = []
    olds: dict[int, Carried] = {}
    live = old_entities(hass)
    for device_id, entries in sorted(live.items()):
        target = ids.get(device_id, device_id)
        if format_id(device_id) in stored:
            olds[device_id] = carried_from(hass, entries)
            continue  # from the report below
        main = primary_entity(entries)
        carried = carried_from(hass, entries)
        old_device = _old_device_name(hass, entries)
        for old in sorted(entries, key=lambda e: (e is not main, e.entity_id)):
            replacement = new_entity(old, main, taken[target]) if target in taken else None
            rows.append(
                {
                    "device": old_device or format_id(device_id),
                    "id": format_id(device_id),
                    "area": area_name(hass, carried.area_id) if carried.area_id else None,
                    "taken": False,
                    "old": old.entity_id,
                    "new": replacement.entity_id if replacement is not None else None,
                    "primary": old is main,
                    "restored": False,
                }
            )
    rows += _stored_rows(hass, stored)
    totals = await _with_usage(hass, rows)
    # per set-up device what the old integration had that it still lacks, by its old ID
    back = {target: device_id for device_id, target in ids.items()}
    missing = {
        format_id(back.get(target, target)): sorted(changes)
        for target, changes in missing_carried(
            hass, entry, {ids.get(i, i): c for i, c in olds.items()}
        ).items()
    }
    devices = {k: {n: v for n, v in d.items() if n != "entities"} for k, d in stored.items()}
    connection.send_result(
        msg["id"],
        {
            "rows": rows,
            "devices": devices,
            "totals": totals,
            "missing": missing,
            "old_active": old_active(hass),
            "old_entities": bool(live),
            "strategy": report.strategy.get(entry.entry_id),
        },
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
    planned, _ = await _plan(hass, entry)
    ids = new_ids(planned)
    carried = {
        ids.get(i, i): carried_from(hass, entries) for i, entries in old_entities(hass).items()
    }
    connection.send_result(
        msg["id"], {"carried": apply_carried(hass, entry, carried, set(msg["carry"]))}
    )


def _old_device_name(hass: HomeAssistant, entries: list[er.RegistryEntry]) -> str | None:
    devices = dr.async_get(hass)
    for entry in entries:
        if entry.device_id and (device := devices.async_get(entry.device_id)) is not None:
            return device.name_by_user or device.name
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/takeover/strategy",
        vol.Required("entry_id"): str,
        vol.Required("strategy"): vol.In(STRATEGIES),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_strategy(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """How the old entity IDs are dealt with, chosen per gateway: given back, or switched."""
    report = await async_get_report(hass)
    report.strategy[msg["entry_id"]] = msg["strategy"]
    await report.async_save()
    connection.send_result(msg["id"], {})


@websocket_api.websocket_command(
    {vol.Required("type"): "enocean_eltako/takeover/restore", vol.Required("entry_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_restore(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The new entities get the old entity IDs back: only once the old entities are gone."""
    if (entry := _loaded_entry(hass, msg["entry_id"])) is None:
        connection.send_error(msg["id"], "gateway_not_loaded", "gateway not loaded")
        return
    if old_active(hass) or old_entities(hass):
        connection.send_error(msg["id"], "old_present", "the old entities still exist")
        return
    restored, blocked, in_use = await async_restore_ids(hass, entry)
    connection.send_result(msg["id"], {"restored": restored, "blocked": blocked, "in_use": in_use})


def _summary(hass: HomeAssistant, run_id: str, run: Mapping[str, Any]) -> dict[str, Any]:
    gateway = hass.config_entries.async_get_entry(run["entry_id"])
    rows = [row for device in run["devices"].values() for row in device["entities"]]
    return {
        "id": run_id,
        "entry_id": run["entry_id"],
        "gateway": gateway.title if gateway is not None else None,
        "at": run["at"],
        "manual": run["manual"],
        "carry": run["carry"],
        "devices": len(run["devices"]),
        "entities": len(rows),
        "restored": sum(1 for row in rows if row["restored"]),
    }


@websocket_api.websocket_command({vol.Required("type"): "enocean_eltako/takeover/reports"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_reports(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The reports, newest first (the one of devices set up by hand last)."""
    report = await async_get_report(hass)
    runs = sorted(report.runs.items(), key=lambda i: (i[1]["at"] is not None, i[1]["at"] or ""))
    connection.send_result(
        msg["id"], [_summary(hass, run_id, run) for run_id, run in reversed(runs)]
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "enocean_eltako/takeover/report", vol.Required("run_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_report(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """One report: its devices as they were, and the old -> new entity IDs as they are now."""
    report = await async_get_report(hass)
    if (run := report.runs.get(msg["run_id"])) is None:
        connection.send_error(msg["id"], "not_found", "no such report")
        return
    rows = _stored_rows(hass, run["devices"])
    totals = await _with_usage(hass, rows)
    devices = {
        k: {n: v for n, v in d.items() if n != "entities"} for k, d in run["devices"].items()
    }
    connection.send_result(
        msg["id"],
        {**_summary(hass, msg["run_id"], run), "rows": rows, "devices": devices, "totals": totals},
    )


@websocket_api.websocket_command(
    {vol.Required("type"): "enocean_eltako/takeover/report_delete", vol.Required("run_id"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_takeover_report_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete a report: the old -> new mapping of its devices is gone with it."""
    report = await async_get_report(hass)
    if report.runs.pop(msg["run_id"], None) is None:
        connection.send_error(msg["id"], "not_found", "no such report")
        return
    await report.async_save()
    connection.send_result(msg["id"], {})
