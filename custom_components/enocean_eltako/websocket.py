"""Websocket API of the telegram monitor (E4)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .hub import async_get_hub
from .protocol.monitor import MonitorEntry


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe_telegrams)


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
            connection.send_message(websocket_api.event_message(msg["id"], entry.as_dict()))

    connection.subscriptions[msg["id"]] = monitor.subscribe(forward)
    connection.send_result(msg["id"])
    if msg["history"]:
        for entry in monitor.history(entry_id, msg["history"]):
            forward(entry)
