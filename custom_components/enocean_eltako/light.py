"""Lights: switching actuators (on/off) and dimmers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import CENTRAL, OPT_PLATFORM, ROCKER, ROCKER_PRESS_DOWN, ROCKER_PRESS_UP
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .protocol.eep.eltako import switching

PARALLEL_UPDATES = 0


def switch_actuator(device: EnOceanDevice, on: bool) -> None:
    """Central command when configured, otherwise the rocker (0x70 on, 0x50 off)."""
    if device.has_sender(CENTRAL.id):
        device.send(switching.encode_switch(on), profile=CENTRAL.id, key="switch")
    else:
        device.press(ROCKER.id, ROCKER_PRESS_UP if on else ROCKER_PRESS_DOWN)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.model.id == "dimmer":
            async_add_entities([EnOceanDimmer(device)], config_subentry_id=subentry_id)
        elif (
            device.model.id == "switch"
            and device.options.get(OPT_PLATFORM, Platform.LIGHT) == Platform.LIGHT
        ):
            async_add_entities([EnOceanSwitchLight(device)], config_subentry_id=subentry_id)


class EnOceanSwitchLight(EnOceanEntity, LightEntity, RestoreEntity):
    _attr_name = None
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "light")

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


class EnOceanDimmer(EnOceanSwitchLight):
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._attr_brightness = last.attributes.get(ATTR_BRIGHTNESS)

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self._device.has_sender(CENTRAL.id):
            switch_actuator(self._device, True)  # a rocker cannot set a brightness
            return
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 255)
        percent = max(1, round(brightness * 100 / 255))
        self._device.send(switching.encode_dim(percent), profile=CENTRAL.id, key="switch")

    async def async_turn_off(self, **kwargs: Any) -> None:
        if not self._device.has_sender(CENTRAL.id):
            switch_actuator(self._device, False)
            return
        self._device.send(switching.encode_dim(0, on=False), profile=CENTRAL.id, key="switch")

    def _apply(self, values: dict[str, Any]) -> bool:
        changed = super()._apply(values)
        if "brightness" in values and values["brightness"]:
            brightness = round(values["brightness"] * 255 / 100)
            if brightness != self._attr_brightness:
                self._attr_brightness = brightness
                changed = True
        return changed
