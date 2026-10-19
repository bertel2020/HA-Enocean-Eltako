"""Base entity: one per device function, updated from decoded telegram values."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

from .catalog import OPT_UNAVAILABLE_WHEN_SILENT
from .device import EnOceanDevice


class EnOceanEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: EnOceanDevice, key: str) -> None:
        self._device = device
        self._attr_unique_id = f"{device.unique_prefix}_1_{key}"
        self._attr_device_info = device.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._device.add_listener(self._handle_values))
        self._was_available = self.available
        self.async_on_remove(self._device.add_stats_listener(self._availability_changed))

    @callback
    def _availability_changed(self) -> None:
        if self.available != self._was_available:
            self._was_available = self.available
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """E5 option: unavailable while the device is silent."""
        return not (self._device.silent and self._device.options.get(OPT_UNAVAILABLE_WHEN_SILENT))

    @callback
    def _handle_values(self, values: dict[str, Any]) -> None:
        # write state only on a real change (cyclic repetitions are common)
        if self._apply(values):
            self.async_write_ha_state()

    def _apply(self, values: dict[str, Any]) -> bool:
        """Update attributes from values; True when the state changed."""
        raise NotImplementedError
