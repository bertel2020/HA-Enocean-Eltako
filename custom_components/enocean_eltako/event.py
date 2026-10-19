"""Rocker switches: one event entity per button with gestures (E6)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later

from . import EnOceanEltakoConfigEntry
from .catalog import OPT_DOUBLE_PRESS, OPT_LONG_PRESS
from .const import DOMAIN
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .gestures import DEFAULT_DOUBLE_PRESS, DEFAULT_LONG_PRESS, EVENT_TYPES, GestureDetector

PARALLEL_UPDATES = 0

# F6-02-01 rocker action R1/R2: 0 = A1 (AI), 1 = A0 (AO), 2 = B1 (BI), 3 = B0 (BO)
BUTTONS = ("a1", "a0", "b1", "b0")
EVENT_BUTTON = f"{DOMAIN}_button"  # bus event for device triggers


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if Platform.EVENT not in device.model.platforms:
            continue
        buttons = {b: RockerButton(device, b) for b in ("a0", "a1", "b0", "b1")}
        RockerGestures(hass, device, buttons)
        async_add_entities(list(buttons.values()), config_subentry_id=subentry_id)


class RockerGestures:
    """Feeds one device's rocker telegrams into the gesture detector."""

    def __init__(
        self, hass: HomeAssistant, device: EnOceanDevice, buttons: dict[str, RockerButton]
    ) -> None:
        self._hass = hass
        self._device = device
        self._buttons = buttons

        def call_later(delay: float, action: Any) -> Any:
            # a @callback runs in the event loop (a plain lambda would go to the executor)
            return async_call_later(hass, delay, callback(lambda _now: action()))

        self._detector = GestureDetector(
            self._emit,
            call_later,
            float(device.options.get(OPT_LONG_PRESS) or DEFAULT_LONG_PRESS),
            float(device.options.get(OPT_DOUBLE_PRESS) or DEFAULT_DOUBLE_PRESS),
        )
        device.entry.async_on_unload(device.add_listener(self._handle))
        device.entry.async_on_unload(self._detector.cancel)

    @callback
    def _handle(self, values: dict[str, Any]) -> None:
        if values.get("EB") == 1:
            second = BUTTONS[values["R2"]] if values.get("SA") == 1 else None
            self._detector.press(BUTTONS[values["R1"]], second)
        elif values.get("EB") == 0:
            self._detector.release()

    @callback
    def _emit(self, button: str, event_type: str, data: dict[str, Any]) -> None:
        self._buttons[button].fire(event_type, data)
        registry_id = (
            self._buttons[button].device_entry.id if self._buttons[button].device_entry else None
        )
        self._hass.bus.async_fire(
            EVENT_BUTTON,
            {"device_id": registry_id, "button": button, "type": event_type, **data},
        )


class RockerButton(EnOceanEntity, EventEntity):
    _attr_translation_key = "button"
    _attr_event_types = EVENT_TYPES

    def __init__(self, device: EnOceanDevice, button: str) -> None:
        super().__init__(device, f"button_{button}")
        self._attr_translation_placeholders = {"button": button.upper()}

    @callback
    def fire(self, event_type: str, data: dict[str, Any]) -> None:
        if self.hass is None:
            return
        self._trigger_event(event_type, data)
        self.async_write_ha_state()

    def _apply(self, values: dict[str, Any]) -> bool:
        return False  # events come from the gesture detector
