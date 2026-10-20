"""I8: device definitions of the user, read from /config/enocean_eltako/custom_devices.yaml.

A definition names a receive-only device on a standard EEP and maps the profile's fields to
sensors and binary sensors with names, device classes and units of the user's choice:

    devices:
      - id: acme_climate
        name: Acme room sensor
        manufacturer: Acme
        eep: A5-04-01
        interval: 600
        sensors:
          - field: TMP
            device_class: temperature
          - field: HUM
            name: Humidity
            device_class: humidity
        binary_sensors:
          - field: TSN
            name: Temperature available
            on: 1

The file is read when an entry is set up (reloading it applies changes). Errors raise a
repair issue; a device whose definition disappeared keeps working as a generic EEP device.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.yaml import load_yaml

from .const import DOMAIN
from .protocol.eep import EEPRef
from .protocol.eep.model import Field
from .protocol.eep.std.profiles import PROFILES

_LOGGER = logging.getLogger(__name__)

FILE = "enocean_eltako/custom_devices.yaml"
ISSUE_ID = "custom_devices_invalid"


@dataclass(frozen=True, slots=True)
class CustomSensor:
    field: Field
    name: str
    device_class: str | None = None
    unit: str | None = None
    state_class: str | None = None


@dataclass(frozen=True, slots=True)
class CustomBinarySensor:
    field: Field
    name: str
    device_class: str | None = None
    on: int | None = None  # value meaning "on"; None: any value but 0


@dataclass(frozen=True, slots=True)
class CustomDevice:
    id: str
    name: str
    eep: EEPRef
    manufacturer: str = "EnOcean"
    interval: int | None = None
    sensors: tuple[CustomSensor, ...] = ()
    binary_sensors: tuple[CustomBinarySensor, ...] = ()


# the definitions read last; the catalog resolves "custom" subentries against them
DEFINITIONS: dict[str, CustomDevice] = {}


def _fields(eep: str) -> dict[str, Field]:
    fields: dict[str, Field] = {}
    for case in PROFILES[eep].cases:
        for f in case.fields:
            fields.setdefault(f.shortcut, f)
    return fields


def _text(item: dict[str, Any], key: str, where: str, errors: list[str]) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: {key} must be a text")
        return None
    return value.strip()


def _choice(
    item: dict[str, Any], key: str, allowed: set[str], where: str, errors: list[str]
) -> str | None:
    value = _text(item, key, where, errors)
    if value is not None and value not in allowed:
        errors.append(f"{where}: unknown {key} '{value}'")
        return None
    return value


def _entities(
    raw: Any, fields: dict[str, Field], where: str, errors: list[str]
) -> list[tuple[dict[str, Any], Field, str]]:
    """(item, field, place) of every valid sensor entry of a definition."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        errors.append(f"{where}: must be a list")
        return []
    found = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        place = f"{where}[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("field"), str):
            errors.append(f"{place}: needs a field")
            continue
        if (field := fields.get(item["field"])) is None:
            errors.append(f"{place}: the profile has no field '{item['field']}'")
            continue
        if field.shortcut in seen:
            errors.append(f"{place}: field '{field.shortcut}' used twice")
            continue
        seen.add(field.shortcut)
        found.append((item, field, place))
    return found


def parse(raw: Any) -> tuple[dict[str, CustomDevice], list[str]]:
    """Valid definitions and a message per error; a broken definition is left out."""
    errors: list[str] = []
    if raw is None:
        return {}, errors
    if not isinstance(raw, dict) or not isinstance(raw.get("devices"), list):
        return {}, ["the file needs a list 'devices'"]
    sensor_classes = {c.value for c in SensorDeviceClass}
    state_classes = {c.value for c in SensorStateClass}
    binary_classes = {c.value for c in BinarySensorDeviceClass}
    definitions: dict[str, CustomDevice] = {}
    for index, item in enumerate(raw["devices"]):
        where = f"devices[{index}]"
        before = len(errors)
        if not isinstance(item, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        device_id = _text(item, "id", where, errors)
        name = _text(item, "name", where, errors)
        eep = _text(item, "eep", where, errors)
        if device_id is None or name is None or eep is None:
            errors.append(f"{where}: id, name and eep are required")
            continue
        where = f"{device_id}"
        if device_id in definitions:
            errors.append(f"{where}: id used twice")
            continue
        eep = eep.upper()
        if eep not in PROFILES:
            errors.append(f"{where}: unknown EEP '{eep}'")
            continue
        fields = _fields(eep)
        interval = item.get("interval")
        if interval is not None and (not isinstance(interval, int) or interval <= 0):
            errors.append(f"{where}: interval must be a number of seconds")
            interval = None
        sensors = []
        for entry, field, place in _entities(item.get("sensors"), fields, where, errors):
            sensors.append(
                CustomSensor(
                    field,
                    _text(entry, "name", place, errors) or field.name,
                    _choice(entry, "device_class", sensor_classes, place, errors),
                    _text(entry, "unit", place, errors),
                    _choice(entry, "state_class", state_classes, place, errors),
                )
            )
        binary_sensors = []
        for entry, field, place in _entities(item.get("binary_sensors"), fields, where, errors):
            on = entry.get("on")
            if on is not None and not isinstance(on, int):
                errors.append(f"{place}: on must be a number")
                on = None
            binary_sensors.append(
                CustomBinarySensor(
                    field,
                    _text(entry, "name", place, errors) or field.name,
                    _choice(entry, "device_class", binary_classes, place, errors),
                    on,
                )
            )
        if not sensors and not binary_sensors and len(errors) == before:
            errors.append(f"{where}: needs sensors or binary_sensors")
        if len(errors) > before:
            continue
        definitions[device_id] = CustomDevice(
            device_id,
            name,
            EEPRef(eep, "std"),
            _text(item, "manufacturer", where, errors) or "EnOcean",
            interval,
            tuple(sensors),
            tuple(binary_sensors),
        )
    return definitions, errors


def _read(path: Path) -> Any:
    if not path.exists():
        return None
    return load_yaml(path)


async def async_load(hass: HomeAssistant) -> dict[str, CustomDevice]:
    """Read the file, replace DEFINITIONS, raise or clear the repair issue."""
    path = Path(hass.config.path(FILE))
    try:
        raw = await hass.async_add_executor_job(_read, path)
    except HomeAssistantError as err:
        definitions: dict[str, CustomDevice] = {}
        errors = [str(err)]
    else:
        definitions, errors = parse(raw)
    DEFINITIONS.clear()
    DEFINITIONS.update(definitions)
    if errors:
        _LOGGER.warning("Errors in %s: %s", path, "; ".join(errors))
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ID,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_ID,
            translation_placeholders={"path": str(path), "errors": "\n".join(errors)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_ID)
    return definitions
