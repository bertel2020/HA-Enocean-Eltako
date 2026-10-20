"""Shutters and blinds (FSB): G5-3F-7F status, H5-3F-7F commands with run time.

Two sender profiles can be taught in at the same time: the controller (H5-3F-7F, run time
in the telegram) and the direction rocker (F6-02-01: 0x70 up, 0x50 down; the same direction
again stops). The routing option picks which one moves the cover (controller,
direction_rocker or both); positions use the controller when present, otherwise the rocker
with a timed stop.

Position and inaccuracy follow cover_position.CoverPosition (I6), including vent slots of
shutters (position 1 = down, slots open) and the slats of blinds (tilt position, turned with
the 100 ms resolution of the controller command). Commands to 0 % or 100 % are
always full runs with margin, which renews the anchor. Calibration strategy per cover:
passive (anchor only when fully opened or closed anyway) or before an uncertain move (drive to
the nearer end first when the inaccuracy exceeds the threshold). The calibrate button and the
action enocean_eltako.calibrate_cover drive to the nearer end and back.

VLD blinds (D2-05) report their position themselves; VldCover only sends position, stop and
query commands and shows the reply (D2-05 counts closed percent, HA open percent).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import EnOceanEltakoConfigEntry
from .catalog import (
    CONTROLLER,
    DIRECTION_ROCKER,
    OPT_CALIBRATION,
    OPT_CHANNEL,
    OPT_ROUTING,
    OPT_TENTHS,
    OPT_TILT_TIME,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
    OPT_VENT_TIME,
)
from .const import DOMAIN
from .cover_position import CoverPosition
from .device import EnOceanDevice
from .entity import EnOceanEntity
from .protocol.eep import vld
from .protocol.eep.eltako import shutter

PARALLEL_UPDATES = 0

SERVICE_CALIBRATE = "calibrate_cover"

DEFAULT_TRAVEL_TIME = 30.0
DEFAULT_THRESHOLD = 10.0  # inaccuracy points before an uncertain move triggers calibration
ANCHOR_WAIT_EXTRA = 10.0  # seconds to wait for the anchor beyond the full run time


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    for subentry_id, device in entry.runtime_data.devices.items():
        if device.model.kind == "vld_cover":
            async_add_entities([VldCover(device)], config_subentry_id=subentry_id)
        elif Platform.COVER in device.model.platforms:
            async_add_entities([EnOceanCover(device)], config_subentry_id=subentry_id)
    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_CALIBRATE, None, "async_calibrate"
    )


class EnOceanCover(EnOceanEntity, CoverEntity, RestoreEntity):
    _attr_name = None
    _assume_until_heard = True
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "cover")
        self.position = CoverPosition(
            float(device.options.get(OPT_TIME_OPENS) or DEFAULT_TRAVEL_TIME),
            float(device.options.get(OPT_TIME_CLOSES) or DEFAULT_TRAVEL_TIME),
            vent_time=float(device.options.get(OPT_VENT_TIME) or 0),
            tilt_time=float(device.options.get(OPT_TILT_TIME) or 0),
        )
        if self.position.is_blind:
            self._attr_device_class = CoverDeviceClass.BLIND
            self._attr_supported_features = (
                self._attr_supported_features
                | CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.STOP_TILT
                | CoverEntityFeature.SET_TILT_POSITION
            )
        self._before_move = device.options.get(OPT_CALIBRATION) == "before_move"
        self._tenths = bool(device.options.get(OPT_TENTHS))
        self._attr_is_opening = False
        self._attr_is_closing = False
        routing = device.options.get(OPT_ROUTING, CONTROLLER.id)
        self._via = [
            p
            for p in (CONTROLLER.id, DIRECTION_ROCKER.id)
            if device.has_sender(p) and routing in (p, "both")
        ] or list(device.senders)
        self._cancel_stop: Callable[[], None] | None = None
        self._rocker_direction: bytes | None = None
        self._anchored = asyncio.Event()
        self._last_calibrated: str | None = None
        device.cover_entity = self

    @property
    def current_cover_position(self) -> int | None:
        return self.position.position

    @property
    def current_cover_tilt_position(self) -> int | None:
        return self.position.tilt if self.position.is_blind else None

    @property
    def is_closed(self) -> bool | None:
        return None if self.position.position is None else self.position.position == 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "inaccuracy": round(self.position.inaccuracy, 1),
            "last_calibrated": self._last_calibrated,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self.position.position = last.attributes.get("current_position")
            if self.position.is_blind:
                self.position.tilt = last.attributes.get("current_tilt_position")
            if (inaccuracy := last.attributes.get("inaccuracy")) is not None:
                self.position.inaccuracy = float(inaccuracy)
            self._last_calibrated = last.attributes.get("last_calibrated")
        self.position.restarted()  # the restored position is uncertain

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_timed_stop()

    async def async_open_cover(self, **kwargs: Any) -> None:
        self._full_run(up=True)

    async def async_close_cover(self, **kwargs: Any) -> None:
        self._full_run(up=False)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        self._cancel_timed_stop()
        for profile in self._via:
            if profile == CONTROLLER.id:
                self._device.send(shutter.encode_command(shutter.STOP), profile=profile, key="move")
            elif self._rocker_direction is not None:
                # the same direction again stops a cover moved by the direction rocker
                self._device.press(profile, self._rocker_direction)
        self._rocker_direction = None

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        target = kwargs[ATTR_POSITION]
        if target >= 100 or target <= 0:
            self._full_run(up=target >= 100)
            return
        if self.position.position is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cover_position_unknown"
            )
        if self._before_move and self.position.inaccuracy > DEFAULT_THRESHOLD:
            await self._drive_to_anchor(self.position.nearer_end())
        self._partial_run(target)

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        await self.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 100})

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        await self.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 0})

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        await self.async_stop_cover()

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Turn the slats only: a short run in one direction (100 ms resolution)."""
        if self.position.tilt is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cover_position_unknown"
            )
        run = self.position.tilt_run(kwargs[ATTR_TILT_POSITION])
        if run is not None:
            up, seconds = run
            self._run(shutter.UP if up else shutter.DOWN, seconds, full=False)

    async def async_calibrate(self) -> None:
        """Drive to the nearer end (anchor) and back to the previous position."""
        previous = self.position.position
        end = self.position.nearer_end()
        if await self._drive_to_anchor(end) and previous not in (None, 0, 100, end):
            self._partial_run(previous)

    async def _drive_to_anchor(self, end: int) -> bool:
        self._anchored.clear()
        self._full_run(up=end == 100)
        timeout = self.position.full_run_time(up=end == 100) + ANCHOR_WAIT_EXTRA
        with contextlib.suppress(TimeoutError):
            async with asyncio.timeout(timeout):
                await self._anchored.wait()
                return True
        self.position.no_answer()
        self._changed()
        return False

    def _full_run(self, up: bool) -> None:
        self._run(shutter.UP if up else shutter.DOWN, self.position.full_run_time(up), full=True)

    def _partial_run(self, target: int) -> None:
        run = self.position.partial_run(target)
        if run is not None:
            up, seconds = run
            self._run(shutter.UP if up else shutter.DOWN, seconds, full=False)

    def _run(self, command: int, seconds: float, full: bool) -> None:
        self._cancel_timed_stop()
        controller = self._device.has_sender(CONTROLLER.id)
        # positions: controller when present; open/close: the configured routing
        profiles = self._via if full else ([CONTROLLER.id] if controller else self._via)
        for profile in profiles:
            if profile == CONTROLLER.id:
                self._device.send(
                    shutter.encode_command(command, round(seconds, 1), tenths=self._tenths),
                    profile=profile,
                    key="move",
                )
            else:
                self._rocker_direction = self._device.rocker_button(command == shutter.UP)
                self._device.press(profile, self._rocker_direction)
                if not full:
                    self._cancel_stop = async_call_later(self.hass, seconds, self._timed_stop)

    @callback
    def _timed_stop(self, _now: Any) -> None:
        self._cancel_stop = None
        if self._rocker_direction is not None:
            self._device.press(DIRECTION_ROCKER.id, self._rocker_direction)
            self._rocker_direction = None

    def _cancel_timed_stop(self) -> None:
        if self._cancel_stop is not None:
            self._cancel_stop()
            self._cancel_stop = None

    def _changed(self) -> None:
        self._device._notify_stats()  # accuracy sensor follows

    def _mark_anchor(self) -> None:
        self._last_calibrated = dt_util.utcnow().isoformat()
        self._anchored.set()

    def _apply(self, values: dict[str, Any]) -> bool:
        before = (
            self.position.position,
            round(self.position.inaccuracy, 1),
            self._attr_is_opening,
            self._attr_is_closing,
        )
        if (state := values.get("state")) is not None:
            self._attr_is_opening = state == "opening"
            self._attr_is_closing = state == "closing"
            if state in ("open", "closed"):
                self._rocker_direction = None  # stopped at the end position by itself
                self.position.anchor(100 if state == "open" else 0)
                self._mark_anchor()
        elif "driven_time" in values:
            self._attr_is_opening = self._attr_is_closing = False
            self.position.driven(values["driven_time"], up=values["direction"] == "up")
            if self.position.inaccuracy == 0:
                self._mark_anchor()
        after = (
            self.position.position,
            round(self.position.inaccuracy, 1),
            self._attr_is_opening,
            self._attr_is_closing,
        )
        if before != after:
            self._changed()
        return before != after


