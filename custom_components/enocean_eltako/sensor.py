"""Sensors from decoded telegram values."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, TypedDict

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
    UnitOfDensity,
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
from .catalog import (
    CUSTOM,
    GENERIC_EEP,
    GROUP_VIRTUAL,
    OPT_FIELDS,
    custom_definition,
    custom_key,
    generic_fields,
)
from .const import CONF_DEVICE, CONF_MODEL
from .custom_devices import CustomDevice
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .entity_ids import gateway_prefix
from .gateway_entity import GATEWAY_SENSORS, GatewaySensor
from .protocol.ids import format_id
from .protocol.models import MODELS
from .virtual import CONTACT_CLOSED, CONTACT_OPEN, MOTION, NO_MOTION

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

HANDLE_POSITIONS = {0xF0: "closed", 0xC0: "open", 0xE0: "open", 0xD0: "tilted"}


@dataclass(frozen=True, kw_only=True)
class EnOceanSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    monotonic: bool = False  # meter readings: a step backwards is dropped, not a reset
    # a second source of the same value (e.g. D2-01 next to A5-12-01); used only as long as
    # value_fn never produced a value, so two sources do not fight over the state
    fallback_value_fn: Callable[[dict[str, Any]], Any] | None = None


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


# D2-01 measurement (command 7): unit UN 0 Ws, 1 Wh, 2 kWh, 3 W, 4 kW, value MV
_VLD_TO_KWH = {0: 1 / 3_600_000, 1: 1 / 1000, 2: 1.0}
_VLD_TO_WATT = {3: 1.0, 4: 1000.0}


def _vld_energy(values: dict[str, Any]) -> Any:
    factor = _VLD_TO_KWH.get(values.get("UN", -1)) if values.get("CMD") == 7 else None
    return None if factor is None else round(values["MV"] * factor, 3)


def _vld_power(values: dict[str, Any]) -> Any:
    factor = _VLD_TO_WATT.get(values.get("UN", -1)) if values.get("CMD") == 7 else None
    return None if factor is None else round(values["MV"] * factor, 1)


def _any_tariff_power(values: dict[str, Any]) -> Any:
    return round(values["MR"], 1) if values.get("DT") == 1 else None


def _handle(values: dict[str, Any]) -> Any:
    return HANDLE_POSITIONS.get(values.get("WIN", -1))


class _Preset(TypedDict):
    """Keyword arguments shared by many sensor descriptions (typed for **unpacking)."""

    device_class: SensorDeviceClass
    native_unit_of_measurement: str
    state_class: SensorStateClass


TEMPERATURE: _Preset = {
    "device_class": SensorDeviceClass.TEMPERATURE,
    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
    "state_class": SensorStateClass.MEASUREMENT,
}
HUMIDITY: _Preset = {
    "device_class": SensorDeviceClass.HUMIDITY,
    "native_unit_of_measurement": PERCENTAGE,
    "state_class": SensorStateClass.MEASUREMENT,
}
ILLUMINANCE: _Preset = {
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


# A5-09-05/0C scale multiplier SCM: 0 = x0.01, 1 = x0.1, 2 = x1, 3 = x10
VOC_SCALE = {0: 0.01, 1: 0.1, 2: 1.0, 3: 10.0}


def _voc(unit: int) -> Callable[[dict[str, Any]], float | None]:
    """VOC concentration in ppb (unit 0) or ug/m3 (unit 1, A5-09-0C only)."""

    def get(values: dict[str, Any]) -> float | None:
        if "Conc" not in values or values.get("Unit", 0) != unit:
            return None
        return round(float(values["Conc"]) * VOC_SCALE.get(values.get("SCM", 2), 1.0), 2)

    return get


VOC_PPB = EnOceanSensorDescription(
    key="voc",
    device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
    native_unit_of_measurement=UnitOfRatio.PARTS_PER_BILLION,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=_voc(0),
)
SENSORS["voc"] = (VOC_PPB,)
SENSORS["tvoc"] = (
    VOC_PPB,
    EnOceanSensorDescription(
        key="voc_mass",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        native_unit_of_measurement=UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_voc(1),
    ),
)


def _d2_14(
    keys: tuple[str, str], limit: int, scale: Callable[[int], float]
) -> Callable[[dict[str, Any]], float | None]:
    """D2-14-40/41 value (the two profiles name their fields differently); None if invalid."""

    def get(values: dict[str, Any]) -> float | None:
        raw = next((values[k] for k in keys if k in values), None)
        return None if raw is None or raw > limit else round(scale(raw), 2)

    return get


def _acceleration(axis: str) -> EnOceanSensorDescription:
    return EnOceanSensorDescription(
        key=f"acceleration_{axis.lower()}",
        translation_key=f"acceleration_{axis.lower()}",
        native_unit_of_measurement="g",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_d2_14((f"ACC_{axis}", f"Acceleration {axis}"), 1000, lambda r: r / 200 - 2.5),
    )


SENSORS["multisensor"] = SENSORS["multisensor_contact"] = (
    EnOceanSensorDescription(
        key="temperature",
        **TEMPERATURE,
        value_fn=_d2_14(("TMP10", "temperature"), 1000, lambda r: r / 10 - 40),
    ),
    EnOceanSensorDescription(
        key="humidity", **HUMIDITY, value_fn=_d2_14(("HUM", "humidity"), 200, lambda r: r / 2)
    ),
    EnOceanSensorDescription(
        key="illuminance",
        **ILLUMINANCE,
        value_fn=_d2_14(("ILL", "Illumination"), 100000, float),
    ),
    *(_acceleration(axis) for axis in ("X", "Y", "Z")),
)
SENSORS["digital_inputs"] = (
    EnOceanSensorDescription(key="temperature", **TEMPERATURE, value_fn=_field("TMP")),
)

SENSORS["gas_meter"] = _volume_sensors(SensorDeviceClass.GAS)
SENSORS["water_meter"] = _volume_sensors(SensorDeviceClass.WATER)


def _psc_sensor(description: EnOceanSensorDescription) -> EnOceanSensorDescription:
    """The PSC reports energy and power twice: D2-01 (full resolution, ESP3 gateways only: ESP2
    cuts the telegram) and A5-12-01. Energy comes preferably from D2-01 (every few seconds,
    in Wh; the A5 counter only every 10 minutes), power from A5-12-01 (every ~3 s)."""
    if description.key == "energy":
        return replace(description, value_fn=_vld_energy, fallback_value_fn=description.value_fn)
    return replace(description, fallback_value_fn=_vld_power)


SENSORS["psc"] = tuple(
    _psc_sensor(d) for d in SENSORS["meter"] if d.key not in ("energy_tariff_1", "active_tariff")
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


def custom_descriptions(definition: CustomDevice) -> tuple[EnOceanSensorDescription, ...]:
    """I8: the sensors of the user's definition; unit from the EEP unless given."""
    descriptions = []
    for sensor in definition.sensors:
        f = sensor.field
        scaled = f.scale is not None or f.scale_ref is not None
        unit = sensor.unit or (None if f.unit in _NO_UNIT else f.unit)
        state_class = sensor.state_class or (SensorStateClass.MEASUREMENT if scaled else None)
        descriptions.append(
            EnOceanSensorDescription(
                key=custom_key(f.shortcut),
                name=sensor.name,
                device_class=SensorDeviceClass(sensor.device_class)
                if sensor.device_class
                else None,
                native_unit_of_measurement=unit,
                state_class=SensorStateClass(state_class) if state_class else None,
                value_fn=_field(f.shortcut, 2 if scaled else None),
            )
        )
    return tuple(descriptions)


