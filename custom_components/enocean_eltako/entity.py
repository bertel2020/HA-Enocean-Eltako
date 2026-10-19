"""Base entity: one per device function, updated from decoded telegram values."""

from __future__ import annotations

from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity

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

    @callback
    def _handle_values(self, values: dict[str, Any]) -> None:
        # write state only on a real change (cyclic repetitions are common)
        if self._apply(values):
            self.async_write_ha_state()

    def _apply(self, values: dict[str, Any]) -> bool:
        """Update attributes from values; True when the state changed."""
        raise NotImplementedError
