"""Telegram monitor (E4)."""

from custom_components.enocean_eltako.protocol.dispatcher import ReceivedTelegram
from custom_components.enocean_eltako.protocol.monitor import TelegramMonitor
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

T = RadioTelegram(Rorg.RPS, b"\x70", 0x00216343, 0x30, dbm=-61)


def test_ring_buffer_and_history() -> None:
    m = TelegramMonitor(size=3)
    for i in range(5):
        m.received(ReceivedTelegram(T, "gw1", 1000.0 + i, T.sender))
    m.sent("gw2", RadioTelegram(Rorg.RPS, b"\x10", 0xFFB74481, 0x30))
    assert len(m.history("gw1")) == 3
    assert m.history("gw1")[0].timestamp == 1002.0
    assert [e.direction for e in m.history()][-1] == "tx"
    assert len(m.history(limit=2)) == 2
    assert m.received_since("gw1", 1003.0) == 2
    assert m.received_since("gw2", 0.0) == 0  # sent ones do not count


def test_entry_as_dict_and_subscribe() -> None:
    m = TelegramMonitor()
    got = []
    unsubscribe = m.subscribe(got.append)
    m.received(ReceivedTelegram(T, "gw1", 0.0, T.sender, duplicate=True))
    unsubscribe()
    m.received(ReceivedTelegram(T, "gw1", 1.0, T.sender))
    assert len(got) == 1
    assert got[0].as_dict() == {
        "time": "1970-01-01T00:00:00.000+00:00",
        "gateway": "gw1",
        "dir": "rx",
        "rorg": "F6",
        "data": "70",
        "sender": "00-21-63-43",
        "status": "30",
        "destination": "FF-FF-FF-FF",
        "dbm": -61,
        "duplicate": True,
    }
