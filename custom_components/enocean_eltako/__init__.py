"""The EnOcean Eltako integration.

One config entry per gateway, one config subentry per device. Gateway handling,
the dispatcher and the platforms are added in phase 1 and 2 of the plan.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a gateway from a config entry."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a gateway config entry."""
    return True
