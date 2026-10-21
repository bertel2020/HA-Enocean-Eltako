"""The EnOcean Eltako integration."""

from __future__ import annotations

import contextlib
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .catalog import (
    CATALOG,
    CENTRAL,
    DIRECTION_ROCKER,
    GENERIC_EEP,
    GROUP_VIRTUAL,
    OPT_CHANNEL,
    OPT_FIELDS,
    OPT_PLATFORM,
    OPT_ROCKER_OFF,
    OPT_ROCKER_ON,
    OPT_STATUS_REQUEST,
    PLATFORMS,
    ROCKER,
    STATUS_REQUEST,
    generic_fields,
)
from .const import (
    CONF_BASE_ID,
    CONF_BUS_GROUP,
    CONF_DEVICE,
    CONF_MESSAGE_DELAY,
    CONF_MODE,
    CONF_MODEL,
    CONF_PROFILE,
    CONF_PROXY_REPLAY,
    CONF_REPEATER,
    CONF_SENDER_ID,
    CONF_SENDERS,
    DEFAULT_MESSAGE_DELAY,
    DOMAIN,
    MODE_ALWAYS,
    MODE_ON_DEMAND,
    PROXY_REPLAY_REQUEST,
    REPEATER_LEVELS,
    REPEATER_UNCHANGED,
)
from .custom_devices import async_load as async_load_custom_devices
from .device import EnOceanDevice
from .discovery import async_abort_configured, async_setup_discovery
from .health import async_setup_health
from .hub import BusGroupRuntime, Hub, async_get_hub
from .panel import async_register_panel
from .protocol.bus_group import BusMember
from .protocol.dispatcher import WILDCARD, ReceivedTelegram
from .protocol.eep import vld
from .protocol.gateway import Gateway
from .protocol.ids import format_id, parse_id
from .protocol.models import MODELS, Protocol
from .protocol.send_queue import Priority, SendQueue
from .protocol.sender_pool import SenderState
from .protocol.telegram import RadioTelegram
from .protocol.transport import connection_from_dict
from .proxy_status import async_setup_proxy_status
from .senders import SenderStore, async_remove_store, bus_key, radio_key
from .services import async_setup_services
from .subentry_flow import sender_owner
from .virtual import VirtualSensor
from .websocket import async_setup_websocket

_LOGGER = logging.getLogger(__name__)

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
    connection_listeners: list[Callable[[], None]] = field(default_factory=list)
    gateway_device_id: str | None = None  # device registry ID, parent of all devices
    proxy: dict[str, Any] | None = None  # EnOcean Proxy app status (proxy_status.py)
    remove_reload_listener: Callable[[], None] | None = None
    drops: deque[float] = field(default_factory=lambda: deque(maxlen=20))  # time.time()

    @callback
    def suspend_reload(self) -> None:
        """No reload per entry change until the next setup (many subentries at once)."""
        if self.remove_reload_listener is not None:
            self.remove_reload_listener()
            self.remove_reload_listener = None

    def add_connection_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self.connection_listeners.append(listener)
        return lambda: self.connection_listeners.remove(listener)


