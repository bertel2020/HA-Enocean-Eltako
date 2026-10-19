"""Gesture detector with a manual clock."""

from custom_components.enocean_eltako.gestures import GestureDetector


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.timers: list[list] = []

    def call_later(self, delay, action):
        timer = [self.now + delay, action, True]
        self.timers.append(timer)

        def cancel():
            timer[2] = False

        return cancel

    def advance(self, seconds: float) -> None:
        self.now += seconds
        for timer in sorted(self.timers, key=lambda t: t[0]):
            if timer[2] and timer[0] <= self.now:
                timer[2] = False
                timer[1]()


def make():
    clock, events = Clock(), []
    detector = GestureDetector(lambda b, t, d: events.append((b, t)), clock.call_later)
    return detector, clock, events


def test_short_press_after_window() -> None:
    d, clock, events = make()
    d.press("b0")
    clock.advance(0.1)
    d.release()
    assert ("b0", "short_press") not in events
    clock.advance(0.5)
    assert events == [("b0", "pressed"), ("b0", "released"), ("b0", "short_press")]


def test_long_press_fires_while_held() -> None:
    d, clock, events = make()
    d.press("a0")
    clock.advance(0.7)
    assert ("a0", "long_press") in events
    d.release()
    clock.advance(1)
    assert ("a0", "short_press") not in events


def test_double_press() -> None:
    d, clock, events = make()
    for _ in range(2):
        d.press("b1")
        clock.advance(0.05)
        d.release()
        clock.advance(0.1)
    clock.advance(1)
    assert ("b1", "double_press") in events
    assert ("b1", "short_press") not in events


def test_other_button_ends_pending_short_and_combined() -> None:
    d, clock, events = make()
    d.press("a0")
    d.release()
    d.press("b0", second="a1")
    assert ("a0", "short_press") in events
    assert ("b0", "combined_press") in events and ("a1", "combined_press") in events
