"""The EnOcean Eltako integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_DEVICE, CONF_MODEL, DOMAIN
from .hub import Hub, async_get_hub
from .protocol.dispatcher import WILDCARD, ReceivedTelegram
from .protocol.gateway import Gateway
from .protocol.models import MODELS
from .protocol.send_queue import SendQueue
from .protocol.telegram import RadioTelegram
from .protocol.transport import connection_from_dict


@dataclass
class GatewayRuntime:
    """Runtime data of one gateway entry."""

    hub: Hub
    gateway: Gateway
    queue: SendQueue


type EnOceanEltakoConfigEntry = ConfigEntry[GatewayRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """Connect the gateway, feed the dispatcher and keep the connection up."""
    model = MODELS[entry.data[CONF_MODEL]]
    hub = async_get_hub(hass)

    @callback
    def on_telegram(telegram: RadioTelegram) -> None:
        hub.dispatcher.dispatch(entry.entry_id, telegram)

    gateway = Gateway(
        model.protocol, connection_from_dict(entry.data[CONF_DEVICE]), on_telegram=on_telegram
    )
    try:
        await gateway.connect()
    except (OSError, TimeoutError) as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"connection": str(gateway.connection), "error": str(err)},
        ) from err
    queue = SendQueue(gateway.send, is_connected=lambda: gateway.connected)
    entry.runtime_data = GatewayRuntime(hub=hub, gateway=gateway, queue=queue)

    @callback
    def confirm(received: ReceivedTelegram) -> None:
        # actuator answers may arrive over any gateway
        queue.on_telegram(received.telegram)

    entry.async_on_unload(hub.dispatcher.add_listener(WILDCARD, confirm))
    entry.async_create_background_task(hass, gateway.run(), f"{DOMAIN} {entry.title}")
    entry.async_create_background_task(hass, queue.run(), f"{DOMAIN} {entry.title} queue")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """Stop the send queue and close the gateway connection."""
    await entry.runtime_data.queue.stop()
    await entry.runtime_data.gateway.close()
    return True
