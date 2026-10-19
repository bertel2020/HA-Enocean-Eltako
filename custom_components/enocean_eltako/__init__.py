"""The EnOcean Eltako integration."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .catalog import CATALOG, CENTRAL, OPT_STATUS_REQUEST, PLATFORMS, STATUS_REQUEST
from .const import (
    CONF_BASE_ID,
    CONF_BUS_GROUP,
    CONF_DEVICE,
    CONF_MESSAGE_DELAY,
    CONF_MODE,
    CONF_MODEL,
    CONF_PROFILE,
    CONF_SENDER_ID,
    CONF_SENDERS,
    DEFAULT_MESSAGE_DELAY,
    DOMAIN,
    MODE_ALWAYS,
    MODE_ON_DEMAND,
)
from .device import EnOceanDevice
from .health import async_setup_health
from .hub import BusGroupRuntime, Hub, async_get_hub
from .protocol.bus_group import BusMember
from .protocol.dispatcher import WILDCARD, ReceivedTelegram
from .protocol.gateway import Gateway
from .protocol.ids import parse_id
from .protocol.models import MODELS
from .protocol.send_queue import Priority, SendQueue
from .protocol.sender_pool import SenderState
from .protocol.telegram import RadioTelegram
from .protocol.transport import connection_from_dict
from .senders import SenderStore, async_remove_store, bus_key, radio_key
from .services import async_setup_services
from .subentry_flow import sender_owner
from .websocket import async_setup_websocket

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


@dataclass
class GatewayRuntime:
    """Runtime data of one gateway entry."""

    hub: Hub
    gateway: Gateway
    queue: SendQueue
    senders: SenderStore  # radio sender IDs: base ID + 0...127
    on_demand: bool = False
    bus: BusGroupRuntime | None = None
    devices: dict[str, EnOceanDevice] = field(default_factory=dict)  # by subentry ID
    disconnected_since: float | None = None  # time.time() of the last disconnect
    health_check: Callable[[], None] | None = None


type EnOceanEltakoConfigEntry = ConfigEntry[GatewayRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the telegram monitor websocket API and services."""
    async_setup_websocket(hass)
    async_setup_services(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """1.1 -> 1.2: device subentries move "sender_id" into "senders" (schema 2)."""
    if entry.version > 1:
        return False  # downgrade not supported
    if entry.minor_version < 2:
        for subentry in list(entry.subentries.values()):
            data = dict(subentry.data)
            if data.get("schema", 1) >= 2:
                continue
            model = CATALOG.get(data.get(CONF_MODEL, ""))
            sender = data.pop(CONF_SENDER_ID, None)
            if sender and model and model.senders:
                data[CONF_SENDERS] = [{CONF_PROFILE: model.senders[0].id, CONF_SENDER_ID: sender}]
            data["schema"] = 2
            hass.config_entries.async_update_subentry(entry, subentry, data=data)
        hass.config_entries.async_update_entry(entry, minor_version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """Connect the gateway (unless on demand), feed the dispatcher, join the bus group."""
    model = MODELS[entry.data[CONF_MODEL]]
    hub = async_get_hub(hass)
    on_demand = model.bus and entry.options.get(CONF_MODE, MODE_ALWAYS) == MODE_ON_DEMAND

    @callback
    def on_telegram(telegram: RadioTelegram) -> None:
        hub.dispatcher.dispatch(entry.entry_id, telegram)

    @callback
    def on_connection_change(connected: bool) -> None:
        if hasattr(entry, "runtime_data"):
            entry.runtime_data.disconnected_since = None if connected else time.time()

    gateway = Gateway(
        model.protocol,
        connection_from_dict(entry.data[CONF_DEVICE]),
        on_telegram=on_telegram,
        on_connection_change=on_connection_change,
    )
    if not on_demand:
        try:
            await gateway.connect()
        except (OSError, TimeoutError) as err:
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={
                    "connection": str(gateway.connection),
                    "error": str(err),
                },
            ) from err
    queue = SendQueue(
        gateway.send,
        is_connected=lambda: gateway.connected,
        delay=entry.options.get(CONF_MESSAGE_DELAY, DEFAULT_MESSAGE_DELAY) / 1000,
        on_sent=lambda telegram: hub.monitor.sent(entry.entry_id, telegram),
    )
    pool = hub.senders.create_pool(radio_key(entry.entry_id), parse_id(entry.data[CONF_BASE_ID]))
    entry.async_on_unload(lambda: hub.senders.remove_pool(radio_key(entry.entry_id)))
    senders = SenderStore(hass, radio_key(entry.entry_id), pool)
    await senders.async_load()

    bus = None
    if model.bus:
        group_key = entry.data[CONF_BUS_GROUP]
        member = BusMember(entry.entry_id, entry.title, gateway, queue, on_demand=on_demand)
        bus = await hub.async_join_bus_group(hass, group_key, member)
        entry.async_on_unload(lambda: hub.leave_bus_group(group_key, entry.entry_id))

    entry.runtime_data = GatewayRuntime(hub, gateway, queue, senders, on_demand, bus)

    @callback
    def confirm(received: ReceivedTelegram) -> None:
        # actuator answers may arrive over any gateway
        queue.on_telegram(received.telegram)

    entry.async_on_unload(hub.dispatcher.add_listener(WILDCARD, confirm))

    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="EnOcean",
        model=model.name,
        serial_number=entry.data[CONF_BASE_ID],
    )
    _async_setup_devices(hass, entry)
    entry.runtime_data.health_check = async_setup_health(hass, entry)
    _async_request_states(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    if not on_demand:
        entry.async_create_background_task(hass, gateway.run(), f"{DOMAIN} {entry.title}")
    entry.async_create_background_task(hass, queue.run(), f"{DOMAIN} {entry.title} queue")
    return True


def _async_setup_devices(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """One runtime object per device subentry; release sender IDs of removed devices."""
    runtime = entry.runtime_data
    owners = set()
    for subentry_id, subentry in entry.subentries.items():
        device = EnOceanDevice(hass, entry, subentry)
        runtime.devices[subentry_id] = device
        entry.async_on_unload(device.start())
        owners.update(sender_owner(device.device_id, p) for p in device.senders)
    pool = runtime.senders.pool
    released = False
    for sender, allocation in pool.allocations():
        if (
            allocation.state is SenderState.ASSIGNED
            and allocation.owner.startswith("device:")
            and allocation.owner not in owners
        ):
            pool.release(sender)  # blocked until the teach-out is confirmed
            released = True
    if released:
        runtime.senders.async_schedule_save()


def _async_request_states(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """E2: ask actuators that support it for their state, at background priority.

    The send queue spaces them out; actuators without a query report on their next change.
    """

    @callback
    def request(_event: Any = None) -> None:
        for device in entry.runtime_data.devices.values():
            if device.options.get(OPT_STATUS_REQUEST) and device.has_sender(CENTRAL.id):
                with contextlib.suppress(HomeAssistantError):
                    device.send(
                        STATUS_REQUEST,
                        profile=CENTRAL.id,
                        priority=Priority.BACKGROUND,
                        confirm=False,
                    )

    if hass.state is CoreState.running:
        request()
    else:
        entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, request))


async def _async_reload_on_change(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Subentries added or removed: rebuild devices and entities."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """Unload platforms, stop the send queue and close the gateway connection."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.queue.stop()
    await entry.runtime_data.gateway.close()
    entry.runtime_data.hub.monitor.clear(entry.entry_id)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Delete the stored sender pools (the bus pool with the last member of its group)."""
    await async_remove_store(hass, radio_key(entry.entry_id))
    if group := entry.data.get(CONF_BUS_GROUP):
        others = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.data.get(CONF_BUS_GROUP) == group
        ]
        if not others:
            await async_remove_store(hass, bus_key(group))
