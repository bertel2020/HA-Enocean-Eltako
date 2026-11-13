"""Thermostat of a switching actuator: Home Assistant regulates, the relay switches.

A switching actuator (FSR14, FSR61 ...) cannot regulate; a convector with a thermostat of its own
only shows whether it heats through the power of a meter (F3Z14D) on the same load. The optional
thermostat of the channel regulates a room temperature (any Home Assistant sensor) around a
setpoint, switches the relay through the send queue and reads the power of the meter that is set
to "belongs to device" this actuator, so "heating" means that power really flows.

Everything that decides is in ``decide`` (a pure function, tested as a table); the controller
only feeds it (sensors, relay state, clock) and carries the decision out. Safety stays with the
convector's own thermostat: Home Assistant adds a limit below it and never raises it.

- Hysteresis: on at or below setpoint - hysteresis, off at or above setpoint + hysteresis; in
  between nothing is sent, so a relay switched by hand or by a wall switch stays as it is until
  the next threshold is crossed.
- Shortest time on and off (min_cycle) protects the relay; going off because of the safety rules
  below is never held back.
- Longest run (max_run) in a row, then a forced pause (cooldown).
- No room temperature (unavailable, or silent for longer than stale_after): relay off.
- Relay on, power below the active threshold for blocked_after, room below setpoint: "blocked"
  (the convector's own thermostat, or the device, stops it); a repair issue says so.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .catalog import (
    OPT_ACTIVE_POWER,
    OPT_BLOCKED_AFTER,
    OPT_COOLDOWN,
    OPT_HUMIDITY_SENSOR,
    OPT_HYSTERESIS,
    OPT_MAX_RUN,
    OPT_MIN_CYCLE,
    OPT_SETPOINT_MAX,
    OPT_SETPOINT_MIN,
    OPT_SETPOINT_STEP,
    OPT_STALE_AFTER,
    OPT_TEMP_PRECISION,
    OPT_THERMOSTAT,
    OPT_THERMOSTAT_SENSOR,
    THERMOSTAT_DEFAULTS,
)
from .device import EnOceanDevice

TICK = 30  # s between checks: clock based rules (pauses, silence, longest run) and the repeat
REPEAT = 600  # s after which the last command is sent again (the relay state is assumed)
DEFAULT_SETPOINT = 21.0


class Status(StrEnum):
    OFF = "off"  # mode Off
    HEATING = "heating"  # relay on and power flows (without a meter: relay on)
    IDLE = "idle"  # nothing to do, or relay on but the load takes no power (its own thermostat)
    REACHED = "reached"  # relay off, the room is at the setpoint
    COOLDOWN = "cooldown"  # forced pause after the longest run
    BLOCKED = "blocked"  # relay on, no power for too long, the room is below the setpoint
    SENSOR_STALE = "sensor_stale"  # no room temperature: relay off for safety


@dataclass(frozen=True, slots=True)
class Settings:
    hysteresis: float
    setpoint_min: float
    setpoint_max: float
    step: float
    precision: float
    min_cycle: float  # s
    max_run: float  # s, 0 = unlimited
    cooldown: float  # s
    active_power: float  # W
    blocked_after: float  # s
    stale_after: float  # s

    @classmethod
    def from_options(cls, options: dict[str, Any]) -> Settings:
        def number(key: str) -> float:
            value = options.get(key)
            return float(THERMOSTAT_DEFAULTS[key] if value in (None, "") else value)

        return cls(
            hysteresis=number(OPT_HYSTERESIS),
            setpoint_min=number(OPT_SETPOINT_MIN),
            setpoint_max=number(OPT_SETPOINT_MAX),
            step=number(OPT_SETPOINT_STEP),
            precision=number(OPT_TEMP_PRECISION),
            min_cycle=number(OPT_MIN_CYCLE) * 60,
            max_run=number(OPT_MAX_RUN) * 60,
            cooldown=number(OPT_COOLDOWN) * 60,
            active_power=number(OPT_ACTIVE_POWER),
            blocked_after=number(OPT_BLOCKED_AFTER) * 60,
            stale_after=number(OPT_STALE_AFTER) * 60,
        )


@dataclass(frozen=True, slots=True)
class Inputs:
    now: float  # monotonic seconds
    heating: bool  # mode Heat (False: Off)
    setpoint: float
    temperature: float | None  # None: unavailable
    temperature_age: float | None  # s since the sensor last reported
    relay_on: bool | None  # None: unknown so far
    changed_at: float | None  # when the relay last changed (its own or observed)
    run_started: float | None  # when the current run began (relay on)
    cooldown_until: float  # end of a forced pause (<= now: none)
    power: float | None  # W of the meter on the load, None: no meter or no reading
    low_power_since: float | None  # since when the relay is on and the power below the threshold


@dataclass(frozen=True, slots=True)
class Decision:
    relay: bool | None  # True / False: send; None: leave as it is
    status: Status
    start_cooldown: bool = False  # the longest run is over: begin the forced pause now


def decide(settings: Settings, data: Inputs) -> Decision:
    """What the relay should do now and what to report."""
    on = data.relay_on
    if not data.heating:
        return Decision(False if on is not False else None, Status.OFF)
    if data.temperature is None or (
        data.temperature_age is not None and data.temperature_age > settings.stale_after
    ):
        return Decision(False if on is not False else None, Status.SENSOR_STALE)
    if data.now < data.cooldown_until:
        return Decision(False if on is not False else None, Status.COOLDOWN)
    if (
        on
        and settings.max_run > 0
        and data.run_started is not None
        and data.now - data.run_started >= settings.max_run
    ):
        return Decision(False, Status.COOLDOWN, start_cooldown=True)

    temperature = data.temperature
    want: bool | None = None
    if temperature <= data.setpoint - settings.hysteresis:
        want = True
    elif temperature >= data.setpoint + settings.hysteresis:
        want = False
    if want is not None and want == on:
        want = None  # nothing to do (a command is repeated by the controller)
    if (
        want is not None
        and on is not None
        and data.changed_at is not None
        and data.now - data.changed_at < settings.min_cycle
    ):
        want = None  # too soon after the last change; the next check tries again

    relay = on if want is None else want
    if relay:
        blocked = (
            data.power is not None
            and data.low_power_since is not None
            and data.now - data.low_power_since >= settings.blocked_after
            and temperature < data.setpoint
        )
        if blocked:
            status = Status.BLOCKED
        elif data.power is not None and data.power < settings.active_power:
            status = Status.IDLE
        else:
            status = Status.HEATING
    else:
        status = Status.REACHED if temperature >= data.setpoint else Status.IDLE
    return Decision(want, status)


def _float(value: str | None) -> float | None:
    if value in (None, STATE_UNAVAILABLE, STATE_UNKNOWN):
        return None
    try:
        return float(value)
    except ValueError:
        return None


class ThermostatController:
    """Feeds ``decide`` and carries the decision out for one switching actuator channel."""

    def __init__(self, hass: HomeAssistant, device: EnOceanDevice) -> None:
        self.hass = hass
        self.device = device
        self.settings = Settings.from_options(device.options)
        self.sensor: str | None = device.options.get(OPT_THERMOSTAT_SENSOR) or None
        self.humidity_sensor: str | None = device.options.get(OPT_HUMIDITY_SENSOR) or None
        self.setpoint = DEFAULT_SETPOINT
        self.heating = True
        self.status = Status.IDLE
        self.temperature: float | None = None
        self.humidity: float | None = None
        self.power: float | None = None
        self.relay_on: bool | None = None
        self.on_time_today = 0.0  # s relay on since midnight (not kept across a restart)
        self._changed_at: float | None = None
        self._run_started: float | None = None
        self._cooldown_until = 0.0
        self._low_power_since: float | None = None
        self._last_sent = 0.0
        self._last_tick = time.monotonic()
        self._day = dt_util.now().date()
        self._listeners: list[Callable[[], None]] = []
        self._unsubscribe: list[CALLBACK_TYPE] = []
        self._users = 0
        self._meter: EnOceanDevice | None = None
        self.snapshot: tuple[Any, ...] = ()
        # nothing is sent before the climate entity restored setpoint and mode (or the first
        # tick passed): the defaults would switch the relay on after every reload
        self._settled = False
        self._first = True

    # -- lifecycle ---------------------------------------------------------------------------

    @callback
    def start(self) -> None:
        """Shared by the thermostat and its extra entities: the first one starts it."""
        self._users += 1
        if self._users > 1:
            return
        entities = [e for e in (self.sensor, self.humidity_sensor) if e]
        if entities:
            self._unsubscribe.append(
                async_track_state_change_event(self.hass, entities, self._sensor_changed)
            )
        self._unsubscribe.append(self.device.add_listener(self._relay_values))
        if (meter := self.find_meter()) is not None:
            self._meter = meter
            self._unsubscribe.append(meter.add_listener(self._meter_values))
            self.power = self._power_of(meter.last_values)
        self._unsubscribe.append(
            async_track_time_interval(self.hass, self._tick, timedelta(seconds=TICK))
        )
        self._read_sensors()
        self.relay_on = self._relay_of(self.device.last_values)

    @callback
    def stop(self) -> None:
        self._users = max(0, self._users - 1)
        if self._users:
            return
        for unsubscribe in self._unsubscribe:
            unsubscribe()
        self._unsubscribe.clear()
        self._listeners.clear()
        self._settled, self._first = False, True

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def find_meter(self) -> EnOceanDevice | None:
        """The meter that is set to "belongs to device" this actuator, if any."""
        for other in self.device.entry.runtime_data.devices.values():
            if other.part_of is self.device:
                return other
        return None

    @property
    def has_meter(self) -> bool:
        return self._meter is not None

    # -- inputs ------------------------------------------------------------------------------

    @staticmethod
    def _power_of(values: dict[str, Any]) -> float | None:
        return round(values["MR"], 1) if values.get("DT") == 1 and "MR" in values else None

    def _relay_of(self, values: dict[str, Any]) -> bool | None:
        from .light import inverted, on_state  # a platform module: not at import time

        state = on_state(values)
        return None if state is None else state != inverted(self.device)

    @callback
    def _sensor_changed(self, event: Event[EventStateChangedData]) -> None:
        self._read_sensors()
        self._evaluate()

    def _read_sensors(self) -> None:
        state = self.hass.states.get(self.sensor) if self.sensor else None
        self.temperature = _float(state.state) if state is not None else None
        if self.humidity_sensor and (humidity := self.hass.states.get(self.humidity_sensor)):
            self.humidity = _float(humidity.state)

    def _temperature_age(self) -> float | None:
        state = self.hass.states.get(self.sensor) if self.sensor else None
        if state is None:
            return None
        return (dt_util.utcnow() - state.last_reported).total_seconds()

    @callback
    def _relay_values(self, values: dict[str, Any]) -> None:
        relay = self._relay_of(values)
        if relay is None or relay == self.relay_on:
            return
        self._set_relay(relay)  # observed (its own report, a wall switch, a central command)
        self._evaluate()

    @callback
    def _meter_values(self, values: dict[str, Any]) -> None:
        power = self._power_of(values)
        if power is None or power == self.power:
            return
        self.power = power
        self._evaluate()

    # -- control -----------------------------------------------------------------------------

    def _set_relay(self, relay: bool) -> None:
        now = time.monotonic()
        self._account(now)
        self.relay_on = relay
        self._changed_at = now
        self._run_started = now if relay else None
        self._low_power_since = None

    def _account(self, now: float) -> None:
        """Count the time the relay was on, by day."""
        if (today := dt_util.now().date()) != self._day:
            self._day = today
            self.on_time_today = 0.0
        if self.relay_on:
            self.on_time_today += now - self._last_tick
        self._last_tick = now

    def _inputs(self, now: float) -> Inputs:
        if self.relay_on and self.power is not None and self.power < self.settings.active_power:
            if self._low_power_since is None:
                self._low_power_since = now
        else:
            self._low_power_since = None
        return Inputs(
            now=now,
            heating=self.heating,
            setpoint=self.setpoint,
            temperature=self.temperature,
            temperature_age=self._temperature_age(),
            relay_on=self.relay_on,
            changed_at=self._changed_at,
            run_started=self._run_started,
            cooldown_until=self._cooldown_until,
            power=self.power,
            low_power_since=self._low_power_since,
        )

    @callback
    def _evaluate(self) -> None:
        if not self._settled:
            return
        initial, self._first = self._first, False
        now = time.monotonic()
        self._account(now)
        decision = decide(self.settings, self._inputs(now))
        relay = decision.relay
        if initial and relay is None and self.relay_on is None:
            relay = False  # a defined state after a start: off, until the room asks for heat
        if decision.start_cooldown:
            self._cooldown_until = now + self.settings.cooldown
        if relay is not None:
            self._send(relay, now)
        elif self.relay_on is not None and now - self._last_sent >= REPEAT and self._last_sent:
            self._send(self.relay_on, now)  # the state is only assumed: say it again
        status = decision.status
        if decision.start_cooldown:
            status = Status.COOLDOWN
        self.status = status
        self._notify()

    def _send(self, relay: bool, now: float) -> None:
        from .light import switch_actuator  # a platform module: not at import time

        try:
            switch_actuator(self.device, relay)
        except Exception:  # noqa: BLE001 - gateway offline: the next check tries again
            return
        self._last_sent = now
        if relay != self.relay_on:
            self._set_relay(relay)

    @callback
    def _tick(self, _now: Any) -> None:
        self._settled = True  # no climate entity restored anything: the defaults stand
        self._read_sensors()
        self._evaluate()

    # -- operation ---------------------------------------------------------------------------

    @callback
    def set_setpoint(self, value: float) -> None:
        self.setpoint = min(self.settings.setpoint_max, max(self.settings.setpoint_min, value))
        self._evaluate()

    @callback
    def set_heating(self, heating: bool) -> None:
        self.heating = heating
        self._evaluate()

    @callback
    def restore(self, setpoint: float | None, heating: bool | None) -> None:
        if setpoint is not None:
            self.setpoint = min(
                self.settings.setpoint_max, max(self.settings.setpoint_min, setpoint)
            )
        if heating is not None:
            self.heating = heating
        self._settled = True
        if self._users:
            self._evaluate()

    # -- outputs -----------------------------------------------------------------------------

    @property
    def run_minutes(self) -> int:
        if not self.relay_on or self._run_started is None:
            return 0
        return int((time.monotonic() - self._run_started) // 60)

    @property
    def cooldown_remaining(self) -> int:
        return max(0, int((self._cooldown_until - time.monotonic() + 59) // 60))

    @property
    def on_hours_today(self) -> float:
        extra = time.monotonic() - self._last_tick if self.relay_on else 0.0
        return round((self.on_time_today + extra) / 3600, 1)

    @property
    def is_heating(self) -> bool:
        return self.status == Status.HEATING

    @property
    def is_blocked(self) -> bool:
        return self.status == Status.BLOCKED

    def _notify(self) -> None:
        snapshot = (
            self.status,
            self.setpoint,
            self.heating,
            self.temperature,
            self.humidity,
            self.power,
            self.relay_on,
            self.run_minutes,
            self.cooldown_remaining,
            self.on_hours_today,
        )
        if snapshot == self.snapshot:
            return
        self.snapshot = snapshot
        for listener in list(self._listeners):
            listener()


def enabled(device: EnOceanDevice) -> bool:
    """Whether the channel has a thermostat (kind "switch", switched on, a room sensor set)."""
    return (
        device.model.kind == "switch"
        and bool(device.options.get(OPT_THERMOSTAT))
        and bool(device.options.get(OPT_THERMOSTAT_SENSOR))
    )


def controller_for(hass: HomeAssistant, device: EnOceanDevice) -> ThermostatController:
    """The controller of a device, created on first use (platforms set up in any order)."""
    controller: ThermostatController | None = device.thermostat
    if controller is None:
        controller = device.thermostat = ThermostatController(hass, device)
    return controller
