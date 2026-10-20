"""I9 virtual sensors: a Home Assistant entity sent as an EnOcean contact, motion or
temperature sensor, so actuators can use it (window contact lowers the heating, a lux or
door state for the shutter actuator).

The device's ID is its own sender ID from the pool. It sends on every change of the source
and repeats the current value every send interval (actuators that supervise their sensors
drop a silent one). An unavailable source sends nothing, or for contacts optionally the
safe value "open".
"""

from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.util.unit_conversion import TemperatureConverter

from .catalog import OPT_INVERT, OPT_SEND_INTERVAL, OPT_SOURCE, OPT_WHEN_UNAVAILABLE
from .device import EnOceanDevice
from .protocol.eep import virtual
from .protocol.send_queue import Priority

_LOGGER = logging.getLogger(__name__)

CONTACT_OPEN = "open"
CONTACT_CLOSED = "closed"
MOTION = "motion"
NO_MOTION = "no_motion"


class VirtualSensor:
    """Follows the source entity and sends its value from the device's sender ID."""

    def __init__(self, hass: HomeAssistant, device: EnOceanDevice) -> None:
        self.hass = hass
        self.device = device
        self.kind = device.model.kind
        self.source: str | None = device.options.get(OPT_SOURCE)
        self.sent_value: str | float | None = None
        self.last_sent: float | None = None  # time.time()
        self._listeners: list[Callable[[], None]] = []

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def start(self) -> Callable[[], None]:
        if self.source is None:
            return lambda: None

        @callback
        def send(_arg: Any) -> None:
            self.send_current()

        removers = [
            async_track_state_change_event(self.hass, self.source, self._source_changed),
            async_at_started(self.hass, send),
        ]
        if interval := int(self.device.options.get(OPT_SEND_INTERVAL) or 0):
            removers.append(async_track_time_interval(self.hass, send, timedelta(seconds=interval)))

        def stop() -> None:
            for remove in removers:
                remove()

        return stop

    @callback
    def _source_changed(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data["old_state"], event.data["new_state"]
        if old is not None and new is not None and old.state == new.state:
            return  # attribute change only
        self.send_current()

    def value(self, state: State | None) -> str | float | None:
        """Value to send for a source state; None = send nothing."""
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            if self.kind == "virtual_contact" and (
                self.device.options.get(OPT_WHEN_UNAVAILABLE) == "safe"
            ):
                return CONTACT_OPEN
            return None
        invert = bool(self.device.options.get(OPT_INVERT))
        if self.kind == "virtual_contact":  # on = open (door, window binary sensors)
            return CONTACT_OPEN if (state.state == STATE_ON) != invert else CONTACT_CLOSED
        if self.kind == "virtual_motion":
            return MOTION if (state.state == STATE_ON) != invert else NO_MOTION
        try:
            value = float(state.state)
        except ValueError:
            return None
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature.CELSIUS)
        with contextlib.suppress(ValueError, KeyError):
            value = TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
        return round(value, 1)

    def encode(self, value: str | float) -> bytes:
        if self.kind == "virtual_contact":
            return virtual.encode_contact(value == CONTACT_CLOSED)
        if self.kind == "virtual_motion":
            return virtual.encode_motion(value == MOTION)
        return virtual.encode_temperature(float(value))

    @callback
    def send_current(self) -> None:
        """Send the source's current value (on change, cyclically, or by the button)."""
        if self.source is None:
            return
        value = self.value(self.hass.states.get(self.source))
        if value is None:
            return
        try:
            self.device.send(
                self.encode(value), priority=Priority.AUTOMATION, key="value", confirm=False
            )
        except HomeAssistantError as err:
            _LOGGER.debug("%s: not sent: %s", self.device.subentry.title, err)
            return
        self.sent_value = value
        self.last_sent = time.time()
        for listener in list(self._listeners):
            listener()
