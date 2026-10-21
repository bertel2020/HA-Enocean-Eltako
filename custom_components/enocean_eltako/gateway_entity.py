"""Entities of the gateway itself: connection, traffic, send queue and sender IDs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfInformation
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from .const import CONF_BASE_ID, CONF_DEVICE, DOMAIN

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry, GatewayRuntime


class GatewayEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: EnOceanEltakoConfigEntry, key: str) -> None:
        self._entry = entry
        self._attr_translation_key = f"gateway_{key}"
        self._attr_unique_id = f"{entry.entry_id}_gateway_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def _runtime(self) -> GatewayRuntime:
        return self._entry.runtime_data


class GatewayConnectionSensor(GatewayEntity, BinarySensorEntity):
    """Connected to the gateway; on-demand bus gateways only while the group needs them."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, entry: EnOceanEltakoConfigEntry) -> None:
        super().__init__(entry, "connection")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._runtime.add_connection_listener(self._changed))

    @callback
    def _changed(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._runtime.gateway.connected


@dataclass(frozen=True, kw_only=True)
class GatewaySensorDescription(SensorEntityDescription):
    value_fn: Callable[[GatewayRuntime, EnOceanEltakoConfigEntry], Any]
    bus_only: bool = False
    tcp_only: bool = False


def _last_telegram(runtime: GatewayRuntime, _entry: Any) -> datetime | None:
    last = runtime.gateway.last_telegram
    return dt_util.utc_from_timestamp(last) if last is not None else None


GATEWAY_SENSORS: tuple[GatewaySensorDescription, ...] = (
    GatewaySensorDescription(
        key="telegrams",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda r, _e: r.gateway.telegrams_received,
    ),
    GatewaySensorDescription(
        key="last_telegram",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_telegram,
    ),
    GatewaySensorDescription(
        key="bytes",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        entity_registry_enabled_default=False,
        value_fn=lambda r, _e: r.gateway.bytes_received,
    ),
    GatewaySensorDescription(
        key="address",
        entity_category=EntityCategory.DIAGNOSTIC,
        tcp_only=True,
        value_fn=lambda _r, e: e.data[CONF_DEVICE].get("host"),
    ),
    GatewaySensorDescription(
        key="queue",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r, _e: len(r.queue),
    ),
    GatewaySensorDescription(
        key="retries",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r, _e: r.queue.stats.retries,
    ),
    GatewaySensorDescription(
        key="failed",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r, _e: r.queue.stats.unconfirmed + r.queue.stats.failed,
    ),
    GatewaySensorDescription(
        key="base_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda _r, e: e.data[CONF_BASE_ID],
    ),
    GatewaySensorDescription(
        key="free_senders",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r, _e: r.senders.pool.free_count(),
    ),
    GatewaySensorDescription(
        key="polls_dropped",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        bus_only=True,
        value_fn=lambda r, _e: r.gateway.polls_dropped,
    ),
)


class GatewaySensor(GatewayEntity, SensorEntity):
    """Counters and values read from the runtime; polled every 30 s."""

    _attr_should_poll = True
    entity_description: GatewaySensorDescription

    def __init__(
        self, entry: EnOceanEltakoConfigEntry, description: GatewaySensorDescription
    ) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._runtime, self._entry)


class GatewayReconnectButton(GatewayEntity, ButtonEntity):
    """Drop the connection; the gateway task reconnects at once."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: EnOceanEltakoConfigEntry) -> None:
        super().__init__(entry, "reconnect")

    async def async_press(self) -> None:
        await self._runtime.gateway.disconnect()
