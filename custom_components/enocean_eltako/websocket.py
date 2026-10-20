"""Websocket API of the telegram monitor (E4) and its panel.

Each telegram is sent with what Home Assistant knows about it: the gateway's name, the
device it comes from (or, for sent telegrams, the device and sender profile of the sender
ID), the decoded values, and the EEP of a 4BS teach-in from an unknown sender.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import (
    SOURCE_INTEGRATION_DISCOVERY,
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResultType

from .const import CONF_BASE_ID, CONF_MODEL, DOMAIN
from .discovery import discovery_data
from .hub import async_get_hub
from .protocol.eep.codecs import decode_telegram
from .protocol.eep.teach_in import decode_teach_in_4bs
from .protocol.ids import parse_id
from .protocol.models import MODELS
from .protocol.monitor import MonitorEntry
from .protocol.telegram import Rorg


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe_telegrams)
    websocket_api.async_register_command(hass, ws_gateways)
    websocket_api.async_register_command(hass, ws_discover)


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


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
                    data["profile"] = profile
                    return data
            elif device.device_id == telegram.sender:
                data["device"] = device.subentry.title
                for ref in (device.model.receive, *device.model.receive_extra):
                    if ref is not None and (values := decode_telegram(ref, telegram)):
                        data["values"] = {k: _json_value(v) for k, v in values.items()}
                        break
                return data
    if telegram.rorg == Rorg.BS4 and (teach_in := decode_teach_in_4bs(telegram.data)):
        data["teach_in"] = teach_in.eep
    return data


@websocket_api.websocket_command(
    {
        vol.Required("type"): "enocean_eltako/telegrams/subscribe",
        vol.Optional("entry_id"): str,
        vol.Optional("history", default=0): vol.All(int, vol.Range(min=0, max=500)),
    }
)
@websocket_api.require_admin
@callback
def ws_subscribe_telegrams(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Stream telegrams live; with history > 0 the last N buffered ones first."""
    monitor = async_get_hub(hass).monitor
    entry_id = msg.get("entry_id")

    @callback
    def forward(entry: MonitorEntry) -> None:
        if entry_id is None or entry.gateway == entry_id:
            connection.send_message(websocket_api.event_message(msg["id"], describe(hass, entry)))

    connection.subscriptions[msg["id"]] = monitor.subscribe(forward)
    connection.send_result(msg["id"])
    if msg["history"]:
        for entry in monitor.history(entry_id, msg["history"]):
            forward(entry)


@websocket_api.websocket_command({vol.Required("type"): "enocean_eltako/gateways"})
@websocket_api.require_admin
@callback
def ws_gateways(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The gateway entries with their state: the panel's overview and filter."""
    entries = hass.config_entries.async_entries(DOMAIN, include_ignore=False)
    connection.send_result(msg["id"], [gateway_status(e) for e in entries])


def gateway_status(entry: ConfigEntry) -> dict[str, Any]:
    model = MODELS.get(entry.data.get(CONF_MODEL, ""))
    status: dict[str, Any] = {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "model": model.name if model else None,
        "base_id": entry.data.get(CONF_BASE_ID),
        "loaded": entry.state is ConfigEntryState.LOADED,
    }
    runtime = getattr(entry, "runtime_data", None)
    if status["loaded"] and runtime is not None:
        gateway = runtime.gateway
        status |= {
            "connected": gateway.connected,
            "on_demand": runtime.on_demand,
            "connection": str(gateway.connection),
            "telegrams": gateway.telegrams_received,
            "last_telegram": gateway.last_telegram,
            "queue": len(runtime.queue),
            "unconfirmed": runtime.queue.stats.unconfirmed + runtime.queue.stats.failed,
            "devices": len(runtime.devices),
            "free_senders": runtime.senders.pool.free_count(),
            "disconnected_since": runtime.disconnected_since,
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
    """Panel "add as device": a discovered-device card for a sender from the monitor.

    Uses the sender's last received telegram (gateway, type, teach-in); works also with
    discovery switched off. The result names the flow, or why there is none (already set
    up, ignored, card already there).
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
    hub.discovered.add(sender)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data=discovery_data(last.gateway, sender, last.telegram),
    )
    if result["type"] is FlowResultType.ABORT:
        connection.send_result(msg["id"], {"reason": result["reason"]})
        return
    connection.send_result(msg["id"], {"flow_id": result["flow_id"]})
