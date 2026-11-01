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


def test_release_without_press_is_ignored() -> None:
    d, clock, events = make()
    d.release()
    clock.advance(1)
    assert events == []


def test_second_button_ends_the_hold_of_the_first() -> None:
    d, clock, events = make()
    d.press("a0")
    d.press("b0")
    clock.advance(0.7)
    assert [e for e in events if e[1] == "long_press"] == [("b0", "long_press")]


def test_combined_press_reports_both_buttons() -> None:
    d, _clock, events = make()
    d.press("a0", second="b0")
    assert ("a0", "combined_press") in events
    assert ("b0", "combined_press") in events


def test_pending_short_press_of_another_button_is_emitted_on_next_press() -> None:
    d, _clock, events = make()
    d.press("a0")
    d.release()
    d.press("b0")
    assert ("a0", "short_press") in events


def test_repeated_telegram_while_held_does_not_restart_the_hold() -> None:
    d, clock, events = make()
    d.press("a0")
    clock.advance(0.3)
    d.press("a0")
    clock.advance(0.4)
    assert events.count(("a0", "long_press")) == 1


def test_cancel_drops_pending_short_press_and_hold() -> None:
    d, clock, events = make()
    d.press("a0")
    d.release()
    d.cancel()
    d.press("b0")
    d.cancel()
    clock.advance(2)
    assert ("a0", "short_press") not in events
    assert ("b0", "long_press") not in events
