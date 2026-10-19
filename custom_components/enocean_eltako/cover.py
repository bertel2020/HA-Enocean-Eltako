"""Shutters and blinds (FSB): G5-3F-7F status, H5-3F-7F commands with run time.

Position is tracked from the driven time. It is anchored at the end positions (status 0x70
and 0x50), whenever the driven time reaches the full travel time and on every command to
0 % or 100 %, which is always sent as a full run. No self-learning travel times.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import OPT_TIME_CLOSES, OPT_TIME_OPENS
from .const import DOMAIN
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .protocol.eep.eltako import shutter

PARALLEL_UPDATES = 0

FULL_RUN_MARGIN = 2.0  # seconds added to a full run so the end position is surely reached
DEFAULT_TRAVEL_TIME = 30.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if Platform.COVER in device.model.platforms:
            async_add_entities([EnOceanCover(device)], config_subentry_id=subentry_id)


class EnOceanCover(EnOceanEntity, CoverEntity, RestoreEntity):
    _attr_name = None
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "cover")
        self._time_opens = float(device.options.get(OPT_TIME_OPENS) or DEFAULT_TRAVEL_TIME)
        self._time_closes = float(device.options.get(OPT_TIME_CLOSES) or DEFAULT_TRAVEL_TIME)
        self._attr_is_opening = False
        self._attr_is_closing = False

    @property
    def is_closed(self) -> bool | None:
        if self._attr_current_cover_position is None:
            return None
        return self._attr_current_cover_position == 0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._attr_current_cover_position = last.attributes.get("current_position")

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._run(shutter.UP, self._time_opens + FULL_RUN_MARGIN)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._run(shutter.DOWN, self._time_closes + FULL_RUN_MARGIN)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        self._device.send(shutter.encode_command(shutter.STOP), key="move")

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        target = kwargs[ATTR_POSITION]
        if target >= 100:
            await self.async_open_cover()
            return
        if target <= 0:
            await self.async_close_cover()
            return
        current = self._attr_current_cover_position
        if current is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cover_position_unknown"
            )
        if target == current:
            return
        if target > current:
            await self._run(shutter.UP, (target - current) / 100 * self._time_opens)
        else:
            await self._run(shutter.DOWN, (current - target) / 100 * self._time_closes)

    async def _run(self, command: int, seconds: float) -> None:
        self._device.send(shutter.encode_command(command, round(seconds, 1)), key="move")

    def _apply(self, values: dict[str, Any]) -> bool:
        before = (
            self._attr_current_cover_position,
            self._attr_is_opening,
            self._attr_is_closing,
        )
        if (state := values.get("state")) is not None:
            self._attr_is_opening = state == "opening"
            self._attr_is_closing = state == "closing"
            if state == "open":
                self._attr_current_cover_position = 100
            elif state == "closed":
                self._attr_current_cover_position = 0
        elif "driven_time" in values:
            self._attr_is_opening = self._attr_is_closing = False
            up = values["direction"] == "up"
            full = self._time_opens if up else self._time_closes
            if values["driven_time"] >= full:
                self._attr_current_cover_position = 100 if up else 0
            elif self._attr_current_cover_position is not None:
                delta = values["driven_time"] / full * 100
                position = self._attr_current_cover_position + (delta if up else -delta)
                self._attr_current_cover_position = round(max(0, min(100, position)))
        return before != (
            self._attr_current_cover_position,
            self._attr_is_opening,
            self._attr_is_closing,
        )
