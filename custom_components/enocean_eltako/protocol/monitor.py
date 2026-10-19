"""Telegram monitor (E4): ring buffer per gateway of received and sent telegrams."""

from __future__ import annotations

import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .dispatcher import ReceivedTelegram
from .ids import format_id
from .telegram import RadioTelegram

_LOGGER = logging.getLogger(__name__)

BUFFER_SIZE = 500


@dataclass(frozen=True, slots=True)
class MonitorEntry:
    timestamp: float
    gateway: str
    direction: str  # "rx" | "tx"
    telegram: RadioTelegram
    duplicate: bool = False

    def as_dict(self) -> dict[str, Any]:
        """JSON form; also the line format of captures and test fixtures."""
        t = self.telegram
        return {
            "time": datetime.fromtimestamp(self.timestamp, UTC).isoformat(timespec="milliseconds"),
            "gateway": self.gateway,
            "dir": self.direction,
            "rorg": f"{t.rorg:02X}",
            "data": t.data.hex().upper(),
            "sender": format_id(t.sender),
            "status": f"{t.status:02X}",
            "destination": format_id(t.destination),
            "dbm": t.dbm,
            "duplicate": self.duplicate,
        }


Subscriber = Callable[[MonitorEntry], None]


class TelegramMonitor:
    def __init__(self, size: int = BUFFER_SIZE) -> None:
        self._size = size
        self._buffers: dict[str, deque[MonitorEntry]] = {}
        self._subscribers: list[Subscriber] = []

    def received(self, received: ReceivedTelegram) -> None:
        self._add(
            MonitorEntry(
                received.timestamp, received.gateway, "rx", received.telegram, received.duplicate
            )
        )

    def sent(self, gateway: str, telegram: RadioTelegram) -> None:
        self._add(MonitorEntry(time.time(), gateway, "tx", telegram))

    def history(self, gateway: str | None = None, limit: int | None = None) -> list[MonitorEntry]:
        """Oldest first; all gateways merged by time when gateway is None."""
        if gateway is not None:
            entries = list(self._buffers.get(gateway, ()))
        else:
            entries = sorted(
                (e for buf in self._buffers.values() for e in buf), key=lambda e: e.timestamp
            )
        return entries[-limit:] if limit else entries

    def subscribe(self, subscriber: Subscriber) -> Callable[[], None]:
        self._subscribers.append(subscriber)
        return lambda: self._subscribers.remove(subscriber)

    def clear(self, gateway: str) -> None:
        self._buffers.pop(gateway, None)

    def _add(self, entry: MonitorEntry) -> None:
        buffer = self._buffers.get(entry.gateway)
        if buffer is None:
            buffer = self._buffers[entry.gateway] = deque(maxlen=self._size)
        buffer.append(entry)
        for subscriber in list(self._subscribers):
            try:
                subscriber(entry)
            except Exception:
                _LOGGER.exception("Error in telegram monitor subscriber")
