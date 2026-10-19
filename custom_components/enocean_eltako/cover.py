"""Shutters and blinds (FSB): G5-3F-7F status, H5-3F-7F commands with run time.

Two sender profiles can be taught in at the same time: the controller (H5-3F-7F, run time
in the telegram) and the direction rocker (F6-02-01: 0x70 up, 0x50 down; the same direction
again stops). The routing option picks which one moves the cover (controller,
direction_rocker or both); positions use the controller when present, otherwise the rocker
with a timed stop.

Position and inaccuracy follow cover_position.CoverPosition (I6). Commands to 0 % or 100 % are
always full runs with margin, which renews the anchor. Calibration strategy per cover:
passive (anchor only when fully opened or closed anyway) or before an uncertain move (drive to
the nearer end first when the inaccuracy exceeds the threshold). The calibrate button and the
action enocean_eltako.calibrate_cover drive to the nearer end and back.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
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
    OPT_ROUTING,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
    ROCKER_PRESS_DOWN,
    ROCKER_PRESS_UP,
)
from .const import DOMAIN
from .cover_position import CoverPosition
from .device import EnOceanDevice
from .entity import EnOceanEntity
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
        if Platform.COVER in device.model.platforms:
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
        )
        self._before_move = device.options.get(OPT_CALIBRATION) == "before_move"
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
                    shutter.encode_command(command, round(seconds, 1)),
                    profile=profile,
                    key="move",
                )
            else:
                self._rocker_direction = (
                    ROCKER_PRESS_UP if command == shutter.UP else ROCKER_PRESS_DOWN
                )
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