def model_descriptions(device: EnOceanDevice) -> tuple[EnOceanSensorDescription, ...]:
    """Sensor descriptions of a device: by kind, by EEP, or by the user's definition."""
    model = device.model
    if model.kind == CUSTOM and (definition := custom_definition(device.options)) is not None:
        return custom_descriptions(definition)
    if model.kind == GENERIC_EEP and model.receive is not None:
        descriptions = generic_descriptions(model.receive.eep)
        if (chosen := device.options.get(OPT_FIELDS)) is not None:
            descriptions = tuple(d for d in descriptions if d.key in chosen)
        return descriptions
    return SENSORS.get(model.kind, ())


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    bus = MODELS[entry.data[CONF_MODEL]].bus
    tcp = entry.data[CONF_DEVICE].get("type") == "tcp"
    prefix = gateway_prefix(entry.options) is not None
    async_add_entities(
        [
            GatewaySensor(entry, d)
            for d in GATEWAY_SENSORS
            if (bus or not d.bus_only) and (tcp or not d.tcp_only) and (prefix or not d.prefix_only)
        ]
    )
    for subentry_id, device in entry.runtime_data.devices.items():
        # E5/I7 diagnostics for every device
        if device.model.group == GROUP_VIRTUAL:  # sends only: no radio statistics
            virtual: list[SensorEntity] = [SenderIdSensor(device, p) for p in device.senders]
            if device.virtual is not None:
                virtual += [VirtualValueSensor(device), VirtualLastSentSensor(device)]
            async_add_entities(virtual, config_subentry_id=subentry_id)
            continue
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
        if device.model.kind in (GENERIC_EEP, CUSTOM):
            diagnostics.append(RawDataSensor(device))
        async_add_entities(diagnostics, config_subentry_id=subentry_id)
        if Platform.SENSOR not in device.model.platforms:
            continue
        descriptions = model_descriptions(device)
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
        self._primary_seen = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value

    def _apply(self, values: dict[str, Any]) -> bool:
        value = self.entity_description.value_fn(values)
        if value is not None:
            self._primary_seen = True
        elif self.entity_description.fallback_value_fn is not None and not self._primary_seen:
            value = self.entity_description.fallback_value_fn(values)
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


