"""I9 virtual sensors: a Home Assistant entity sent as an EnOcean contact, motion,
temperature or brightness sensor, or several entities as an Eltako weather station, so
actuators can use them (window contact lowers the heating, lux or wind and rain for the
shutter actuator's automatic functions).

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
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.util.unit_conversion import SpeedConverter, TemperatureConverter

from .catalog import (
    OPT_INVERT,
    OPT_SEND_INTERVAL,
    OPT_SOURCE,
    OPT_WEATHER_BRIGHTNESS,
    OPT_WEATHER_RAIN,
    OPT_WEATHER_TEMPERATURE,
    OPT_WEATHER_WIND,
    OPT_WHEN_UNAVAILABLE,
    WEATHER_SOURCES,
)
from .device import EnOceanDevice
from .protocol.eep import virtual
from .protocol.send_queue import Priority

_LOGGER = logging.getLogger(__name__)

CONTACT_OPEN = "open"
CONTACT_CLOSED = "closed"
MOTION = "motion"
NO_MOTION = "no_motion"
NIGHT_BELOW_LUX = 10.0  # weather station: day/night bit from the brightness
# weather values sent while no entity is chosen for them
WEATHER_DEFAULTS = {
    OPT_WEATHER_TEMPERATURE: 20.0,
    OPT_WEATHER_WIND: 0.0,
    OPT_WEATHER_RAIN: False,
    OPT_WEATHER_BRIGHTNESS: 0.0,
}


def _number(state: State) -> float | None:
    try:
        return float(state.state)
    except ValueError:
        return None


def _celsius(state: State) -> float | None:
    value = _number(state)
    if value is None:
        return None
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfTemperature.CELSIUS)
    with contextlib.suppress(ValueError, KeyError):
        value = TemperatureConverter.convert(value, unit, UnitOfTemperature.CELSIUS)
    return round(value, 1)


def _meters_per_second(state: State) -> float | None:
    value = _number(state)
    if value is None:
        return None
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfSpeed.METERS_PER_SECOND)
    with contextlib.suppress(ValueError, KeyError):
        value = SpeedConverter.convert(value, unit, UnitOfSpeed.METERS_PER_SECOND)
    return round(value, 1)


class VirtualSensor:
    """Follows the source entity and sends its value from the device's sender ID."""

    def __init__(self, hass: HomeAssistant, device: EnOceanDevice) -> None:
        self.hass = hass
        self.device = device
        self.kind = device.model.kind
        self.source: str | None = device.options.get(OPT_SOURCE)
        # the weather station follows one entity per value; the others one source
        self.weather: dict[str, str] = {
            key: device.options[key] for key in WEATHER_SOURCES if device.options.get(key)
        }
        self.sources = list(self.weather.values()) or ([self.source] if self.source else [])
        self.sent_value: str | float | None = None
        self.last_sent: float | None = None  # time.time()
        self._listeners: list[Callable[[], None]] = []

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def start(self) -> Callable[[], None]:
        if not self.sources:
            return lambda: None

        @callback
        def send(_arg: Any) -> None:
            self.send_current()

        removers = [
            async_track_state_change_event(self.hass, self.sources, self._source_changed),
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

    def weather_values(self) -> dict[str, Any] | None:
        """Weather station: the chosen entities' values, defaults for the others; None
        (send nothing) while a chosen entity is unavailable, so no wrong alarm goes out."""
        values = dict(WEATHER_DEFAULTS)
        for key, entity_id in self.weather.items():
            state = self.hass.states.get(entity_id)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return None
            if key == OPT_WEATHER_RAIN:
                values[key] = state.state == STATE_ON
                continue
            convert = {OPT_WEATHER_TEMPERATURE: _celsius, OPT_WEATHER_WIND: _meters_per_second}
            value = convert.get(key, _number)(state)
            if value is None:
                return None
            values[key] = value
        return values

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
        if self.kind == "virtual_brightness":
            lux = _number(state)
            return None if lux is None else round(lux)
        return _celsius(state)

    def encode(self, value: str | float) -> bytes:
        if self.kind == "virtual_contact":
            return virtual.encode_contact(value == CONTACT_CLOSED)
        if self.kind == "virtual_motion":
            return virtual.encode_motion(value == MOTION)
        if self.kind == "virtual_brightness":
            return virtual.encode_brightness(float(value))
        return virtual.encode_temperature(float(value))

    def _send_weather(self) -> str | None:
        """Both FWS61 telegrams; the brightness also stands for the sun on all sides."""
        values = self.weather_values()
        if values is None:
            return None
        lux = float(values[OPT_WEATHER_BRIGHTNESS])
        klx = lux / 1000
        telegrams = (
            virtual.encode_weather(
                lux,
                values[OPT_WEATHER_TEMPERATURE],
                values[OPT_WEATHER_WIND],
                night=OPT_WEATHER_BRIGHTNESS in self.weather and lux < NIGHT_BELOW_LUX,
                rain=values[OPT_WEATHER_RAIN],
            ),
            virtual.encode_sun(klx, klx, klx),
        )
        for key, data in zip(("value", "sun"), telegrams, strict=True):
            self.device.send(data, priority=Priority.AUTOMATION, key=key, confirm=False)
        rain = "rain" if values[OPT_WEATHER_RAIN] else "dry"
        return (
            f"{values[OPT_WEATHER_TEMPERATURE]} °C, {values[OPT_WEATHER_WIND]} m/s, "
            f"{rain}, {round(lux)} lx"
        )

    @callback
    def send_current(self) -> None:
        """Send the source's current value (on change, cyclically, or by the button)."""
        if not self.sources:
            return
        try:
            if self.weather:
                value: str | float | None = self._send_weather()
            else:
                assert self.source is not None
                value = self.value(self.hass.states.get(self.source))
                if value is not None:
                    self.device.send(
                        self.encode(value),
                        priority=Priority.AUTOMATION,
                        key="value",
                        confirm=False,
                    )
            if value is None:
                return
        except HomeAssistantError as err:
            _LOGGER.debug("%s: not sent: %s", self.device.subentry.title, err)
            return
        self.sent_value = value
        self.last_sent = time.time()
        for listener in list(self._listeners):
            listener()
