"""Climate (E8).

Room controller on site (FUTH, FTR): read only; setpoint, temperature and night setback come
from its telegrams and it is operated locally.

Heating actuator (FHK14, FAE14, F4HK14, FHK61) with Home Assistant as room controller: the
entity sends setpoint and room temperature (from a chosen sensor) every send interval, at
most every 10 min, also without changes. Without telegrams for more than 1 h the actuator
falls back to its fault mode, the safe fallback when Home Assistant is down; a repair issue
appears when a channel could not send for 45 min. "Off" sends setpoint 0 degC: the actuator
stops heating and keeps its own frost protection.
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.restore_state import RestoreEntity

from . import EnOceanEltakoConfigEntry
from .catalog import COOLING_PRESS, COOLING_SWITCH, OPT_SEND_INTERVAL, OPT_TEMPERATURE_SENSOR
from .const import DOMAIN
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .protocol.eep.eltako import heating
from .protocol.send_queue import Priority

PARALLEL_UPDATES = 0

DEFAULT_SEND_INTERVAL = 60
MAX_SEND_INTERVAL = 600  # the actuators need a telegram at least every 10 min
SILENCE_REPAIR = 45 * 60  # seconds without a successful send before the repair issue
COOLING_REPEAT = 600  # s between cooling switch presses; switch inputs repeat every 15 min
DEFAULT_SETPOINT = 21.0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.model.kind == "room_controller":
            async_add_entities([RoomControllerClimate(device)], config_subentry_id=subentry_id)
        elif device.model.kind == "heating_actuator":
            async_add_entities([HeatingClimate(device)], config_subentry_id=subentry_id)


class RoomControllerClimate(EnOceanEntity, ClimateEntity, RestoreEntity):
    """Read-only image of a controller operated on site."""

    _attr_name = None
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    # the feature shows the setpoint; setting it is refused (operated on site)
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "climate")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="room_controller_read_only"
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self._attr_current_temperature = last.attributes.get("current_temperature")
            self._attr_target_temperature = last.attributes.get(ATTR_TEMPERATURE)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Only heating; the controller is operated on site."""

    def _apply(self, values: dict[str, Any]) -> bool:
        before = (self._attr_current_temperature, self._attr_target_temperature)
        if "temperature" in values:
            self._attr_current_temperature = values["temperature"]
        if "setpoint" in values:
            self._attr_target_temperature = values["setpoint"]
        return before != (self._attr_current_temperature, self._attr_target_temperature)


class HeatingClimate(EnOceanEntity, ClimateEntity, RestoreEntity):
    """Home Assistant as room controller for an Eltako heating actuator."""

    _attr_name = None
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5
    _attr_max_temp = 30
    _attr_target_temperature_step = 0.5

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "climate")
        self._cooling = device.has_sender(COOLING_SWITCH.id)
        if self._cooling:
            self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.COOL, HVACMode.OFF]
        self._last_cooling_press: float | None = None
        self._sensor: str | None = device.options.get(OPT_TEMPERATURE_SENSOR)
        interval = int(device.options.get(OPT_SEND_INTERVAL) or DEFAULT_SEND_INTERVAL)
        self._interval = max(10, min(MAX_SEND_INTERVAL, interval))
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_target_temperature = DEFAULT_SETPOINT
        self._last_ok = time.monotonic()
        self._issue_id = f"climate_silent_{device.unique_prefix}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            if last.state in self._attr_hvac_modes:
                self._attr_hvac_mode = HVACMode(last.state)
            if (target := last.attributes.get(ATTR_TEMPERATURE)) is not None:
                self._attr_target_temperature = float(target)
        self._read_sensor()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_cycle, timedelta(seconds=self._interval)
            )
        )
        self._send()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (target := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = float(target)
        self._send()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._attr_hvac_mode = hvac_mode
        self._last_cooling_press = None  # entering cooling: press the switch at once
        self._send()
        self.async_write_ha_state()

    @callback
    def _async_cycle(self, _now: Any) -> None:
        self._read_sensor()
        self._send()
        self._check_silence()
        self.async_write_ha_state()

    def _read_sensor(self) -> None:
        if self._sensor is None or (state := self.hass.states.get(self._sensor)) is None:
            return
        try:
            self._attr_current_temperature = float(state.state)
        except ValueError:
            return

    @callback
    def _send(self) -> None:
        if self._sensor is not None and self._attr_current_temperature is None:
            return  # no room temperature yet; the actuator keeps its last values
        setpoint = (
            0.0 if self._attr_hvac_mode == HVACMode.OFF else self._attr_target_temperature or 0
        )
        try:
            self._device.send(
                # without an entity the actuator's own thermostat measures (setpoint only)
                heating.encode_controller(
                    setpoint, self._attr_current_temperature if self._sensor else None
                ),
                priority=Priority.AUTOMATION,
                key="controller",
                confirm=False,
            )
        except HomeAssistantError:  # gateway offline: retried next cycle
            return
        self._last_ok = time.monotonic()
        ir.async_delete_issue(self.hass, DOMAIN, self._issue_id)
        self._keep_cooling()

    def _keep_cooling(self) -> None:
        """Cooling: repeat the cooling switch press, as a real switch input would."""
        if not self._cooling or self._attr_hvac_mode != HVACMode.COOL:
            return
        now = time.monotonic()
        if self._last_cooling_press is not None and now - self._last_cooling_press < COOLING_REPEAT:
            return
        try:
            self._device.press(COOLING_SWITCH.id, COOLING_PRESS, confirm=False)
        except HomeAssistantError:
            return
        self._last_cooling_press = now

    def _check_silence(self) -> None:
        if time.monotonic() - self._last_ok >= SILENCE_REPAIR:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self._issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="climate_silent",
                translation_placeholders={"name": self._device.subentry.title},
            )

    def _apply(self, values: dict[str, Any]) -> bool:
        if "mode" not in values:
            # the actuator's acknowledgement: its thermostat's temperature, if HA has none
            temperature = values.get("temperature")
            if self._sensor is not None or temperature in (None, self._attr_current_temperature):
                return False
            self._attr_current_temperature = temperature
            return True
        if values["mode"] == "off":
            action = HVACAction.OFF
        elif self._attr_hvac_mode == HVACMode.COOL:
            action = HVACAction.COOLING
        else:
            action = HVACAction.HEATING
        if action == self._attr_hvac_action:
            return False
        self._attr_hvac_action = action
        return True
