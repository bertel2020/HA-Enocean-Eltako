"""Shutter position model (I6): position from driven times, anchors, inaccuracy.

Separate travel times up and down. Anchors set the position for sure and the inaccuracy to 0:
the end-position status 0x70/0x50, and a driven time in one direction of at least the full
travel time plus margin (the usual case after controller commands, which the FSB answers with
the driven time). Every partial run adds inaccuracy (1 point plus 3 % of the distance), so do
a restart and a command without answer. No self-learning travel times: the actuator never
reports when the motor physically stops.
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


def margin(travel_time: float) -> float:
    return max(MARGIN_MIN, travel_time * MARGIN_SHARE)


@dataclass
class CoverPosition:
    time_opens: float
    time_closes: float
    position: int | None = None  # 0 closed ... 100 open
    inaccuracy: float = MAX_INACCURACY

    def full_run_time(self, up: bool) -> float:
        travel = self.time_opens if up else self.time_closes
        return travel + margin(travel)

    def anchor(self, position: int) -> None:
        self.position = position
        self.inaccuracy = 0.0

    def driven(self, seconds: float, up: bool) -> None:
        """The actuator reports the time it drove after a stop."""
        travel = self.time_opens if up else self.time_closes
        if seconds >= travel + margin(travel) - 0.05:
            self.anchor(100 if up else 0)
            return
        if self.position is None:
            return
        delta = seconds / travel * 100
        target = self.position + (delta if up else -delta)
        self.position = round(max(0.0, min(100.0, target)))
        if self.position in (0, 100) and target != self.position:
            return  # drove beyond an end: counts as overrun, keeps the inaccuracy
        self.inaccuracy = min(
            MAX_INACCURACY, self.inaccuracy + PARTIAL_BASE + delta * PARTIAL_SHARE
        )

    def partial_run(self, target: int) -> tuple[bool, float] | None:
        """Direction and time to reach target from the current position; None if unknown."""
        if self.position is None or target == self.position:
            return None
        up = target > self.position
        travel = self.time_opens if up else self.time_closes
        return up, abs(target - self.position) / 100 * travel

    def nearer_end(self) -> int:
        return 100 if (self.position or 0) >= 50 else 0

    def restarted(self) -> None:
        self.inaccuracy = min(MAX_INACCURACY, self.inaccuracy + RESTART_PENALTY)

    def no_answer(self) -> None:
        self.inaccuracy = min(MAX_INACCURACY, self.inaccuracy + NO_ANSWER_PENALTY)
