"""Websocket API of the telegram monitor (E4) and its panel.

Each telegram is sent with what Home Assistant knows about it: the gateway's name, the
device it comes from (or, for sent telegrams, the device and sender profile of the sender
ID), the decoded values, and the EEP of a 4BS teach-in from an unknown sender, or the profiles
that fit its telegram.
"""

from __future__ import annotations

import time
from typing import Any

import probatio as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util.hass_dict import HassKey

from .catalog import CATALOG, GENERIC_EEP
from .const import (
    CONF_BASE_ID,
    CONF_BUS_GROUP,
    CONF_MODEL,
    CONF_MODEL_NAME,
    CONF_PROXY_REPLAY,
    DOMAIN,
)
from .device import UTE_WINDOW
from .hub import async_get_hub
from .protocol.dispatcher import ReceivedTelegram
from .protocol.eep import EEPRef
from .protocol.eep.codecs import decode_telegram
from .protocol.eep.teach_in import decode_teach_in_4bs
from .protocol.ids import format_id, parse_id
from .protocol.models import MODELS
from .protocol.monitor import MonitorEntry
from .protocol.send_queue import Priority
from .protocol.sender_pool import SenderState
from .protocol.telegram import RadioTelegram, Rorg
from .subentry_flow import candidates
from .takeover_ws import async_setup_takeover_websocket

MAX_CANDIDATES = 4
# telegram types the panel may send, with the data lengths in bytes
SEND_LENGTHS = {Rorg.RPS: (1,), Rorg.BS1: (1,), Rorg.BS4: (4,), Rorg.VLD: tuple(range(1, 15))}


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe_telegrams)
    websocket_api.async_register_command(hass, ws_gateways)
    websocket_api.async_register_command(hass, ws_discover)
    websocket_api.async_register_command(hass, ws_send)
    websocket_api.async_register_command(hass, ws_teach_in)
    websocket_api.async_register_command(hass, ws_device_details)
    websocket_api.async_register_command(hass, ws_set_model)
    websocket_api.async_register_command(hass, ws_remove_devices)
    websocket_api.async_register_command(hass, ws_sender_pools)
    websocket_api.async_register_command(hass, ws_free_sender)
    async_setup_takeover_websocket(hass)


LABELS: HassKey[dict[str, dict[str, str]]] = HassKey(f"{DOMAIN}_monitor_labels")


async def async_load_labels(hass: HomeAssistant) -> dict[str, str]:
    """Entity names in the server language: ours, and HA's device class names."""
    cache = hass.data.setdefault(LABELS, {})
    language = hass.config.language
    if language not in cache:
        own = await async_get_translations(hass, language, "entity", [DOMAIN])
        classes = await async_get_translations(
            hass, language, "entity_component", ["sensor", "binary_sensor"]
        )
        cache[language] = {**classes, **own}
    return cache[language]


def readable_fields(
    device: Any, values: dict[str, Any], labels: dict[str, str]
) -> list[dict[str, Any]]:
    """Decoded values as the device's entities show them: name, value, unit.

    Uses the platforms' entity descriptions, so "MR 15, DT 1, DIV 0" reads "Power 15 W".
    Kinds without sensors (switches, rockers, covers) keep their raw keys, minus LRN bits.
    """
    from .binary_sensor import model_binary_descriptions  # noqa: PLC0415 - platforms import this
    from .sensor import generic_descriptions, model_descriptions  # noqa: PLC0415

    model = device.model
    sensors = model_descriptions(device)
    if model.kind == GENERIC_EEP and model.receive is not None:  # every field, chosen or not
        sensors = generic_descriptions(model.receive.eep)
    fields: list[dict[str, Any]] = []
    for platform, descriptions in (
        ("sensor", sensors),
        ("binary_sensor", model_binary_descriptions(device)),
    ):
        for description in descriptions:
            if description.entity_registry_enabled_default is False:
                continue
            try:
                value = description.value_fn(values)
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            if value is None:
                continue
            key = description.translation_key
            device_class = description.device_class
            prefix = (
                f"component.{DOMAIN}.entity.{platform}.{key}"
                if key
                else f"component.{platform}.entity_component.{device_class}"
            )
            name = description.name if isinstance(description.name, str) else None
            label = labels.get(f"{prefix}.name") or name or description.key
            if isinstance(value, bool):
                value = labels.get(f"{prefix}.state.{'on' if value else 'off'}", value)
            elif isinstance(value, str):
                value = labels.get(f"{prefix}.state.{value}", value)
            unit = getattr(description, "native_unit_of_measurement", None)
            fields.append({"label": label, "value": _json_value(value), "unit": unit})
    if fields:
        return fields
    return [
        {"label": k, "value": _json_value(v), "unit": None}
        for k, v in values.items()
        if not k.upper().startswith("LRN")
    ]


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _catalog_refs() -> list[EEPRef]:
    refs: dict[EEPRef, None] = {}
    for model in CATALOG.values():
        for ref in (model.receive, *model.receive_extra):
            if ref is not None:
                refs[ref] = None
    return list(refs)


