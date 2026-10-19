"""Dispatcher routing and deduplication."""

from custom_components.enocean_eltako.protocol.dispatcher import WILDCARD, Dispatcher
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

SWITCH = RadioTelegram(Rorg.RPS, b"\x70", 0x00216343, 0x30)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_routes_by_sender_and_wildcard() -> None:
    d = Dispatcher()
    got, every, unknown = [], [], []
    d.add_listener(0x00216343, got.append)
    d.add_listener(WILDCARD, every.append)
    d.add_unknown_listener(unknown.append)
    d.dispatch("gw1", SWITCH)
    d.dispatch("gw1", RadioTelegram(Rorg.RPS, b"\x50", 0x01020304, 0x30))
    assert [r.telegram for r in got] == [SWITCH]
    assert len(every) == 2
    assert [r.sender for r in unknown] == [0x01020304]
    assert d.stats.unknown == 1


def test_duplicate_within_window_is_dropped() -> None:
    clock = Clock()
    d = Dispatcher(clock=clock)
    got, monitor = [], []
    d.add_listener(SWITCH.sender, got.append)
    d.add_monitor(monitor.append)
    d.dispatch("gw1", SWITCH)
    clock.now += 0.05
    # repeated telegram over the second gateway, repeater count 1 in status
    dup = d.dispatch("gw2", RadioTelegram(Rorg.RPS, b"\x70", SWITCH.sender, 0x31))
    assert dup.duplicate
    assert len(got) == 1
    assert [r.duplicate for r in monitor] == [False, True]
    clock.now += 0.3
    d.dispatch("gw1", SWITCH)
    assert len(got) == 2
    assert d.stats.as_dict()["duplicates"] == 1
    assert d.stats.per_gateway == {"gw1": 2, "gw2": 1}


def test_different_data_is_not_a_duplicate() -> None:
    d = Dispatcher(clock=Clock())
    got = []
    d.add_listener(SWITCH.sender, got.append)
    d.dispatch("gw1", SWITCH)
    d.dispatch("gw1", RadioTelegram(Rorg.RPS, b"\x00", SWITCH.sender, 0x20))
    assert len(got) == 2


def test_alias_maps_to_canonical_sender_and_dedups() -> None:
    clock = Clock()
    d = Dispatcher(clock=clock)
    got = []
    bus, radio = 0x00000012, 0xFFAA8012
    d.add_listener(bus, got.append)
    d.add_alias(radio, bus)
    status = RadioTelegram(Rorg.BS4, bytes.fromhex("01000009"), bus)
    d.dispatch("fgw14", status)
    d.dispatch("fam_usb", RadioTelegram(Rorg.BS4, status.data, radio))
    assert len(got) == 1
    assert got[0].sender == bus
    assert d.is_known(radio)


def test_remove_listener_and_failing_listener() -> None:
    d = Dispatcher()
    got = []

    def boom(_):
        raise RuntimeError

    d.add_listener(SWITCH.sender, boom)
    remove = d.add_listener(SWITCH.sender, got.append)
    d.dispatch("gw1", SWITCH)
    assert len(got) == 1
    remove()
    assert d.is_known(SWITCH.sender)  # boom still listens
