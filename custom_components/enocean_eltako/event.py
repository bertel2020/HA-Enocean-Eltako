"""Rocker switches as event entities (pressed button or release)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EnOceanEltakoConfigEntry
from .device import EnOceanDevice
from .entity import EnOceanEntity

PARALLEL_UPDATES = 0

# F6-02-01 rocker action R1/R2: 0 = A1 (AI), 1 = A0 (AO), 2 = B1 (BI), 3 = B0 (BO)
BUTTONS = ("a1", "a0", "b1", "b0")
EVENT_TYPES = [*(f"{b}_pressed" for b in BUTTONS), "released"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if Platform.EVENT in device.model.platforms:
            async_add_entities([EnOceanRocker(device)], config_subentry_id=subentry_id)


class EnOceanRocker(EnOceanEntity, EventEntity):
    _attr_translation_key = "rocker"
    _attr_event_types = EVENT_TYPES

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "rocker")

    def _apply(self, values: dict[str, Any]) -> bool:
        if values.get("EB") == 1:
            buttons = [BUTTONS[values["R1"]]]
            if values.get("SA") == 1:
                buttons.append(BUTTONS[values["R2"]])
            self._trigger_event(f"{buttons[0]}_pressed", {"buttons": buttons})
        elif values.get("EB") == 0:
            self._trigger_event("released")
        else:
            return False
        return True  # every press is an event, even the same button again
