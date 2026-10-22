"""The old eltako integration on the same gateway: both would fight over one connection.

A serial port opens only once and an MGW-ETH serves one session, so two integrations on the
same USB path or host and port block each other. A repair issue names the old entry; it goes
away when the old integration no longer uses that gateway. Gateways reached through the
Device Proxy app are not affected (the old integration cannot share them).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import CONF_DEVICE, DOMAIN

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

OLD_DOMAIN = "eltako"
_ACTIVE = (
    ConfigEntryState.LOADED,
    ConfigEntryState.SETUP_RETRY,
    ConfigEntryState.SETUP_IN_PROGRESS,
)


def issue_id(entry_id: str) -> str:
    return f"old_integration_shares_gateway_{entry_id}"


def _uses(old: dict[str, Any], device: dict[str, Any]) -> bool:
    """The old entry's gateway is the one of this device (same port, or same host and port)."""
    path = old.get("serial_path") or old.get("custom_serial_path")
    if not path:
        return False
    if device.get("type") == "serial":
        return bool(path == device.get("path"))
    return bool(
        device.get("type") == "tcp"
        and path == device.get("host")
        and str(old.get("port")) == str(device.get("port"))
    )


def sharing_entries(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> list[ConfigEntry]:
    """Entries of the old integration that are set up on this entry's connection."""
    device = entry.data.get(CONF_DEVICE, {})
    return [
        old
        for old in hass.config_entries.async_entries(OLD_DOMAIN)
        if old.disabled_by is None and old.state in _ACTIVE and _uses(dict(old.data), device)
    ]


@callback
def async_check_old_integration(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Raise or clear the repair issue for this gateway."""
    if not sharing_entries(hass, entry):
        ir.async_delete_issue(hass, DOMAIN, issue_id(entry.entry_id))
        return
    device = entry.data.get(CONF_DEVICE, {})
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id(entry.entry_id),
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="old_integration_shares_gateway",
        translation_placeholders={
            "name": entry.title,
            "connection": str(device.get("path") or f"{device.get('host')}:{device.get('port')}"),
        },
    )
