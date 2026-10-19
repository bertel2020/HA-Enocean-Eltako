"""Sensors from decoded telegram values."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    Platform,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EnOceanEltakoConfigEntry
from .device import EnOceanDevice
from .entity import EnOceanEntity

PARALLEL_UPDATES = 0

HANDLE_POSITIONS = {0xF0: "closed", 0xC0: "open", 0xE0: "open", 0xD0: "tilted"}


@dataclass(frozen=True, kw_only=True)
class EnOceanSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


def _field(name: str, ndigits: int | None = 1) -> Callable[[dict[str, Any]], Any]:
    def get(values: dict[str, Any]) -> Any:
        value = values.get(name)
        if value is None or ndigits is None:
            return value
        return round(value, ndigits)

    return get


def _meter(data_type: int, tariff: int) -> Callable[[dict[str, Any]], Any]:
    def get(values: dict[str, Any]) -> Any:
        if values.get("DT") != data_type or values.get("TI") != tariff:
            return None
        return round(values["MR"], 3)

    return get


def _handle(values: dict[str, Any]) -> Any:
    return HANDLE_POSITIONS.get(values.get("WIN", -1))


TEMPERATURE = {
    "device_class": SensorDeviceClass.TEMPERATURE,
    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
    "state_class": SensorStateClass.MEASUREMENT,
}
HUMIDITY = {
    "device_class": SensorDeviceClass.HUMIDITY,
    "native_unit_of_measurement": PERCENTAGE,
    "state_class": SensorStateClass.MEASUREMENT,
}
ILLUMINANCE = {
    "device_class": SensorDeviceClass.ILLUMINANCE,
    "native_unit_of_measurement": LIGHT_LUX,
    "state_class": SensorStateClass.MEASUREMENT,
}

SENSORS: dict[str, tuple[EnOceanSensorDescription, ...]] = {
    "window_handle": (
        EnOceanSensorDescription(
            key="handle",
            translation_key="handle",
            device_class=SensorDeviceClass.ENUM,
            options=["closed", "open", "tilted"],
            value_fn=_handle,
        ),
    ),
    "meter": (
        EnOceanSensorDescription(
            key="energy",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=_meter(0, 0),
        ),
        EnOceanSensorDescription(
            key="energy_tariff_1",
            translation_key="energy_tariff",
            translation_placeholders={"tariff": "1"},
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=False,
            value_fn=_meter(0, 1),
        ),
        EnOceanSensorDescription(
            key="power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_meter(1, 0),
        ),
    ),
    "temp_humidity": (
        EnOceanSensorDescription(key="temperature", **TEMPERATURE, value_fn=_field("TMP")),
        EnOceanSensorDescription(key="humidity", **HUMIDITY, value_fn=_field("HUM")),
    ),
    "fbh": (
        EnOceanSensorDescription(key="illuminance", **ILLUMINANCE, value_fn=_field("ILL", 0)),
        EnOceanSensorDescription(
            key="voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=_field("SVC", 2),
        ),
    ),
    "co2": (
        EnOceanSensorDescription(
            key="co2",
            device_class=SensorDeviceClass.CO2,
            native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_field("Conc", 0),
        ),
        EnOceanSensorDescription(key="temperature", **TEMPERATURE, value_fn=_field("TMP")),
        EnOceanSensorDescription(key="humidity", **HUMIDITY, value_fn=_field("HUM")),
    ),
    "room_controller": (
        EnOceanSensorDescription(key="temperature", **TEMPERATURE, value_fn=_field("temperature")),
        EnOceanSensorDescription(
            key="setpoint",
            translation_key="setpoint",
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            value_fn=_field("setpoint"),
        ),
        EnOceanSensorDescription(
            key="night_setback",
            translation_key="night_setback",
            native_unit_of_measurement="K",
            value_fn=_field("night_setback", 0),
        ),
    ),
    "weather": (
        EnOceanSensorDescription(
            key="dawn", translation_key="dawn", **ILLUMINANCE, value_fn=_field("DWS", 0)
        ),
        EnOceanSensorDescription(key="temperature", **TEMPERATURE, value_fn=_field("TMP")),
        EnOceanSensorDescription(
            key="wind_speed",
            device_class=SensorDeviceClass.WIND_SPEED,
            native_unit_of_measurement=UnitOfSpeed.METERS_PER_SECOND,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_field("WND"),
        ),
        *(
            EnOceanSensorDescription(
                key=f"sun_{side}",
                translation_key=f"sun_{side}",
                **ILLUMINANCE,
                value_fn=(lambda f: lambda v: round(v[f] * 1000) if f in v else None)(field),
            )
            for side, field in (("west", "SNW"), ("south", "SNS"), ("east", "SNE"))
        ),
    ),
}


SENSORS["heating_actuator"] = (
    EnOceanSensorDescription(
        key="heating_mode",
        translation_key="heating_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["normal", "night_setback", "setback", "off"],
        value_fn=lambda v: v.get("mode"),
    ),
)
SENSORS["psc"] = tuple(d for d in SENSORS["meter"] if d.key != "energy_tariff_1")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if Platform.SENSOR not in device.model.platforms:
            continue
        async_add_entities(
            [EnOceanSensor(device, d) for d in SENSORS.get(device.model.id, ())],
            config_subentry_id=subentry_id,
        )


class EnOceanSensor(EnOceanEntity, RestoreSensor):
    entity_description: EnOceanSensorDescription

    def __init__(self, device: EnOceanDevice, description: EnOceanSensorDescription) -> None:
        super().__init__(device, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value

    def _apply(self, values: dict[str, Any]) -> bool:
        value = self.entity_description.value_fn(values)
        if value is None or value == self._attr_native_value:
            return False
        self._attr_native_value = value
        return True
