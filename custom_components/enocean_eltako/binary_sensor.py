"""Binary sensors: contacts, window handles, motion, rain."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import OPT_DEVICE_CLASS, OPT_INVERT, OPT_OFF_BUTTON, OPT_ON_BUTTON
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .sensor import HANDLE_POSITIONS

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class EnOceanBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None]


def _handle_open(values: dict[str, Any]) -> bool | None:
    position = HANDLE_POSITIONS.get(values.get("WIN", -1))
    return None if position is None else position != "closed"


BINARY_SENSORS: dict[str, tuple[EnOceanBinarySensorDescription, ...]] = {
    "window_handle": (
        EnOceanBinarySensorDescription(
            key="window", device_class=BinarySensorDeviceClass.WINDOW, value_fn=_handle_open
        ),
    ),
    "contact": (
        EnOceanBinarySensorDescription(
            key="contact",
            name=None,
            # CO: 0 = open, 1 = closed; "on" means open for door/window classes
            value_fn=lambda v: None if "CO" not in v else v["CO"] == 0,
        ),
    ),
    "fbh": (
        EnOceanBinarySensorDescription(
            key="motion",
            device_class=BinarySensorDeviceClass.MOTION,
            value_fn=lambda v: None if "PIRS" not in v else v["PIRS"] == 0,  # 0 = PIR on
        ),
    ),
    "weather": (
        EnOceanBinarySensorDescription(
            key="rain",
            translation_key="rain",
            device_class=BinarySensorDeviceClass.MOISTURE,
            value_fn=lambda v: None if "RAN" not in v else v["RAN"] == 1,
        ),
    ),
}


BUTTONS = ("a1", "a0", "b1", "b0")  # F6-02-01 R1 values 0...3


def _rocker_contact(on_button: str, off_button: str) -> Callable[[dict[str, Any]], bool | None]:
    """On when on_button is pressed, off when off_button is pressed (or on any release)."""

    def value(values: dict[str, Any]) -> bool | None:
        if values.get("EB") == 0:
            return False if off_button == "released" else None
        if values.get("EB") != 1:
            return None
        button = BUTTONS[values["R1"]]
        if button == on_button:
            return True
        if button == off_button:
            return False
        return None

    return value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if Platform.BINARY_SENSOR not in device.model.platforms:
            continue
        descriptions = BINARY_SENSORS.get(device.model.id, ())
        if device.model.id == "rocker_contact":
            descriptions = (
                EnOceanBinarySensorDescription(
                    key="contact",
                    name=None,
                    value_fn=_rocker_contact(
                        device.options.get(OPT_ON_BUTTON, "b0"),
                        device.options.get(OPT_OFF_BUTTON, "b1"),
                    ),
                ),
            )
        async_add_entities(
            [EnOceanBinarySensor(device, d) for d in descriptions],
            config_subentry_id=subentry_id,
        )


class EnOceanBinarySensor(EnOceanEntity, BinarySensorEntity, RestoreEntity):
    entity_description: EnOceanBinarySensorDescription

    def __init__(self, device: EnOceanDevice, description: EnOceanBinarySensorDescription) -> None:
        super().__init__(device, description.key)
        self.entity_description = description
        self._invert = bool(device.options.get(OPT_INVERT))
        if device_class := device.options.get(OPT_DEVICE_CLASS):
            self._attr_device_class = BinarySensorDeviceClass(device_class)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"

    def _apply(self, values: dict[str, Any]) -> bool:
        value = self.entity_description.value_fn(values)
        if value is None:
            return False
        value = value != self._invert
        if value == self._attr_is_on:
            return False
        self._attr_is_on = value
        return True
