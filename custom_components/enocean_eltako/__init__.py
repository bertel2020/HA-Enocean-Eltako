"""The EnOcean Eltako integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import CONF_BASE_ID, CONF_DEVICE, CONF_MODEL, DOMAIN
from .hub import Hub, async_get_hub
from .protocol.dispatcher import WILDCARD, ReceivedTelegram
from .protocol.gateway import Gateway
from .protocol.ids import parse_id
from .protocol.models import MODELS
from .protocol.send_queue import SendQueue
from .protocol.telegram import RadioTelegram
from .protocol.transport import connection_from_dict
from .senders import SenderStore, async_remove_store
from .services import async_setup_services
from .websocket import async_setup_websocket

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class GatewayRuntime:
    """Runtime data of one gateway entry."""

    hub: Hub
    gateway: Gateway
    queue: SendQueue
    senders: SenderStore


type EnOceanEltakoConfigEntry = ConfigEntry[GatewayRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the telegram monitor websocket API and services."""
    async_setup_websocket(hass)
    async_setup_services(hass)
    return True


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
    queue = SendQueue(
        gateway.send,
        is_connected=lambda: gateway.connected,
        on_sent=lambda telegram: hub.monitor.sent(entry.entry_id, telegram),
    )
    pool = hub.senders.create_pool(entry.entry_id, parse_id(entry.data[CONF_BASE_ID]))
    entry.async_on_unload(lambda: hub.senders.remove_pool(entry.entry_id))
    senders = SenderStore(hass, entry.entry_id, pool)
    await senders.async_load()
    entry.runtime_data = GatewayRuntime(hub=hub, gateway=gateway, queue=queue, senders=senders)

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
    entry.runtime_data.hub.monitor.clear(entry.entry_id)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Delete the stored sender pool."""
    await async_remove_store(hass, entry.entry_id)
