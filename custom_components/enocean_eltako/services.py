"""Services: capture telegrams to a JSONL file (usable as test fixture)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import probatio as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .hub import async_get_hub
from .protocol.monitor import MonitorEntry

SERVICE_CAPTURE = "capture"
ATTR_DURATION = "duration"
ATTR_ENTRY_ID = "config_entry_id"

CAPTURE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DURATION, default=60): vol.All(int, vol.Range(min=1, max=3600)),
        vol.Optional(ATTR_ENTRY_ID): str,
    }
)


def _write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def capture(call: ServiceCall) -> ServiceResponse:
        """Record telegrams for `duration` seconds, then write them; returns the file path."""
        entry_id = call.data.get(ATTR_ENTRY_ID)
        stamp = dt_util.now().strftime("%Y%m%d-%H%M%S")
        path = Path(hass.config.path(DOMAIN, f"capture-{stamp}.jsonl"))
        lines: list[str] = []

        @callback
        def record(entry: MonitorEntry) -> None:
            if entry_id is None or entry.gateway == entry_id:
                lines.append(json.dumps(entry.as_dict()) + "\n")

        unsubscribe = async_get_hub(hass).monitor.subscribe(record)

        async def finish(_now: datetime) -> None:
            unsubscribe()
            await hass.async_add_executor_job(_write, path, lines)

        async_call_later(hass, call.data[ATTR_DURATION], finish)
        return {"path": str(path)}

    hass.services.async_register(
        DOMAIN,
        SERVICE_CAPTURE,
        capture,
        schema=CAPTURE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
