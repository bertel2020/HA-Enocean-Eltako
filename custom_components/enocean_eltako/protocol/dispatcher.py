"""Central dispatcher: every gateway feeds it, devices subscribe by sender ID.

The same telegram often arrives twice: over two gateways, as a repeated radio telegram, or
from a bus actor once on the bus and once as its radio alias. A telegram identical to the
previous one from the same sender within DEDUP_WINDOW is dropped. Only the previous one
counts, so press - release - press of a rocker (a fast double press) all get through.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .telegram import RadioTelegram

_LOGGER = logging.getLogger(__name__)

DEDUP_WINDOW = 0.2  # seconds
WILDCARD = None


@dataclass(frozen=True, slots=True)
class ReceivedTelegram:
    """A telegram plus where and when it arrived."""

    telegram: RadioTelegram
    gateway: str  # config entry ID of the receiving gateway
    timestamp: float  # time.time()
    sender: int  # canonical sender ID (alias resolved)
    duplicate: bool = False


Listener = Callable[[ReceivedTelegram], None]


@dataclass
class DispatcherStats:
    received: int = 0
    duplicates: int = 0
    unknown: int = 0
    per_gateway: dict[str, int] = field(default_factory=dict)
    dispatch_time: float = 0.0  # seconds spent in listeners, summed

    def as_dict(self) -> dict[str, object]:
        return {
            "received": self.received,
            "duplicates": self.duplicates,
            "unknown": self.unknown,
            "per_gateway": dict(self.per_gateway),
            "avg_dispatch_ms": round(
                1000 * self.dispatch_time / max(self.received - self.duplicates, 1), 3
            ),
        }


class Dispatcher:
    """Routes telegrams to listeners by sender ID in constant time."""

    def __init__(
        self, *, window: float = DEDUP_WINDOW, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._window = window
        self._clock = clock
        self._listeners: dict[int | None, list[Listener]] = {}
        self._monitors: list[Listener] = []
        self._unknown: list[Listener] = []
        self._aliases: dict[int, int] = {}
        # per sender: the last telegram's key, clock() and wall time of reception
        self._last: dict[int, tuple[tuple[int, bytes, int], float, float]] = {}
        self.stats = DispatcherStats()

    def add_listener(self, sender: int | None, listener: Listener) -> Callable[[], None]:
        """Listen to one sender, or to every telegram with sender=WILDCARD."""
        self._listeners.setdefault(sender, []).append(listener)

        def remove() -> None:
            listeners = self._listeners.get(sender, [])
            if listener in listeners:
                listeners.remove(listener)
            if not listeners:
                self._listeners.pop(sender, None)

        return remove

    def add_monitor(self, listener: Listener) -> Callable[[], None]:
        """Every telegram including duplicates (telegram monitor)."""
        self._monitors.append(listener)
        return lambda: self._monitors.remove(listener)

    def add_unknown_listener(self, listener: Listener) -> Callable[[], None]:
        """Telegrams no device listens to (discovery)."""
        self._unknown.append(listener)
        return lambda: self._unknown.remove(listener)

    def add_alias(self, alias: int, sender: int) -> Callable[[], None]:
        """Treat telegrams from alias as coming from sender (bus actor radio alias)."""
        self._aliases[alias] = sender

        def remove() -> None:
            self._aliases.pop(alias, None)

        return remove

    def is_known(self, sender: int) -> bool:
        return self._aliases.get(sender, sender) in self._listeners

    def dispatch(
        self, gateway: str, telegram: RadioTelegram, timestamp: float | None = None
    ) -> ReceivedTelegram:
        """Feed one received telegram; returns it with the duplicate flag set.

        timestamp: when it was really received (replayed by the Device Proxy app).
        """
        now = self._clock()
        received_at = timestamp or time.time()
        sender = self._aliases.get(telegram.sender, telegram.sender)
        # status low nibble = repeater count, differs between original and repetition
        key = (telegram.rorg, telegram.data, telegram.status & 0xF0)
        last = self._last.get(sender)
        if last is None or last[0] != key:
            duplicate = False
        elif timestamp is not None:
            # replayed after a restart: minutes of telegrams arrive within milliseconds, so
            # compare the reception times, not the arrival
            duplicate = abs(received_at - last[2]) < self._window
        else:
            duplicate = now - last[1] < self._window
        if not duplicate:
            self._last[sender] = (key, now, received_at)
        received = ReceivedTelegram(telegram, gateway, received_at, sender, duplicate)

        self.stats.received += 1
        self.stats.per_gateway[gateway] = self.stats.per_gateway.get(gateway, 0) + 1
        self._call(self._monitors, received)
        if duplicate:
            self.stats.duplicates += 1
            return received

        start = self._clock()
        targets = self._listeners.get(sender)
        if targets:
            self._call(targets, received)
        else:
            self.stats.unknown += 1
            self._call(self._unknown, received)
        self._call(self._listeners.get(WILDCARD, ()), received)
        self.stats.dispatch_time += self._clock() - start
        return received

    @staticmethod
    def _call(listeners: Iterable[Listener], received: ReceivedTelegram) -> None:
        for listener in list(listeners):
            try:
                listener(received)
            except Exception:
                _LOGGER.exception("Error in listener for %s", received.telegram)
