"""Automation mode of a cover (Off / Morning / Evening / Both): a switch for the user's own
automations, like the old Eltako integration's. It moves nothing by itself and is kept
across restarts."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .device import EnOceanDevice
from .entity import EnOceanEntity

AUTOMATION_MODES = ("off", "morning", "evening", "both")
DEFAULT_AUTOMATION_MODE = "both"

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.model.kind in ("cover", "vld_cover"):
            async_add_entities([CoverAutomationSelect(device)], config_subentry_id=subentry_id)


class CoverAutomationSelect(EnOceanEntity, SelectEntity, RestoreEntity):
    _attr_translation_key = "cover_automation"
    _attr_options = list(AUTOMATION_MODES)
    _attr_current_option = DEFAULT_AUTOMATION_MODE

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "automation_mode")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in self.options:
            self._attr_current_option = last.state

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()

    def _apply(self, values: dict[str, Any]) -> bool:
        return False
