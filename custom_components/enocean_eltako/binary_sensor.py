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
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import (
    CUSTOM,
    OPT_DEVICE_CLASS,
    OPT_INVERT,
    OPT_OFF_BUTTON,
    OPT_ON_BUTTON,
    custom_definition,
    custom_key,
)
from .custom_devices import CustomDevice
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .gateway_entity import GatewayConnectionSensor
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
    "multisensor_contact": (
        EnOceanBinarySensorDescription(
            key="contact",
            translation_key="contact",
            # D2-14-41 contact: 0 = open, 1 = closed; "on" means open
            value_fn=lambda v: None if "Contact" not in v else v["Contact"] == 0,
        ),
    ),
    "digital_input": (
        EnOceanBinarySensorDescription(
            key="contact",
            name=None,
            # A5-30-01 input state: 0...195 contact closed, 196...255 open; "on" means open
            value_fn=lambda v: None if "IPS" not in v else v["IPS"] > 195,
        ),
        EnOceanBinarySensorDescription(
            key="battery",
            device_class=BinarySensorDeviceClass.BATTERY,
            entity_category=EntityCategory.DIAGNOSTIC,
            # supply voltage 0...120 battery low
            value_fn=lambda v: None if "SVC" not in v else v["SVC"] <= 120,
        ),
    ),
    "digital_inputs": (
        *(
            EnOceanBinarySensorDescription(
                key=f"input_{n}",
                translation_key=f"input_{n}",
                value_fn=(lambda f: lambda v: None if f not in v else v[f] == 1)(f"DI{n}"),
            )
            for n in range(4)
        ),
        EnOceanBinarySensorDescription(
            key="wake",
            translation_key="wake",
            value_fn=lambda v: None if "WA0" not in v else v["WA0"] == 1,
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
            translation_key="rain",  # no device class: "moisture" is a leak sensor to assistants
            value_fn=lambda v: None if "RAN" not in v else v["RAN"] == 1,
        ),
    ),
}


def _custom_value(shortcut: str, on: int | None) -> Callable[[dict[str, Any]], bool | None]:
    def value(values: dict[str, Any]) -> bool | None:
        if (raw := values.get(shortcut)) is None:
            return None
        return raw == on if on is not None else bool(raw)

    return value


def custom_binary_descriptions(
    definition: CustomDevice,
) -> tuple[EnOceanBinarySensorDescription, ...]:
    """I8: the binary sensors of the user's definition."""
    return tuple(
        EnOceanBinarySensorDescription(
            key=custom_key(b.field.shortcut),
            name=b.name,
            device_class=BinarySensorDeviceClass(b.device_class) if b.device_class else None,
            value_fn=_custom_value(b.field.shortcut, b.on),
        )
        for b in definition.binary_sensors
    )


def model_binary_descriptions(device: EnOceanDevice) -> tuple[EnOceanBinarySensorDescription, ...]:
    if device.model.kind == CUSTOM and (definition := custom_definition(device.options)):
        return custom_binary_descriptions(definition)
    return BINARY_SENSORS.get(device.model.kind, ())


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
    async_add_entities([GatewayConnectionSensor(entry)])
    for subentry_id, device in entry.runtime_data.devices.items():
        if Platform.BINARY_SENSOR not in device.model.platforms:
            continue
        descriptions = model_binary_descriptions(device)
        if device.model.kind == "rocker_contact":
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
        # the options describe the device's contact, not its battery or other inputs
        configurable = description.key not in ("battery",)
        self._invert = configurable and bool(device.options.get(OPT_INVERT))
        if configurable and (device_class := device.options.get(OPT_DEVICE_CLASS)):
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
