"""Switches: switching actuators configured as switch (sockets, convectors, releases)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import OPT_CHANNEL, OPT_PLATFORM
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .light import inverted, on_state, switch_actuator
from .protocol.eep import vld

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.lockable:
            async_add_entities([LockButtonsSwitch(device)], config_subentry_id=subentry_id)
        platform = device.options.get(OPT_PLATFORM)
        if (device.model.kind == "switch" and platform == Platform.SWITCH) or (
            device.model.kind == "psc" and platform in (None, Platform.SWITCH)
        ):
            async_add_entities([EnOceanSwitch(device)], config_subentry_id=subentry_id)
        elif device.model.kind == "vld_switch" and platform == Platform.SWITCH:
            async_add_entities([VldSwitch(device)], config_subentry_id=subentry_id)


class EnOceanSwitch(EnOceanEntity, SwitchEntity, RestoreEntity):
    _attr_name = None
    _assume_until_heard = True

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "switch")
        self._invert = inverted(device)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"
            self._device.wall_state = self._attr_is_on != self._invert  # I4: raw relay state

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


class LockButtonsSwitch(EnOceanEntity, SwitchEntity, RestoreEntity):
    """Lock the pushbuttons of an actuator: every command carries the lock bit (DB0.2), so the
    taught-in pushbuttons cannot change the state until the lock is lifted. The actuator does
    not report the lock (a shutter only in a run), so the state is the last one set."""

    _attr_translation_key = "lock_buttons"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_is_on = False

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "lock_buttons")

    @property
    def assumed_state(self) -> bool:
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state == "on":
            self._attr_is_on = True
            self._device.locked = True

    async def _set(self, locked: bool) -> None:
        self._device.locked = locked
        try:
            self._device.apply_lock()
        except HomeAssistantError:
            self._device.locked = not locked
            raise
        self._attr_is_on = locked
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    def _apply(self, values: dict[str, Any]) -> bool:
        return False


class VldSwitch(EnOceanSwitch):
    """D2-01 channel as a plain switch (sockets, releases)."""

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device)
        self._channel = int(device.options.get(OPT_CHANNEL, 0))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._device.send(vld.encode_set_output(self._channel, 100), key="switch")

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._device.send(vld.encode_set_output(self._channel, 0), key="switch")

    def _apply(self, values: dict[str, Any]) -> bool:
        output = vld.switch_status(values, self._channel)
        if output is None or (output > 0) == self._attr_is_on:
            return False
        self._attr_is_on = output > 0
        return True
