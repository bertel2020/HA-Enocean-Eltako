"""E5: repair issues for silent devices and gateways that stay disconnected."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

CHECK_INTERVAL = timedelta(minutes=1)
GATEWAY_REPAIR_AFTER = 5 * 60  # seconds


def device_issue_id(unique_prefix: str) -> str:
    return f"device_silent_{unique_prefix}"


def gateway_issue_id(entry_id: str) -> str:
    return f"gateway_disconnected_{entry_id}"


@callback
def async_setup_health(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> Callable[[], None]:
    """Start the periodic check; returns it for an immediate run."""

    @callback
    def check(_now: Any = None) -> None:
        now = time.time()
        runtime = entry.runtime_data
        for device in runtime.devices.values():
            issue_id = device_issue_id(device.unique_prefix)
            if device.check_silence(now):
                hours = (now - (device.stats.last_seen or device.started)) / 3600
                gateway = hass.config_entries.async_get_entry(device.stats.gateway or "")
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="device_silent",
                    translation_placeholders={
                        "name": device.subentry.title,
                        "hours": f"{hours:.1f}",
                        "gateway": gateway.title if gateway else "-",
                    },
                )
            else:
                ir.async_delete_issue(hass, DOMAIN, issue_id)
        issue_id = gateway_issue_id(entry.entry_id)
        since = runtime.disconnected_since
        if not runtime.on_demand and since is not None and now - since > GATEWAY_REPAIR_AFTER:
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key="gateway_disconnected",
                translation_placeholders={
                    "name": entry.title,
                    "connection": str(runtime.gateway.connection),
                },
            )
        else:
            ir.async_delete_issue(hass, DOMAIN, issue_id)

    entry.async_on_unload(async_track_time_interval(hass, check, CHECK_INTERVAL))

    def clear() -> None:
        ir.async_delete_issue(hass, DOMAIN, gateway_issue_id(entry.entry_id))
        for device in entry.runtime_data.devices.values():
            ir.async_delete_issue(hass, DOMAIN, device_issue_id(device.unique_prefix))

    entry.async_on_unload(clear)
    return check
