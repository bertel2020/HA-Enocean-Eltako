"""Teach-in buttons (one per sender profile of an actuator), calibration, gateway reconnect;
I9 virtual sensors: send now, virtual rocker buttons."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import EnOceanEltakoConfigEntry
from .catalog import OPT_BUTTONS
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .gateway_entity import GatewayReconnectButton

# F6-02-01 rocker action of each button (pressed)
ROCKER_BUTTONS = {"b0": 0x70, "b1": 0x50, "a0": 0x30, "a1": 0x10}
# I9 scene button (double rocker taught in as scene button, e.g. FSB14 learn function
# 180/200): scene 1...4 = left top, left bottom, right top, right bottom
SCENE_BUTTONS = ("a0", "a1", "b0", "b1")

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    if not entry.runtime_data.on_demand:  # on demand: the bus group connects it
        async_add_entities([GatewayReconnectButton(entry)])
    for subentry_id, device in entry.runtime_data.devices.items():
        buttons: list[ButtonEntity] = [TeachInButton(device, p) for p in device.senders]
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
