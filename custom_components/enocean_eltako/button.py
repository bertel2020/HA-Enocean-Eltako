"""Teach-in buttons: one per sender profile of an actuator."""

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
        buttons: list[ButtonEntity] = [TeachInButton(device, p) for p in device.senders]
        if device.model.id == "cover":
            buttons.append(CalibrateButton(device))
        async_add_entities(buttons, config_subentry_id=subentry_id)


class TeachInButton(EnOceanEntity, ButtonEntity):
    """Sends the teach-in telegram of one sender profile (4BS teach-in or rocker press)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: EnOceanDevice, profile: str) -> None:
        super().__init__(device, f"teach_in_{profile}")
        self._profile = profile
        self._attr_translation_key = f"teach_in_{profile}"

    async def async_press(self) -> None:
        self._device.teach_in(self._profile)

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class CalibrateButton(EnOceanEntity, ButtonEntity):
    """I6: drive the cover to the nearer end position and back."""

    _attr_translation_key = "calibrate"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "calibrate")

    async def async_press(self) -> None:
        if self._device.cover_entity is not None:
            self.hass.async_create_task(self._device.cover_entity.async_calibrate())

    def _apply(self, values: dict[str, Any]) -> bool:
        return False