class _WrittenOnChange(SensorEntity):
    """Values read from elsewhere (statistics, what was sent): written only when they change."""

    _written: tuple[Any, Any] | None = None

    @callback
    def _write_if_changed(self) -> None:
        current = (self.native_value, self.extra_state_attributes)
        if current != self._written:
            self._written = current
            self.async_write_ha_state()


class _StatsSensor(EnOceanEntity, _WrittenOnChange):
    """Diagnostic sensor fed from the device's radio statistics, not from decoded values."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @callback
    def _availability_changed(self) -> None:
        self._write_if_changed()

    @property
    def available(self) -> bool:
        return True

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class RawDataSensor(_StatsSensor):
    """I8: the last telegram's data bytes, to check or extend a definition."""

    _attr_translation_key = "raw_data"
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "raw_data")

    @property
    def native_value(self) -> str | None:
        telegram = self._device.last_telegram
        return telegram.data.hex(" ").upper() if telegram is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        telegram = self._device.last_telegram
        return {"rorg": f"{telegram.rorg:02X}" if telegram is not None else None}


class EnOceanIdSensor(EnOceanEntity, SensorEntity):
    """The device's EnOcean ID as a value for templates and automations."""

    _attr_translation_key = "enocean_id"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "enocean_id")
        self._attr_native_value = format_id(device.device_id)
        self._attr_extra_state_attributes = {"decimal": device.device_id}

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
        self._attr_extra_state_attributes = {"decimal": device.senders[profile]}

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


class _VirtualSensorEntity(EnOceanEntity, _WrittenOnChange):
    """I9: what a virtual sensor sent last."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._device.virtual.add_listener(self._write_if_changed))

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class VirtualValueSensor(_VirtualSensorEntity):
    _attr_translation_key = "sent_value"

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "sent_value")
        if device.model.kind == "virtual_temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif device.model.kind == "virtual_brightness":
            self._attr_device_class = SensorDeviceClass.ILLUMINANCE
            self._attr_native_unit_of_measurement = LIGHT_LUX
        elif device.model.kind == "virtual_weather":
            pass  # a summary text: "21.5 °C, 3.2 m/s, dry, 12000 lx"
        else:
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_translation_key = f"sent_{device.model.kind.removeprefix('virtual_')}"
            self._attr_options = (
                [CONTACT_OPEN, CONTACT_CLOSED]
                if device.model.kind == "virtual_contact"
                else [MOTION, NO_MOTION]
            )

    @property
    def native_value(self) -> Any:
        return self._device.virtual.sent_value


class VirtualLastSentSensor(_VirtualSensorEntity):
    _attr_translation_key = "last_sent"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "last_sent")

    @property
    def native_value(self) -> datetime | None:
        last = self._device.virtual.last_sent
        return dt_util.utc_from_timestamp(last) if last is not None else None
