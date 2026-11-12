"""Teach-in buttons (one per sender profile of an actuator), calibration, gateway reconnect;
I9 virtual sensors: send now, virtual rocker buttons."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EnOceanEltakoConfigEntry
from .catalog import OPT_BUTTONS
from .light import switch_actuator
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .gateway_entity import GatewayReconnectButton

# F6-02-01 rocker action of each button (pressed)
ROCKER_BUTTONS = {"b0": 0x70, "b1": 0x50, "a0": 0x30, "a1": 0x10}
# I9 scene button (double rocker taught in as scene button, e.g. FSB14 learn function
# 180/200): scene 1...4 = left top, left bottom, right top, right bottom
SCENE_BUTTONS = ("a0", "a1", "b0", "b1")

# kinds with a 4BS sender that the series 62 actuators (FL62, FR62, FD62, FJ62) learn
LEARN_LOCK_KINDS = ("switch", "dimmer", "cover")

PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if not entry.runtime_data.on_demand:  # on demand: the bus group connects it
        async_add_entities([GatewayReconnectButton(entry)])
    for subentry_id, device in entry.runtime_data.devices.items():
        buttons: list[ButtonEntity] = [TeachInButton(device, p) for p in device.senders]
        if device.model.kind in LEARN_LOCK_KINDS:  # series 62: unlock learn mode, teach out
            buttons += [
                LearnButton(device, p, out)
                for p in device.senders
                if p in ("central", "controller")
                for out in (False, True)
            ]
        if device.impulse:
            buttons.append(ImpulseButton(device))
        if device.model.kind == "cover":
            buttons.append(CalibrateButton(device))
        if device.model.kind == "virtual_rocker":
            chosen = device.options.get(OPT_BUTTONS, SCENE_BUTTONS)
            buttons.extend(VirtualRockerButton(device, b) for b in SCENE_BUTTONS if b in chosen)
        elif device.model.kind == "virtual_scene":
            buttons.extend(
                VirtualRockerButton(device, b, scene=n) for n, b in enumerate(SCENE_BUTTONS, 1)
            )
        elif device.virtual is not None:
            buttons.append(SendNowButton(device))
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


class LearnButton(EnOceanEntity, ButtonEntity):
    """Series 62 actuators (FL62, FR62, FD62, FJ62): unlock the learn mode, or teach the sender
    out (the same telegram three times within 2 s). Off by default: other series ignore it."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, device: EnOceanDevice, profile: str, teach_out: bool) -> None:
        key = f"{'teach_out' if teach_out else 'unlock_learning'}_{profile}"
        super().__init__(device, key)
        self._profile = profile
        self._teach_out = teach_out
        self._attr_translation_key = key

    async def async_press(self) -> None:
        if self._teach_out:
            self._device.teach_out(self._profile)
        else:
            self._device.unlock_learning(self._profile)

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class ImpulseButton(EnOceanEntity, ButtonEntity):
    """A switching actuator as a button (garage door drive): sends "on" once, never repeated.
    The relay has to fall back by itself (relay function ER with an off delay, EW time)."""

    _attr_translation_key = "impulse"

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "impulse")

    async def async_press(self) -> None:
        switch_actuator(self._device, True)

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class CalibrateButton(EnOceanEntity, ButtonEntity):
    """I6: drive the cover to the nearer end position and back."""

    _attr_translation_key = "calibrate"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "calibrate")

    async def async_press(self) -> None:
        """The run takes up to a full run and back: it goes on after the press returns, and
        stops with the entry (reload, unload)."""
        if self._device.cover_entity is not None and self.platform.config_entry is not None:
            self.platform.config_entry.async_create_background_task(
                self.hass, self._calibrate(), f"calibrate {self.entity_id}"
            )

    async def _calibrate(self) -> None:
        assert self._device.cover_entity is not None
        try:
            await self._device.cover_entity.async_calibrate()
        except HomeAssistantError as err:
            _LOGGER.warning("Calibrating %s failed: %s", self._device.subentry.title, err)

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class SendNowButton(EnOceanEntity, ButtonEntity):
    """I9: send the source's current value right away (e.g. after teaching in)."""

    _attr_translation_key = "send_now"

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "send_now")

    async def async_press(self) -> None:
        self._device.virtual.send_current()

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class VirtualRockerButton(EnOceanEntity, ButtonEntity):
    """I9: a rocker button pressed and released by Home Assistant (FT55-like)."""

    def __init__(self, device: EnOceanDevice, button: str, scene: int | None = None) -> None:
        key = f"press_{button}" if scene is None else f"scene_{scene}"
        super().__init__(device, key)
        self._code = bytes([ROCKER_BUTTONS[button]])
        self._attr_translation_key = key

    async def async_press(self) -> None:
        self._device.press("rocker", self._code, confirm=False)

    def _apply(self, values: dict[str, Any]) -> bool:
        return False
