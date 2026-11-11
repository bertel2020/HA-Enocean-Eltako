"""Base entity: one per device function, updated from decoded telegram values."""

from __future__ import annotations

from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event

from .catalog import OPT_MEASURED_ENERGY, OPT_MEASURED_POWER, OPT_UNAVAILABLE_WHEN_SILENT
from .device import EnOceanDevice
from .entity_ids import PrefixedEntityId


class EnOceanEntity(PrefixedEntityId):
    _attr_has_entity_name = True
    _attr_should_poll = False
    # E2: actuator states restored after a restart count as assumed until the device reports
    _assume_until_heard = False
    _heard = False
    # a Device Proxy replay feeds in the changes of minutes within milliseconds: a pure state
    # (a contact) is written once, when the replay is through, so the flips in between fire
    # no triggers and a state that ends where it began fires none at all
    _write_after_replay = False
    _replay_write_pending = False

    def __init__(self, device: EnOceanDevice, key: str) -> None:
        self._device = device
        self._gateway_entry = device.entry
        self._attr_unique_id = f"{device.entity_prefix}_{key}"
        self._attr_device_info = device.device_info

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._device.add_listener(self._handle_values))
        self.async_on_remove(self._device.add_replay_listener(self._replay_done))
        self._was_available = self.available
        self.async_on_remove(self._device.add_stats_listener(self._availability_changed))

    @callback
    def _availability_changed(self) -> None:
        if self.available != self._was_available:
            self._was_available = self.available
            self.async_write_ha_state()

    @property
    def assumed_state(self) -> bool:
        return self._assume_until_heard and not self._heard

    @property
    def available(self) -> bool:
        """E5 option: unavailable while the device is silent."""
        return not (self._device.silent and self._device.options.get(OPT_UNAVAILABLE_WHEN_SILENT))

    @callback
    def _handle_values(self, values: dict[str, Any]) -> None:
        # write state only on a real change (cyclic repetitions are common)
        changed = self._apply(values)
        # I4: a wall switch press is a guess, only the actuator itself confirms the state
        if self._assume_until_heard and not self._heard and not values.get("assumed"):
            self._heard = True
            changed = True
        if changed:
            if self._write_after_replay and self._device.replaying:
                self._replay_write_pending = True
                return
            self.async_write_ha_state()

    @callback
    def _replay_done(self) -> None:
        if self._replay_write_pending:
            self._replay_write_pending = False
            self.async_write_ha_state()

    def _apply(self, values: dict[str, Any]) -> bool:
        """Update attributes from values; True when the state changed."""
        raise NotImplementedError


MEASURED = {OPT_MEASURED_POWER: "measured_power", OPT_MEASURED_ENERGY: "measured_energy"}


class MeasuredEntity(EnOceanEntity):
    """An actuator entity that shows power and energy of a meter on the same load.

    A switching actuator (FSR14) has no measurement; the meter (F3Z14D) is a device of its own.
    The link is display only: the readings stay with the meter (the energy dashboard uses it),
    nothing is created twice.
    """

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        linked = [e for opt in MEASURED if (e := self._device.options.get(opt))]
        if linked:
            self.async_on_remove(
                async_track_state_change_event(self.hass, linked, self._measured_changed)
            )

    @callback
    def _measured_changed(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data["old_state"], event.data["new_state"]
        if old is None or new is None or old.state != new.state:
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        attributes: dict[str, Any] = {}
        for opt, name in MEASURED.items():
            entity_id = self._device.options.get(opt)
            state = self.hass.states.get(entity_id) if entity_id else None
            if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                continue
            try:
                attributes[name] = float(state.state)
            except ValueError:
                continue
            if unit := state.attributes.get("unit_of_measurement"):
                attributes[f"{name}_unit"] = unit
        return attributes or None
