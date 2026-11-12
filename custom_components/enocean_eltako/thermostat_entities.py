"""Extra entities of a channel's thermostat (optional): run time, forced pause, time on today,
"heating" and "blocked". They only show what the controller knows (thermostat.py)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import callback

from .catalog import OPT_THERMOSTAT_ENTITIES
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .thermostat import ThermostatController, controller_for, enabled

SENSORS: tuple[tuple[str, Callable[[ThermostatController], Any], UnitOfTime], ...] = (
    ("thermostat_run", lambda c: c.run_minutes, UnitOfTime.MINUTES),
    ("thermostat_cooldown", lambda c: c.cooldown_remaining, UnitOfTime.MINUTES),
    ("thermostat_on_today", lambda c: c.on_hours_today, UnitOfTime.HOURS),
)
BINARY_SENSORS: tuple[tuple[str, Callable[[ThermostatController], bool]], ...] = (
    ("thermostat_heating", lambda c: c.is_heating),
    ("thermostat_blocked", lambda c: c.is_blocked),
)


def wanted(device: EnOceanDevice) -> bool:
    """The channel has a thermostat and its extra entities are switched on."""
    return enabled(device) and bool(device.options.get(OPT_THERMOSTAT_ENTITIES, True))


class _Follower(EnOceanEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: EnOceanDevice, key: str) -> None:
        super().__init__(device, key)
        self._attr_translation_key = key
        self._ctl = controller_for(device.hass, device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._ctl.start()
        self.async_on_remove(self._ctl.stop)
        self.async_on_remove(self._ctl.add_listener(self._changed))

    @callback
    def _changed(self) -> None:
        self.async_write_ha_state()

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class ThermostatSensor(_Follower, SensorEntity):
    def __init__(
        self,
        device: EnOceanDevice,
        key: str,
        value_fn: Callable[[ThermostatController], Any],
        unit: UnitOfTime,
    ) -> None:
        super().__init__(device, key)
        self._value_fn = value_fn
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        return self._value_fn(self._ctl)


class ThermostatBinarySensor(_Follower, BinarySensorEntity):
    def __init__(
        self,
        device: EnOceanDevice,
        key: str,
        value_fn: Callable[[ThermostatController], bool],
    ) -> None:
        super().__init__(device, key)
        self._value_fn = value_fn

    @property
    def is_on(self) -> bool:
        return self._value_fn(self._ctl)


def thermostat_sensors(device: EnOceanDevice) -> list[ThermostatSensor]:
    return [ThermostatSensor(device, key, fn, unit) for key, fn, unit in SENSORS]


def thermostat_binary_sensors(device: EnOceanDevice) -> list[ThermostatBinarySensor]:
    return [ThermostatBinarySensor(device, key, fn) for key, fn in BINARY_SENSORS]
