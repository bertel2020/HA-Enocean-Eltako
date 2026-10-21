"""Diagnostics: connection, counters, queue, sender pool and the last telegrams."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import EnOceanEltakoConfigEntry
from .protocol.ids import format_id

TELEGRAMS = 100


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry
) -> dict[str, Any]:
    runtime = entry.runtime_data
    return {
        "entry": {"title": entry.title, "data": dict(entry.data), "options": dict(entry.options)},
        "gateway": {
            "connected": runtime.gateway.connected,
            "connection": str(runtime.gateway.connection),
            "telegrams_received": runtime.gateway.telegrams_received,
            "polls_dropped": runtime.gateway.polls_dropped,
            "bytes_received": runtime.gateway.bytes_received,
            "bytes_unparsed": runtime.gateway.bytes_unparsed,
            "ignored_packets": dict(runtime.gateway.ignored),
            "on_demand": runtime.on_demand,
        },
        "bus_group": runtime.bus.group.as_dict() if runtime.bus else None,
        "bus_sender_pool": runtime.bus.senders.pool.as_dict() if runtime.bus else None,
        "dispatcher": runtime.hub.dispatcher.stats.as_dict(),
        "send_queue": {"length": len(runtime.queue), **runtime.queue.stats.as_dict()},
        "sender_pool": runtime.senders.pool.as_dict(),
        "devices": [
            {
                "title": d.subentry.title,
                "model": d.model.id,
                "device_id": format_id(d.device_id),
                "senders": {profile: format_id(s) for profile, s in d.senders.items()},
                "receive_eep": str(d.model.receive) if d.model.receive else None,
                "send_eep": str(d.model.send) if d.model.send else None,
                "last_telegram": d.last_received.timestamp if d.last_received else None,
            }
            for d in runtime.devices.values()
        ],
        "telegrams": [e.as_dict() for e in runtime.hub.monitor.history(entry.entry_id, TELEGRAMS)],
    }
