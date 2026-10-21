"""Shutter position model (I6): position from driven times, anchors, inaccuracy.

Separate travel times up and down. Anchors set the position for sure and the inaccuracy to 0:
the end-position status 0x70/0x50, and a driven time in one direction of at least the full
travel time plus margin (the usual case after controller commands, which the FSB answers with
the driven time). Every partial run adds inaccuracy (1 point plus 3 % of the distance), so do
a restart and a command without answer. No self-learning travel times: the actuator never
reports when the motor physically stops.

Two refinements of the travel, both part of the full travel time:
- Vent slots (shutters): the last vent_time seconds down only close the slots. Position 0 is
  "closed, slots closed", position 1 "down, slots open"; 1...100 is the height in between.
- Slats (blinds): every run first turns the slats (tilt_time for a full turn: closed when
  going down, open when going up); only the rest of the time changes the height.
"""

from __future__ import annotations

from dataclasses import dataclass

MARGIN_SHARE = 0.10  # safety margin on a full run: 10 % of the travel time ...
MARGIN_MIN = 2.0  # ... but at least 2 s
PARTIAL_BASE = 1.0  # inaccuracy points per partial run
PARTIAL_SHARE = 0.03  # plus this share of the distance in points
RESTART_PENALTY = 10.0
NO_ANSWER_PENALTY = 20.0
MAX_INACCURACY = 100.0
SLOTS_OPEN = 1  # vent shutters: position "down, slots open"


def margin(travel_time: float) -> float:
    return max(MARGIN_MIN, travel_time * MARGIN_SHARE)


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


@dataclass
class CoverPosition:
    time_opens: float
    time_closes: float
    position: int | None = None  # 0 closed ... 100 open
    inaccuracy: float = MAX_INACCURACY
    vent_time: float = 0.0  # shutters: seconds of the down run that only close the slots
    tilt_time: float = 0.0  # blinds: seconds for a full turn of the slats
    tilt: int | None = None  # blinds: 0 slats closed ... 100 open

    @property
    def is_blind(self) -> bool:
        return self.tilt_time > 0

    @property
    def has_vent(self) -> bool:
        return self.vent_time > 0 and not self.is_blind

    def full_run_time(self, up: bool) -> float:
        travel = self.time_opens if up else self.time_closes
        return travel + margin(travel)

    def _height_time(self, up: bool) -> float:
        """Seconds for the height alone (travel time without slat or slot movement)."""
        travel = self.time_opens if up else self.time_closes
        extra = self.tilt_time if self.is_blind else self.vent_time if self.has_vent else 0.0
        return max(0.1, travel - extra)

    def _height(self, position: int) -> float:
        if not self.has_vent:
            return float(position)
        return 0.0 if position <= SLOTS_OPEN else (position - SLOTS_OPEN) * 100 / 99

    def _position(self, height: float, slots_closed: bool) -> int:
        if not self.has_vent:
            return round(_clamp(height))
        if height <= 0:
            return 0 if slots_closed else SLOTS_OPEN
        return SLOTS_OPEN + round(_clamp(height) * 99 / 100)

    def anchor(self, position: int) -> None:
        self.position = position
        self.inaccuracy = 0.0
        if self.is_blind and position in (0, 100):
            self.tilt = position

    def driven(self, seconds: float, up: bool) -> None:
        """The actuator reports the time it drove after a stop."""
        travel = self.time_opens if up else self.time_closes
        if seconds >= travel + margin(travel) - 0.05:
            self.anchor(100 if up else 0)
            return
        if self.position is None:
            return
        rest = seconds
        if self.is_blind:
            rest = self._turn_slats(rest, up)
        elif self.has_vent and up and self.position == 0:
            rest -= self.vent_time  # the slots open first
            if rest < 0:
                self.position = SLOTS_OPEN if seconds >= self.vent_time / 2 else 0
                self._add_inaccuracy(0)
                return
        height_time = self._height_time(up)
        delta = max(0.0, rest) / height_time * 100
        target = self._height(self.position) + (delta if up else -delta)
        overrun_time = -target / 100 * height_time if target < 0 else 0.0
        slots_closed = overrun_time >= self.vent_time - 0.05
        self.position = self._position(target, slots_closed)
        if (target > 100 and self.position == 100) or (target < 0 and self.position == 0):
            return  # drove beyond an end: counts as overrun, keeps the inaccuracy
        self._add_inaccuracy(delta)

    def _turn_slats(self, seconds: float, up: bool) -> float:
        """Blinds: the slats turn before the height changes; returns the time left."""
        tilt = self.tilt if self.tilt is not None else (0 if up else 100)
        needed = (100 - tilt if up else tilt) / 100 * self.tilt_time
        turn = min(seconds, needed)
        step = turn / self.tilt_time * 100
        self.tilt = round(_clamp(tilt + (step if up else -step)))
        return seconds - turn

    def _add_inaccuracy(self, delta: float) -> None:
        self.inaccuracy = min(
            MAX_INACCURACY, self.inaccuracy + PARTIAL_BASE + delta * PARTIAL_SHARE
        )

    def partial_run(self, target: int) -> tuple[bool, float] | None:
        """Direction and time to reach target from the current position; None if unknown."""
        if self.position is None or target == self.position:
            return None
        up = target > self.position
        seconds = abs(self._height(target) - self._height(self.position)) / 100
        seconds *= self._height_time(up)
        if self.is_blind:
            tilt = self.tilt if self.tilt is not None else (0 if up else 100)
            seconds += (100 - tilt if up else tilt) / 100 * self.tilt_time
        elif self.has_vent and up and self.position == 0:
            seconds += self.vent_time
        return up, seconds

    def tilt_run(self, target: int) -> tuple[bool, float] | None:
        """Blinds: direction and time to turn the slats to target; None if unknown."""
        if not self.is_blind or self.tilt is None or target == self.tilt:
            return None
        up = target > self.tilt
        return up, abs(target - self.tilt) / 100 * self.tilt_time

    def nearer_end(self) -> int:
        """End to drive to for calibration; unknown position: open, never close unasked."""
        return 100 if self.position is None or self.position >= 50 else 0

    def restarted(self) -> None:
        self.inaccuracy = min(MAX_INACCURACY, self.inaccuracy + RESTART_PENALTY)

    def no_answer(self) -> None:
        self.inaccuracy = min(MAX_INACCURACY, self.inaccuracy + NO_ANSWER_PENALTY)