class VldCover(EnOceanEntity, CoverEntity, RestoreEntity):
    """D2-05 blind or shutter: drives to a position itself and reports it."""

    _attr_name = None
    _assume_until_heard = True
    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, device: EnOceanDevice) -> None:
        super().__init__(device, "cover")
        self._channel = int(device.options.get(OPT_CHANNEL, 0))
        self._attr_current_cover_position: int | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            position = last.attributes.get("current_position")
            self._attr_current_cover_position = position if isinstance(position, int) else None

    @property
    def is_closed(self) -> bool | None:
        position = self._attr_current_cover_position
        return None if position is None else position == 0

    def _drive(self, open_percent: int) -> None:
        self._device.send(vld.encode_blind_position(self._channel, 100 - open_percent), key="move")

    async def async_open_cover(self, **kwargs: Any) -> None:
        self._drive(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        self._drive(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        self._drive(int(kwargs[ATTR_POSITION]))

    async def async_stop_cover(self, **kwargs: Any) -> None:
        self._device.send(vld.encode_blind_stop(self._channel), key="move")

    async def async_calibrate(self) -> None:
        """The blind measures its position itself; nothing to calibrate."""

    def _apply(self, values: dict[str, Any]) -> bool:
        closed = vld.blind_status(values, self._channel)
        if closed is None or 100 - closed == self._attr_current_cover_position:
            return False
        self._attr_current_cover_position = 100 - closed
        return True
