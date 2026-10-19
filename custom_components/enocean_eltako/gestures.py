"""E6: rocker gestures from press/release telegrams.

pressed / released for every telegram, short_press after the double-press window,
double_press for two short presses within it, long_press once the button is held past the
long-press threshold, combined_press when one telegram reports two buttons. A release
telegram does not say which button was released; it belongs to the last pressed one.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

DEFAULT_LONG_PRESS = 0.6  # seconds held
DEFAULT_DOUBLE_PRESS = 0.4  # seconds between two short presses

EVENT_TYPES = ["pressed", "released", "short_press", "long_press", "double_press", "combined_press"]

Emit = Callable[[str, str, dict[str, Any]], None]  # button, event type, data
CallLater = Callable[[float, Callable[[], None]], Callable[[], None]]  # returns cancel


class GestureDetector:
    def __init__(
        self,
        emit: Emit,
        call_later: CallLater,
        long_press: float = DEFAULT_LONG_PRESS,
        double_press: float = DEFAULT_DOUBLE_PRESS,
    ) -> None:
        self._emit = emit
        self._call_later = call_later
        self._long_press = long_press
        self._double_press = double_press
        self._pressed: str | None = None
        self._long_fired = False
        self._double_candidate = False
        self._cancel_long: Callable[[], None] | None = None
        self._pending_short: tuple[str, Callable[[], None]] | None = None

    def press(self, button: str, second: str | None = None) -> None:
        if self._pressed is not None and self._pressed != button:
            self._finish_hold()
        self._emit(button, "pressed", {})
        if second is not None:
            self._emit(button, "combined_press", {"other": second})
            self._emit(second, "combined_press", {"other": button})
        if self._pending_short is not None:
            pending_button, cancel = self._pending_short
            self._pending_short = None
            cancel()
            if pending_button == button:
                self._double_candidate = True
            else:
                self._emit(pending_button, "short_press", {})
        if self._pressed == button:
            return  # repeated telegram while held
        self._pressed = button
        self._long_fired = False
        self._cancel_long = self._call_later(self._long_press, self._long_elapsed)

    def release(self) -> None:
        button = self._pressed
        if button is None:
            return
        self._emit(button, "released", {})
        self._finish_hold()
        if self._long_fired:
            self._double_candidate = False
            return
        if self._double_candidate:
            self._double_candidate = False
            self._emit(button, "double_press", {})
            return
        self._pending_short = (button, self._call_later(self._double_press, self._short_elapsed))

    def cancel(self) -> None:
        self._finish_hold()
        if self._pending_short is not None:
            self._pending_short[1]()
            self._pending_short = None

    def _finish_hold(self) -> None:
        if self._cancel_long is not None:
            self._cancel_long()
            self._cancel_long = None
        self._pressed = None

    def _long_elapsed(self) -> None:
        self._cancel_long = None
        if self._pressed is not None:
            self._long_fired = True
            self._emit(self._pressed, "long_press", {})

    def _short_elapsed(self) -> None:
        if self._pending_short is not None:
            button = self._pending_short[0]
            self._pending_short = None
            self._emit(button, "short_press", {})