def candidate_eeps(telegram: RadioTelegram) -> list[str]:
    """Profiles of the catalog that decode this telegram: a hint for an unknown sender.

    Only profiles a device can be added with. A telegram that fits many of them (any 4BS
    data telegram fits about a dozen) says nothing about the sender, so there is no hint
    then; short VLD telegrams and 1BS contacts are narrow enough.
    """
    found = [str(ref) for ref in _catalog_refs() if decode_telegram(ref, telegram)]
    return found if len(found) <= MAX_CANDIDATES else []


@callback
def describe(hass: HomeAssistant, entry: MonitorEntry) -> dict[str, Any]:
    """The monitor line plus gateway name, device, profile, decoded values, teach-in EEP."""
    data = entry.as_dict()
    gateway = hass.config_entries.async_get_entry(entry.gateway)
    data["gateway_name"] = gateway.title if gateway is not None else entry.gateway
    telegram = entry.telegram
    for config_entry in hass.config_entries.async_loaded_entries(DOMAIN):
        for device in config_entry.runtime_data.devices.values():
            if entry.direction == "tx":
                profile = next((p for p, s in device.senders.items() if s == telegram.sender), None)
                if profile is not None:
                    data["device"] = device.subentry.title
                    # names need not be unique: the panel pairs command and answer by this key
                    data["device_key"] = device.subentry.subentry_id
                    data["ha_device"] = ha_device_id(device)
                    data["profile"] = profile
                    return data
            elif device.device_id == telegram.sender:
                data["device"] = device.subentry.title
                data["device_key"] = device.subentry.subentry_id
                data["ha_device"] = ha_device_id(device)
                if label := device._model_label:
                    data["model"] = label
                elif device.model.example_list:
                    data["models"] = list(device.model.example_list)  # which of these is unknown
                for ref in (device.model.receive, *device.model.receive_extra):
                    if ref is not None and (values := decode_telegram(ref, telegram)):
                        data["eep"] = str(ref)
                        data["values"] = {k: _json_value(v) for k, v in values.items()}
                        data["fields"] = readable_fields(
                            device, values, hass.data.get(LABELS, {}).get(hass.config.language, {})
                        )
                        break
                return data
    if telegram.rorg == Rorg.BS4 and (teach_in := decode_teach_in_4bs(telegram.data)):
        data["teach_in"] = teach_in.eep
    elif entry.direction == "rx" and (candidates := candidate_eeps(telegram)):
        data["candidates"] = candidates
    return data


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/telegrams/subscribe",
        vol.Optional("entry_id"): str,
        vol.Optional("history", default=0): vol.All(int, vol.Range(min=0, max=500)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_subscribe_telegrams(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Stream telegrams live; with history > 0 the last N buffered ones first.

    Buffered ones carry "history": true, so the panel can skip what it already shows when
    the frontend subscribes again (websocket reconnect, panel reattached).
    """
    await async_load_labels(hass)
    monitor = async_get_hub(hass).monitor
    entry_id = msg.get("entry_id")

    @callback
    def forward(entry: MonitorEntry, history: bool = False) -> None:
        if entry_id is None or entry.gateway == entry_id:
            data = describe(hass, entry)
            if history:
                data["history"] = True
            connection.send_message(websocket_api.event_message(msg["id"], data))

    connection.subscriptions[msg["id"]] = monitor.subscribe(forward)
    connection.send_result(msg["id"])
    if msg["history"]:
        for entry in monitor.history(entry_id, msg["history"]):
            forward(entry, history=True)


@websocket_api.websocket_command({vol.Required("type"): "enocean_eltako/gateways"})
@websocket_api.require_admin
@callback
def ws_gateways(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The gateway entries with their state: the panel's overview and filter."""
    entries = hass.config_entries.async_entries(DOMAIN, include_ignore=False)
    connection.send_result(msg["id"], [gateway_status(e) for e in entries])


def own_senders(runtime: Any) -> list[dict[str, str]]:
    """The gateway's sender IDs that a device uses: what the panel may send from."""
    pool = runtime.senders.pool
    return [
        {"id": format_id(sender_id), "device": device.subentry.title, "profile": profile}
        for device in runtime.devices.values()
        for profile, sender_id in device.senders.items()
        if sender_id in pool
        and getattr(pool.get(sender_id), "state", SenderState.ASSIGNED) is SenderState.ASSIGNED
    ]


def ha_device_id(device: Any) -> str | None:
    """The device's entry in Home Assistant's device registry: the panel links to its page."""
    entry = dr.async_get(device.hass).async_get_device_by_identifier(
        (DOMAIN, device.unique_prefix), device.entry.entry_id
    )
    return entry.id if entry else None


def radio_devices(runtime: Any) -> list[dict[str, Any]]:
    """The gateway's devices that send by radio or bus: the panel's list of set-up devices."""
    rows = []
    for device in runtime.devices.values():
        if device.virtual is not None:  # I9: a virtual sensor has no telegrams of its own
            continue
        hass = device.hass
        entry = dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, device.unique_prefix), device.entry.entry_id
        )
        area = ar.async_get(hass).async_get_area(entry.area_id) if entry and entry.area_id else None
        rows.append(
            {
                "id": format_id(device.device_id),
                "device": device.subentry.title,
                "last_seen": device.stats.last_seen,
                "silent": device.silent,
                "eep": str(device.model.receive) if device.model.receive else None,
                "model": device._model_label,
                "models": [] if device._model_label else list(device.model.example_list),
                "category": device.model.category,
                "area": area.name if area else None,
                "entities": (
                    len(er.async_entries_for_device(er.async_get(hass), entry.id)) if entry else 0
                ),
                "ha_device": entry.id if entry else None,
                "labels": sorted(entry.labels) if entry else [],
                "disabled": bool(entry and entry.disabled),
                # the panel's "teach in": the device's sender IDs; a UTE profile waits for the query
                "key": device.subentry.subentry_id,
                "teach": [
                    {
                        "profile": profile,
                        "id": format_id(sender),
                        "ute": not device.model.sender_profile(profile).teach_in,
                    }
                    for profile, sender in device.senders.items()
                ],
            }
        )
    return rows


