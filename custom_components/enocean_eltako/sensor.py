"""Sensors from decoded telegram values."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    Platform,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfRatio,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import EnOceanEltakoConfigEntry
from .catalog import GENERIC_EEP, OPT_FIELDS, generic_fields
from .const import CONF_MODEL
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .gateway_entity import GATEWAY_SENSORS, GatewaySensor
from .protocol.ids import format_id
from .protocol.models import MODELS

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

HANDLE_POSITIONS = {0xF0: "closed", 0xC0: "open", 0xE0: "open", 0xD0: "tilted"}


@dataclass(frozen=True, kw_only=True)
class EnOceanSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    monotonic: bool = False  # meter readings: a step backwards is dropped, not a reset


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


def _any_tariff_power(values: dict[str, Any]) -> Any:
    return round(values["MR"], 1) if values.get("DT") == 1 else None


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
            monotonic=True,
            value_fn=_meter(0, 0),
        ),
        EnOceanSensorDescription(
            key="energy_tariff_1",
            translation_key="energy_night",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=False,
            monotonic=True,
            value_fn=_meter(0, 1),
        ),
        EnOceanSensorDescription(
            key="power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=_any_tariff_power,
        ),
        EnOceanSensorDescription(
            key="active_tariff",
            translation_key="active_tariff",
            entity_registry_enabled_default=False,
            value_fn=lambda v: v.get("TI") if v.get("DT") == 1 else None,
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
            native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
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


def _volume_sensors(device_class: SensorDeviceClass) -> tuple[EnOceanSensorDescription, ...]:
    """A5-12-02 gas / A5-12-03 water: counter in m3 (DT 0), flow in l/s (DT 1)."""
    return (
        EnOceanSensorDescription(
            key="volume",
            device_class=device_class,
            native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
            state_class=SensorStateClass.TOTAL_INCREASING,
            monotonic=True,
            value_fn=_meter(0, 0),
        ),
        EnOceanSensorDescription(
            key="flow",
            device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
            native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_SECOND,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda v: round(v["MR"], 3) if v.get("DT") == 1 else None,
        ),
    )


SENSORS["gas_meter"] = _volume_sensors(SensorDeviceClass.GAS)
SENSORS["water_meter"] = _volume_sensors(SensorDeviceClass.WATER)

SENSORS["psc"] = tuple(
    d for d in SENSORS["meter"] if d.key not in ("energy_tariff_1", "active_tariff")
)


_NO_UNIT = {"N/A", "1"}


def generic_descriptions(eep: str) -> tuple[EnOceanSensorDescription, ...]:
    """One sensor per field of a standard profile, named and unitized as in the EEP."""
    descriptions = []
    for key, f in generic_fields(eep):
        scaled = f.scale is not None or f.scale_ref is not None
        descriptions.append(
            EnOceanSensorDescription(
                key=key,
                name=f.name,
                native_unit_of_measurement=None if f.unit in _NO_UNIT else f.unit,
                state_class=SensorStateClass.MEASUREMENT if scaled else None,
                value_fn=_field(f.shortcut, 2 if scaled else None),
            )
        )
    return tuple(descriptions)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    bus = MODELS[entry.data[CONF_MODEL]].bus
    async_add_entities([GatewaySensor(entry, d) for d in GATEWAY_SENSORS if bus or not d.bus_only])
    for subentry_id, device in entry.runtime_data.devices.items():
        # E5/I7 diagnostics for every device
        diagnostics: list[SensorEntity] = [
            LastSeenSensor(device),
            RssiSensor(device),
            EnOceanIdSensor(device),
            *(SenderIdSensor(device, profile) for profile in device.senders),
        ]
        if device.senders:
            diagnostics.append(CommandSuccessSensor(device))
        if device.model.kind == "cover":
            diagnostics.append(PositionAccuracySensor(device))
        async_add_entities(diagnostics, config_subentry_id=subentry_id)
        if Platform.SENSOR not in device.model.platforms:
            continue
        descriptions = SENSORS.get(device.model.kind, ())
        if device.model.kind == GENERIC_EEP and device.model.receive is not None:
            descriptions = generic_descriptions(device.model.receive.eep)
            if (chosen := device.options.get(OPT_FIELDS)) is not None:
                descriptions = tuple(d for d in descriptions if d.key in chosen)
        entities: list[SensorEntity] = [EnOceanSensor(device, d) for d in descriptions]
        if device.model.kind == "meter":
            entities.append(MeterTotalSensor(device))
        if (
            device.model.receive is not None
            and device.model.receive.variant == "eltako"
            and (device.model.receive.eep.startswith("A5-12-"))
        ):
            entities.append(MeterSerialSensor(device))
        async_add_entities(entities, config_subentry_id=subentry_id)


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
        if self.entity_description.monotonic and _decreases(self._attr_native_value, value):
            _LOGGER.warning(
                "%s: meter reading %s below %s dropped",
                self.entity_id,
                value,
                self._attr_native_value,
            )
            return False
        self._attr_native_value = value
        return True


def _decreases(current: Any, new: Any) -> bool:
    try:
        return current is not None and float(new) < float(current)
    except (TypeError, ValueError):
        return False


class MeterSerialSensor(EnOceanEntity, RestoreSensor):
    """E7: serial number of Eltako meters, sent in two telegrams (S0 S1, then S2 S3)."""

    _attr_translation_key = "serial_number"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "serial_number")
        self._parts: dict[int, bytes] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value

    def _apply(self, values: dict[str, Any]) -> bool:
        if "serial_part" not in values:
            return False
        self._parts[values["serial_part"]] = values["serial_bytes"]
        if len(self._parts) < 2:
            return False
        serial = (self._parts[0] + self._parts[1]).hex(" ").upper()
        if serial == self._attr_native_value:
            return False
        self._attr_native_value = serial
        return True


class MeterTotalSensor(EnOceanEntity, RestoreSensor):
    """E7: sum of both tariffs, for meters with a day and a night tariff."""

    _attr_translation_key = "energy_total"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "energy_total")
        self._tariffs: dict[int, float] = {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._tariffs = {
                int(k): float(v) for k, v in last.attributes.get("tariffs", {}).items()
            }
            if self._tariffs:
                self._attr_native_value = round(sum(self._tariffs.values()), 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"tariffs": {str(k): v for k, v in self._tariffs.items()}}

    def _apply(self, values: dict[str, Any]) -> bool:
        if values.get("DT") != 0 or values.get("TI") not in (0, 1):
            return False
        tariff, reading = values["TI"], round(values["MR"], 3)
        if reading < self._tariffs.get(tariff, 0):
            return False
        self._tariffs[tariff] = reading
        total = round(sum(self._tariffs.values()), 3)
        if total == self._attr_native_value:
            return False
        self._attr_native_value = total
        return True


class _StatsSensor(EnOceanEntity, SensorEntity):
    """Diagnostic sensor fed from the device's radio statistics, not from decoded values."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @callback
    def _availability_changed(self) -> None:
        self.async_write_ha_state()  # every statistics change is a new state

    @property
    def available(self) -> bool:
        return True

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class EnOceanIdSensor(EnOceanEntity, SensorEntity):
    """The device's EnOcean ID as a value for templates and automations."""

    _attr_translation_key = "enocean_id"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "enocean_id")
        self._attr_native_value = format_id(device.device_id)

    @property
    def available(self) -> bool:
        return True

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class SenderIdSensor(EnOceanEntity, SensorEntity):
    """Sender ID Home Assistant commands the device with, one per configured profile."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: EnOceanDevice, profile: str) -> None:
        super().__init__(device, f"sender_id_{profile}")
        self._attr_translation_key = f"sender_id_{profile}"
        self._attr_native_value = format_id(device.senders[profile])

    @property
    def available(self) -> bool:
        return True

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class LastSeenSensor(_StatsSensor, RestoreEntity):
    _attr_translation_key = "last_seen"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    # changes with every telegram and would flood the logbook; silence is reported by the
    # repair issue and the "unavailable when silent" option instead
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "last_seen")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and self._device.stats.last_seen is None:
            restored = dt_util.parse_datetime(last.state)
            if restored is not None:
                self._device.stats.last_seen = restored.timestamp()

    @property
    def native_value(self) -> datetime | None:
        seen = self._device.stats.last_seen
        return dt_util.utc_from_timestamp(seen) if seen is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        gateway = self.hass.config_entries.async_get_entry(self._device.stats.gateway or "")
        return {
            "gateway": gateway.title if gateway else None,
            "telegrams": self._device.stats.telegrams,
            "silent": self._device.silent,
        }


class RssiSensor(_StatsSensor):
    _attr_translation_key = "rssi"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "rssi")

    @property
    def native_value(self) -> int | None:
        return self._device.stats.rssi

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stats = self._device.stats
        return {"min": stats.rssi_min, "max": stats.rssi_max, "repeat_count": stats.repeat_count}


class CommandSuccessSensor(_StatsSensor):
    _attr_translation_key = "command_success"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "command_success")

    @property
    def native_value(self) -> float | None:
        return self._device.stats.success_rate

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        stats = self._device.stats
        return {"commands": stats.commands, "confirmed": stats.confirmed}


class PositionAccuracySensor(_StatsSensor):
    """I6: inaccuracy of the tracked cover position in percentage points."""

    _attr_translation_key = "position_accuracy"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "position_accuracy")

    @property
    def native_value(self) -> float | None:
        cover = self._device.cover_entity
        return round(cover.position.inaccuracy, 1) if cover is not None else None
