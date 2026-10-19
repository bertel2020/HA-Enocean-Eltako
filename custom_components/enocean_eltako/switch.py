"""Switches: switching actuators configured as switch (sockets, convectors, releases)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import OPT_PLATFORM
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .light import switch_actuator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.model.id == "switch" and device.options.get(OPT_PLATFORM) == Platform.SWITCH:
            async_add_entities([EnOceanSwitch(device)], config_subentry_id=subentry_id)


class EnOceanSwitch(EnOceanEntity, SwitchEntity, RestoreEntity):
    _attr_name = None

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "switch")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        switch_actuator(self._device, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        switch_actuator(self._device, False)

    def _apply(self, values: dict[str, Any]) -> bool:
        if "on" not in values or values["on"] == self._attr_is_on:
            return False
        self._attr_is_on = values["on"]
        return True