def gateway_status(entry: ConfigEntry) -> dict[str, Any]:
    model = MODELS.get(entry.data.get(CONF_MODEL, ""))
    status: dict[str, Any] = {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "model": model.name if model else None,
        "base_id": entry.data.get(CONF_BASE_ID),
        "loaded": entry.state is ConfigEntryState.LOADED,
        # the server's clock: the panel measures "x s ago" against it, not the browser's
        "server_time": time.time(),
    }
    runtime = getattr(entry, "runtime_data", None)
    if status["loaded"] and runtime is not None:
        gateway = runtime.gateway
        status |= {
            "connected": gateway.connected,
            "on_demand": runtime.on_demand,
            "connection": str(gateway.connection),
            "telegrams": gateway.telegrams_received,
            "per_minute": runtime.hub.monitor.received_since(entry.entry_id, time.time() - 60),
            "last_telegram": gateway.last_telegram,
            "queue": len(runtime.queue),
            "unconfirmed": runtime.queue.stats.unconfirmed + runtime.queue.stats.failed,
            "devices": len(runtime.devices),
            "free_senders": runtime.senders.pool.free_count(),
            "senders": own_senders(runtime),
            "radio_devices": radio_devices(runtime),
            # senders hidden from discovery: the panel does not offer them as new devices
            "hidden": sorted(format_id(s) for s in runtime.hub.hidden.get(entry.entry_id, ())),
            "disconnected_since": runtime.disconnected_since,
            "proxy": runtime.proxy,
            "via_proxy": bool(entry.options.get(CONF_PROXY_REPLAY)),
        }
    return status


