"""Teach-in button per actuator: sends the teach-in telegram from the device's sender ID."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EnOceanEltakoConfigEntry
from .device import EnOceanDevice
from .entity import EnOceanEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.model.teach_in is not None and device.sender_id is not None:
            async_add_entities([TeachInButton(device)], config_subentry_id=subentry_id)


class TeachInButton(EnOceanEntity, ButtonEntity):
    _attr_translation_key = "teach_in"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "teach_in")

    async def async_press(self) -> None:
        self._device.teach_in()

    def _apply(self, values: dict[str, Any]) -> bool:
        return False