type EnOceanEltakoConfigEntry = ConfigEntry[GatewayRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the telegram monitor websocket API, its panel and the services."""
    async_setup_websocket(hass)
    async_setup_services(hass)
    await async_register_panel(hass)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> bool:
    """1.1 -> 1.2: device subentries move "sender_id" into "senders" (schema 2).

    1.2 -> 1.3: the rocker sender's buttons default to A0/A1; devices with a rocker sender
    keep the B0/B1 they pressed so far as explicit options (schema 3).
    """
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
                # schema 1 had one sender: the central command where the model has one
                profile = next((p for p in model.senders if p.id == CENTRAL.id), model.senders[0])
                data[CONF_SENDERS] = [{CONF_PROFILE: profile.id, CONF_SENDER_ID: sender}]
            data["schema"] = 2
            hass.config_entries.async_update_subentry(entry, subentry, data=data)
        hass.config_entries.async_update_entry(entry, minor_version=2)
    if entry.minor_version < 3:
        for subentry in list(entry.subentries.values()):
            data = dict(subentry.data)
            if data.get("schema", 1) >= 3:
                continue
            profiles = {s[CONF_PROFILE] for s in data.get(CONF_SENDERS, ())}
            if profiles & {ROCKER.id, DIRECTION_ROCKER.id}:
                data.setdefault(OPT_ROCKER_ON, "b0")
                data.setdefault(OPT_ROCKER_OFF, "b1")
            data["schema"] = 3
            hass.config_entries.async_update_subentry(entry, subentry, data=data)
        hass.config_entries.async_update_entry(entry, minor_version=3)
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
    def on_replayed(telegram: RadioTelegram, received_at: float) -> None:
        """Telegrams the EnOcean Proxy kept during a restart, with their reception time."""
        hub.dispatcher.dispatch(entry.entry_id, telegram, timestamp=received_at)

    @callback
    def on_connection_change(connected: bool) -> None:
        if hasattr(entry, "runtime_data"):
            entry.runtime_data.disconnected_since = None if connected else time.time()
            if not connected:
                entry.runtime_data.drops.append(time.time())
            for listener in list(entry.runtime_data.connection_listeners):
                listener()
            if connected:
                _async_apply_repeater(hass, entry)
                _async_check_base_id(hass, entry)

    gateway = Gateway(
        model.protocol,
        connection_from_dict(entry.data[CONF_DEVICE]),
        on_telegram=on_telegram,
        on_connection_change=on_connection_change,
        hello=PROXY_REPLAY_REQUEST if entry.options.get(CONF_PROXY_REPLAY) else b"",
        on_replayed=on_replayed,
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
    # also when a later step of this setup fails: HA then runs the unload callbacks but not
    # async_unload_entry, and an open serial port would block the next attempt
    entry.async_on_unload(gateway.close)
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

    entry.runtime_data.gateway_device_id = (
        dr.async_get(hass)
        .async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=model.manufacturer,
            model=model.model_name,
            serial_number=entry.data[CONF_BASE_ID],
        )
        .id
    )
    await async_load_custom_devices(hass)  # I8: re-read on every (re)load
    _async_setup_devices(hass, entry)
    async_abort_configured(hass, entry)
    entry.async_on_unload(async_setup_discovery(hass, entry))
    if (stop_proxy_status := async_setup_proxy_status(hass, entry)) is not None:
        entry.async_on_unload(stop_proxy_status)
    if gateway.connected:
        _async_apply_repeater(hass, entry)
        _async_check_base_id(hass, entry)
    entry.async_on_unload(
        lambda: ir.async_delete_issue(hass, DOMAIN, base_id_issue_id(entry.entry_id))
    )
    entry.runtime_data.health_check = async_setup_health(hass, entry)
    _async_request_states(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.runtime_data.remove_reload_listener = entry.add_update_listener(_async_reload_on_change)
    entry.async_on_unload(entry.runtime_data.suspend_reload)
    if not on_demand:
        entry.async_create_background_task(hass, gateway.run(), f"{DOMAIN} {entry.title}")
    entry.async_create_background_task(hass, queue.run(), f"{DOMAIN} {entry.title} queue")
    return True


@callback
def _async_apply_repeater(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """ESP3 gateways: set the chosen repeater level after every (re)connect."""
    level = REPEATER_LEVELS.get(entry.options.get(CONF_REPEATER, REPEATER_UNCHANGED))
    if level is None or MODELS[entry.data[CONF_MODEL]].protocol is not Protocol.ESP3:
        return

    async def write() -> None:
        try:
            ok = await entry.runtime_data.gateway.write_repeater(level)
        except ConnectionError:
            ok = False
        if not ok:
            _LOGGER.warning("%s did not accept repeater level %s", entry.title, level)

    entry.async_create_background_task(hass, write(), f"{DOMAIN} {entry.title} repeater")


def base_id_issue_id(entry_id: str) -> str:
    return f"base_id_changed_{entry_id}"


@callback
def _async_check_base_id(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """E3: after every (re)connect, the gateway must still report the configured base ID.

    Otherwise (gateway swapped, TCM replaced) every sender ID is wrong: the actuators know
    the old IDs and the new gateway refuses to send from them. A repair issue says so.
    """
    if not MODELS[entry.data[CONF_MODEL]].reads_base_id:
        return
    configured = parse_id(entry.data[CONF_BASE_ID])

    async def check() -> None:
        try:
            reported = await entry.runtime_data.gateway.read_base_id()
        except ConnectionError:
            return
        if reported is None:
            return
        issue_id = base_id_issue_id(entry.entry_id)
        if reported == configured:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
            return
        _LOGGER.warning(
            "%s reports base ID %s instead of %s",
            entry.title,
            format_id(reported),
            format_id(configured),
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key="base_id_changed",
            translation_placeholders={
                "name": entry.title,
                "configured": format_id(configured),
                "reported": format_id(reported),
            },
        )

    entry.async_create_background_task(hass, check(), f"{DOMAIN} {entry.title} base ID")


def _async_setup_devices(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """One runtime object per device subentry; release sender IDs of removed devices."""
    runtime = entry.runtime_data
    owners: set[str] = set()
    for subentry_id, subentry in entry.subentries.items():
        device = EnOceanDevice(hass, entry, subentry)
        runtime.devices[subentry_id] = device
        entry.async_on_unload(device.start())
        buttons_only = device.model.kind in ("virtual_rocker", "virtual_scene")
        if device.model.group == GROUP_VIRTUAL and not buttons_only:
            device.virtual = VirtualSensor(hass, device)
            entry.async_on_unload(device.virtual.start())
        owners.update(sender_owner(device.device_id, p, device.channel) for p in device.senders)
    _async_remove_stale_entities(hass, entry)
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


def _async_remove_stale_entities(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """Drop entities of choices no longer made: light vs. switch, removed sender profiles."""
    registry = er.async_get(hass)
    stale: list[tuple[str, str]] = []
    for device in entry.runtime_data.devices.values():
        prefix = device.entity_prefix
        if device.model.kind in ("switch", "psc", "vld_switch"):
            default = Platform.SWITCH if device.model.kind == "psc" else Platform.LIGHT
            chosen = device.options.get(OPT_PLATFORM, default)
            other = Platform.SWITCH if chosen == Platform.LIGHT else Platform.LIGHT
            stale.append((other, f"{prefix}_{'light' if other == Platform.LIGHT else 'switch'}"))
        if device.model.id == GENERIC_EEP and device.model.receive is not None:
            chosen = device.options.get(OPT_FIELDS)
            for key, _field in generic_fields(device.model.receive.eep):
                if chosen is not None and key not in chosen:
                    stale.append((Platform.SENSOR, f"{prefix}_{key}"))
        for profile in device.model.senders:
            if profile.id not in device.senders:
                stale.append((Platform.SENSOR, f"{prefix}_sender_id_{profile.id}"))
                stale.append((Platform.BUTTON, f"{prefix}_teach_in_{profile.id}"))
    for platform, unique_id in stale:
        if entity_id := registry.async_get_entity_id(platform, DOMAIN, unique_id):
            registry.async_remove(entity_id)


# VLD actuators answer a status query with their state (D2-01 command 3, D2-05 command 3)
VLD_QUERIES = {"vld_switch": vld.encode_switch_query, "vld_cover": vld.encode_blind_query}


def _async_request_states(hass: HomeAssistant, entry: EnOceanEltakoConfigEntry) -> None:
    """E2: ask actuators that support it for their state, at background priority.

    The send queue spaces them out; actuators without a query report on their next change.
    """

    @callback
    def request(_event: Any = None) -> None:
        for device in entry.runtime_data.devices.values():
            if not device.options.get(OPT_STATUS_REQUEST):
                continue
            if device.has_sender(CENTRAL.id):
                query, profile = STATUS_REQUEST, CENTRAL.id
            elif device.model.kind in VLD_QUERIES and device.senders:
                channel = int(device.options.get(OPT_CHANNEL, 0))
                query, profile = VLD_QUERIES[device.model.kind](channel), None
            else:
                continue
            with contextlib.suppress(HomeAssistantError):
                device.send(query, profile=profile, priority=Priority.BACKGROUND, confirm=False)

    # async_at_started: unsubscribing after HA started is safe (async_listen_once is not)
    entry.async_on_unload(async_at_started(hass, request))


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
    ir.async_delete_issue(hass, DOMAIN, f"proxy_outdated_{entry.entry_id}")
    await async_remove_store(hass, radio_key(entry.entry_id))
    if group := entry.data.get(CONF_BUS_GROUP):
        others = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id and e.data.get(CONF_BUS_GROUP) == group
        ]
        if not others:
            await async_remove_store(hass, bus_key(group))
