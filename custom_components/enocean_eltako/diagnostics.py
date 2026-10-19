"""Diagnostics: connection, counters, queue, sender pool and the last telegrams."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import EnOceanEltakoConfigEntry

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
        },
        "dispatcher": runtime.hub.dispatcher.stats.as_dict(),
        "send_queue": {"length": len(runtime.queue), **runtime.queue.stats.as_dict()},
        "sender_pool": runtime.senders.pool.as_dict(),
        "telegrams": [e.as_dict() for e in runtime.hub.monitor.history(entry.entry_id, TELEGRAMS)],
    }
