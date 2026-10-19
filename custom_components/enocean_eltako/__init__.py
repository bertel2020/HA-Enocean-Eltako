"""The EnOcean Eltako integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_CONNECTION, CONF_MODEL, DOMAIN
from .protocol.gateway import Gateway
from .protocol.models import MODELS
from .protocol.telegram import RadioTelegram
from .protocol.transport import connection_from_dict

_LOGGER = logging.getLogger(__name__)

type EnOceanEltakoConfigEntry = ConfigEntry[Gateway]


async def async_setup_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """Connect the gateway and keep it connected."""
    model = MODELS[entry.data[CONF_MODEL]]

    def on_telegram(telegram: RadioTelegram) -> None:
        # The dispatcher (next step of phase 1) takes over here.
        _LOGGER.debug("%s: %s", entry.title, telegram)

    gateway = Gateway(
        model.protocol, connection_from_dict(entry.data[CONF_CONNECTION]), on_telegram=on_telegram
    )
    try:
        await gateway.connect()
    except (OSError, TimeoutError) as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"connection": str(gateway.connection), "error": str(err)},
        ) from err
    entry.runtime_data = gateway
    entry.async_create_background_task(hass, gateway.run(), f"{DOMAIN} {entry.title}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """Close the gateway connection."""
    await entry.runtime_data.close()
    return True
