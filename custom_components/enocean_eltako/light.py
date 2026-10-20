"""Lights: switching actuators (on/off) and dimmers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import (
    CENTRAL,
    OPT_CHANNEL,
    OPT_INVERT,
    OPT_PLATFORM,
    ROCKER,
)
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .protocol.eep import vld
from .protocol.eep.eltako import switching

PARALLEL_UPDATES = 0


def inverted(device: EnOceanDevice) -> bool:
    """Reversed relay logic (e.g. a release): on means the relay is off, both ways."""
    return bool(device.options.get(OPT_INVERT))


def switch_actuator(device: EnOceanDevice, on: bool) -> None:
    """A profile with an on/off command when configured, otherwise the rocker's buttons."""
    on = on != inverted(device)
    for profile_id in device.senders:
        profile = device.model.sender_profile(profile_id)
        if profile.switch_fn is not None:
            device.send(profile.switch_fn(on), profile=profile_id, key="switch")
            return
    device.press(ROCKER.id, device.rocker_button(on))


def on_state(values: dict[str, Any]) -> bool | None:
    """On/off from an Eltako status ("on") or a D2-01 actuator status response (OV)."""
    if "on" in values:
        return bool(values["on"])
    if values.get("CMD") == 4 and "OV" in values:
        return bool(values["OV"] > 0)
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.model.kind == "dimmer":
            async_add_entities([EnOceanDimmer(device)], config_subentry_id=subentry_id)
        elif device.model.kind == "vld_switch" and (
            device.options.get(OPT_PLATFORM, Platform.LIGHT) == Platform.LIGHT
        ):
            async_add_entities([VldLight(device)], config_subentry_id=subentry_id)
        elif (
            device.model.kind == "switch"
            and device.options.get(OPT_PLATFORM, Platform.LIGHT) == Platform.LIGHT
        ) or (device.model.kind == "psc" and device.options.get(OPT_PLATFORM) == Platform.LIGHT):
            async_add_entities([EnOceanSwitchLight(device)], config_subentry_id=subentry_id)


class EnOceanSwitchLight(EnOceanEntity, LightEntity, RestoreEntity):
    _attr_name = None
    _assume_until_heard = True
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "light")
        self._invert = inverted(device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"
            self._device.wall_state = self._attr_is_on  # I4: a toggling wall switch

    async def async_turn_on(self, **kwargs: Any) -> None:
        switch_actuator(self._device, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        switch_actuator(self._device, False)

    def _apply(self, values: dict[str, Any]) -> bool:
        on = on_state(values)
        if on is None or (on := on != self._invert) == self._attr_is_on:
            return False
        self._attr_is_on = on
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


class VldLight(EnOceanSwitchLight):
    """D2-01 switch or dimmer channel: output 0...100 %, status by command 4."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device)
        self._channel = int(device.options.get(OPT_CHANNEL, 0))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._attr_brightness = last.attributes.get(ATTR_BRIGHTNESS)

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS, self._attr_brightness or 255)
        percent = max(1, round(brightness * 100 / 255))
        self._device.send(vld.encode_set_output(self._channel, percent), key="switch")

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._device.send(vld.encode_set_output(self._channel, 0), key="switch")

    def _apply(self, values: dict[str, Any]) -> bool:
        output = vld.switch_status(values, self._channel)
        if output is None:
            return False
        on = output > 0
        brightness = round(output * 255 / 100) if on else self._attr_brightness
        if (on, brightness) == (self._attr_is_on, self._attr_brightness):
            return False
        self._attr_is_on, self._attr_brightness = on, brightness
        return True
