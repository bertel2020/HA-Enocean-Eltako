"""Websocket API of the telegram monitor (E4) and its panel.

Each telegram is sent with what Home Assistant knows about it: the gateway's name, the
device it comes from (or, for sent telegrams, the device and sender profile of the sender
ID), the decoded values, and the EEP of a 4BS teach-in from an unknown sender.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .hub import async_get_hub
from .protocol.eep.codecs import decode_telegram
from .protocol.eep.teach_in import decode_teach_in_4bs
from .protocol.monitor import MonitorEntry
from .protocol.telegram import Rorg


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe_telegrams)
    websocket_api.async_register_command(hass, ws_gateways)


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
    """The gateway entries, for the panel's filter."""
    connection.send_result(
        msg["id"],
        [
            {"entry_id": e.entry_id, "title": e.title, "loaded": e.entry_id in loaded}
            for loaded in [{x.entry_id for x in hass.config_entries.async_loaded_entries(DOMAIN)}]
            for e in hass.config_entries.async_entries(DOMAIN, include_ignore=False)
        ],
    )