@websocket_api.websocket_command(
    {vol.Required("type"): "enocean_eltako/discover", vol.Required("sender"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_discover(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Panel "add as device": offer a sender from the monitor under "Add device".

    Uses the sender's last received telegram; works also with discovery switched off. The
    result names the gateway (the panel opens its integration page), or why it cannot be added.
    """
    try:
        sender = parse_id(msg["sender"])
    except ValueError:
        connection.send_error(msg["id"], "invalid_id", "invalid sender ID")
        return
    hub = async_get_hub(hass)
    last = next(
        (
            e
            for e in reversed(hub.monitor.history())
            if e.direction == "rx" and e.telegram.sender == sender
        ),
        None,
    )
    if last is None:
        connection.send_error(msg["id"], "not_found", "no telegram from this sender")
        return
    entry = hass.config_entries.async_get_entry(last.gateway)
    if entry is None or getattr(entry, "runtime_data", None) is None:
        connection.send_result(msg["id"], {"reason": "gateway_not_loaded"})
        return
    if any(s.unique_id == format_id(sender) for s in entry.subentries.values()):
        connection.send_result(msg["id"], {"reason": "already_configured"})
        return
    data = last.telegram.data
    teach_in = decode_teach_in_4bs(data) if last.telegram.rorg == Rorg.BS4 else None
    if not candidates(last.telegram.rorg, teach_in, data):
        connection.send_result(msg["id"], {"reason": "no_matching_kind"})
        return
    hub.discovered[sender] = ReceivedTelegram(last.telegram, last.gateway, last.timestamp, sender)
    connection.send_result(msg["id"], {"entry_id": entry.entry_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/send",
        vol.Required("entry_id"): str,
        vol.Required("sender"): str,
        vol.Required("rorg"): vol.In([f"{r:02X}" for r in SEND_LENGTHS]),
        vol.Required("data"): str,
        vol.Optional("status", default="00"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_send(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Panel "send telegram": a raw telegram through the send queue, to try out an actuator.

    Only from a sender ID a device of this gateway already uses (never an arbitrary ID), at
    user priority; it shows up in the monitor like any sent telegram.
    """
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "gateway not loaded")
        return
    runtime = entry.runtime_data
    try:
        sender = parse_id(msg["sender"])
        data = bytes.fromhex(msg["data"].replace(" ", ""))
        status = bytes.fromhex(msg["status"].replace(" ", ""))
    except ValueError:
        connection.send_error(msg["id"], "invalid_format", "invalid ID or hex data")
        return
    rorg = Rorg(int(msg["rorg"], 16))
    if len(data) not in SEND_LENGTHS[rorg] or len(status) != 1:
        connection.send_error(msg["id"], "invalid_length", "wrong data length for this type")
        return
    if format_id(sender) not in {s["id"] for s in own_senders(runtime)}:
        connection.send_error(msg["id"], "invalid_sender", "not a sender ID of a device")
        return
    result = await runtime.queue.submit(RadioTelegram(rorg, data, sender, status[0]), Priority.USER)
    connection.send_result(msg["id"], {"result": result.value})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/teach_in",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
        vol.Required("profile"): str,
    }
)
@websocket_api.require_admin
@callback
def ws_teach_in(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Panel "teach in": what the device's teach-in button sends, for one of its sender IDs.

    A UTE profile (VLD actuators) sends nothing yet: it answers the actuator's query within the
    window, which the result names.
    """
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "gateway not loaded")
        return
    device = entry.runtime_data.devices.get(msg["device"])
    if device is None or msg["profile"] not in device.senders:
        connection.send_error(msg["id"], "unknown_sender", "no such device or sender profile")
        return
    device.teach_in(msg["profile"])
    ute = not device.model.sender_profile(msg["profile"]).teach_in
    connection.send_result(msg["id"], {"ute": ute, "window": UTE_WINDOW if ute else 0})


# subentry data that is the device's identity or kept elsewhere, not a setting to show
NOT_SETTINGS = ("schema", "model", "device_id", "senders", "eep", "custom", CONF_MODEL_NAME)


def device_details(device: Any) -> dict[str, Any]:
    """Everything known of a set-up device, for the panel's opened row in the devices view."""
    hass, stats, model = device.hass, device.stats, device.model
    entry = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, device.unique_prefix), device.entry.entry_id
    )
    registry = er.async_get(hass)
    entities = []
    for ent in er.async_entries_for_device(registry, entry.id) if entry else ():
        state = hass.states.get(ent.entity_id)
        entities.append(
            {
                "name": ent.name or ent.original_name or ent.entity_id,
                "entity_id": ent.entity_id,
                "state": state.state if state else None,
                "unit": state.attributes.get("unit_of_measurement") if state else None,
            }
        )
    entities.sort(key=lambda e: str(e["name"]).casefold())
    commands = None
    if model.actuator:
        latencies = list(stats.latencies)
        commands = {
            "sent": stats.commands,
            "confirmed": stats.confirmed,
            "rate": stats.success_rate,
            "latency_avg": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "latency_max": round(max(latencies), 1) if latencies else None,
        }
    gateway = device.entry
    return {
        "key": device.subentry.subentry_id,
        "entry_id": gateway.entry_id,
        "gateway_name": gateway.title,
        "model": device._model_label,
        "model_name": str(device.options.get(CONF_MODEL_NAME) or ""),
        "models": list(model.models),
        "eep": str(model.receive) if model.receive else None,
        "eep_extra": [str(ref) for ref in model.receive_extra],
        "category": model.category,
        "signal": {"rssi": stats.rssi, "min": stats.rssi_min, "max": stats.rssi_max},
        "repeat": stats.repeat_count,
        "telegrams": stats.telegrams,
        "interval": model.interval,
        "silent": device.silent,
        "senders": [
            {
                "profile": profile,
                "id": format_id(sender),
                "ute": not model.sender_profile(profile).teach_in,
            }
            for profile, sender in device.senders.items()
        ],
        "commands": commands,
        "settings": {
            k: v
            for k, v in device.subentry.data.items()
            if k not in NOT_SETTINGS and isinstance(v, str | int | float | bool)
        },
        "entities": entities,
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/device_details",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
    }
)
@websocket_api.require_admin
@callback
def ws_device_details(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Panel devices view: what is known of one set-up device (an opened row)."""
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "gateway not loaded")
        return
    device = entry.runtime_data.devices.get(msg["device"])
    if device is None:
        connection.send_error(msg["id"], "unknown_device", "no such device")
        return
    connection.send_result(msg["id"], device_details(device))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/set_model",
        vol.Required("entry_id"): str,
        vol.Required("device"): str,
        vol.Required("model_name"): vol.All(str, vol.Length(max=64)),
    }
)
@websocket_api.require_admin
@callback
def ws_set_model(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Panel devices view: the model of a set-up device (display only); empty clears it.

    Changing the device data reloads the gateway's entry, like any change of a device.
    """
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "gateway not loaded")
        return
    device = entry.runtime_data.devices.get(msg["device"])
    if device is None:
        connection.send_error(msg["id"], "unknown_device", "no such device")
        return
    if not device.model.models:
        connection.send_error(msg["id"], "no_models", "the kind of this device has no models")
        return
    data = dict(device.subentry.data)
    if model_name := msg["model_name"].strip():
        data[CONF_MODEL_NAME] = model_name
    else:
        data.pop(CONF_MODEL_NAME, None)
    if data != dict(device.subentry.data):
        hass.config_entries.async_update_subentry(entry, device.subentry, data=data)
    connection.send_result(msg["id"], {"model_name": data.get(CONF_MODEL_NAME, "")})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/remove_devices",
        vol.Required("entry_id"): str,
        vol.Required("devices"): vol.All([str], vol.Length(min=1)),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_remove_devices(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Panel devices view: remove set-up devices from Home Assistant, one reload for all of them.

    The sender IDs of a removed device stay blocked until the teach-out is confirmed (the
    entry's setup releases them), so nothing is handed out again that an actuator still knows.
    """
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "gateway not loaded")
        return
    keys = list(dict.fromkeys(msg["devices"]))
    if unknown := [key for key in keys if key not in entry.subentries]:
        connection.send_error(msg["id"], "unknown_device", f"no such device: {unknown[0]}")
        return
    runtime = entry.runtime_data
    runtime.suspend_reload()
    try:
        for key in keys:
            hass.config_entries.async_remove_subentry(entry, key)
    finally:
        await hass.config_entries.async_reload(entry.entry_id)
    connection.send_result(msg["id"], {"removed": len(keys)})


def _pools(hass: HomeAssistant) -> dict[str, tuple[str, ConfigEntry, Any]]:
    """The sender pools of the loaded gateways by panel ID: radio per gateway, one per bus group."""
    pools: dict[str, tuple[str, ConfigEntry, Any]] = {}
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        runtime = entry.runtime_data
        pools[f"radio:{entry.entry_id}"] = ("radio", entry, runtime.senders)
        if runtime.bus is not None:
            # the members of a bus group share one pool: listed once, under the first member
            bus_id = f"bus:{entry.data[CONF_BUS_GROUP]}"
            pools.setdefault(bus_id, ("bus", entry, runtime.bus.senders))
    return pools


def _pool_rows(hass: HomeAssistant, store: Any) -> list[dict[str, Any]]:
    titles = {
        s.unique_id: s.title
        for e in hass.config_entries.async_entries(DOMAIN, include_ignore=False)
        for s in e.subentries.values()
    }
    rows = []
    for sender, allocation in store.pool.allocations():
        _kind, _sep, rest = allocation.owner.partition(":")
        device, _sep, profile = rest.rpartition(":")
        rows.append(
            {
                "id": format_id(sender),
                "decimal": sender,
                "device": titles.get(device),  # None: the device was deleted, the ID is blocked
                "ref": device,
                "profile": profile,
                "state": allocation.state.value,
            }
        )
    return rows


@websocket_api.websocket_command({vol.Required("type"): "enocean_eltako/sender_pools"})
@websocket_api.require_admin
@callback
def ws_sender_pools(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Who uses which sender ID, per pool: the panel's sender ID table."""
    result = []
    for pool_id, (kind, entry, store) in _pools(hass).items():
        pool = store.pool
        result.append(
            {
                "id": pool_id,
                "kind": kind,
                "title": entry.title,
                "start": format_id(pool.start),
                "end": format_id(pool.start + pool.size - 1),
                "size": pool.size,
                "first": pool.start,
                "free": pool.free_count(),
                "next_free": format_id(nxt) if (nxt := pool.next_free()) is not None else None,
                # in the range but unusable without an allocation of ours (device IDs, bus aliases)
                "unavailable": [
                    s
                    for s in range(pool.start, pool.start + pool.size)
                    if pool.get(s) is None and not pool.is_free(s)
                ],
                "rows": _pool_rows(hass, store),
            }
        )
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/sender_pools/free",
        vol.Required("pool"): str,
        vol.Required("sender"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_free_sender(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Free a blocked sender ID once the actuator has forgotten it (teach-out done)."""
    found = _pools(hass).get(msg["pool"])
    if found is None:
        connection.send_error(msg["id"], "not_found", "pool not found")
        return
    store = found[2]
    try:
        sender = parse_id(msg["sender"])
    except ValueError:
        connection.send_error(msg["id"], "invalid_id", "invalid sender ID")
        return
    allocation = store.pool.get(sender)
    if allocation is None or allocation.state is not SenderState.BLOCKED:
        connection.send_error(msg["id"], "not_blocked", "only a blocked sender ID can be freed")
        return
    store.pool.confirm_teach_out(sender)
    await store.async_save()
    connection.send_result(msg["id"])
