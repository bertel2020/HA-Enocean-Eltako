"""Send queue per gateway (E9): priorities, minimum spacing, coalescing, confirmation.

Nothing writes to a gateway directly; everything goes through submit().
"""

from __future__ import annotations

import asyncio
import contextlib
import heapq
import itertools
import logging
import time
from collections.abc import Awaitable, Callable, Hashable
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

from .telegram import RadioTelegram

_LOGGER = logging.getLogger(__name__)

DEFAULT_DELAY = 0.01  # seconds between two telegrams
DEFAULT_CONFIRM_TIMEOUT = 1.0
MAX_RETRIES = 2
SEND_TIMEOUT = 5.0  # a write that hangs (blocked serial port) fails instead of stalling the queue


class Priority(IntEnum):
    SAFETY = 0  # central command with priority
    USER = 1  # operation from the UI or a switch
    AUTOMATION = 2  # automations and scenes
    BACKGROUND = 3  # status queries, teach-in


class SendResult(StrEnum):
    SENT = "sent"  # written, no confirmation expected
    CONFIRMED = "confirmed"  # actuator answered
    UNCONFIRMED = "unconfirmed"  # no answer after all retries
    REPLACED = "replaced"  # a newer command for the same channel took its place
    FAILED = "failed"  # gateway not connected or write error
    CANCELLED = "cancelled"  # queue stopped


@dataclass
class QueueStats:
    sent: int = 0
    confirmed: int = 0
    retries: int = 0
    unconfirmed: int = 0
    replaced: int = 0
    failed: int = 0
    max_wait: float = 0.0
    total_wait: float = 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "sent": self.sent,
            "confirmed": self.confirmed,
            "retries": self.retries,
            "unconfirmed": self.unconfirmed,
            "replaced": self.replaced,
            "failed": self.failed,
            "max_wait_ms": round(self.max_wait * 1000, 1),
            "avg_wait_ms": round(self.total_wait * 1000 / max(self.sent, 1), 1),
        }


@dataclass(eq=False)
class _Job:
    telegram: RadioTelegram
    priority: Priority
    key: Hashable | None
    expect: Callable[[RadioTelegram], bool] | None
    timeout: float
    future: asyncio.Future[SendResult]
    queued_at: float = field(default_factory=time.monotonic)
    attempts: int = 0
    done: bool = False

    def finish(self, result: SendResult) -> None:
        self.done = True
        if not self.future.done():
            self.future.set_result(result)


class SendQueue:
    """Serialises sends to one gateway."""

    def __init__(
        self,
        send: Callable[[RadioTelegram], Awaitable[None]],
        *,
        is_connected: Callable[[], bool] = lambda: True,
        delay: float = DEFAULT_DELAY,
        on_sent: Callable[[RadioTelegram], None] | None = None,
    ) -> None:
        self._send = send
        self._is_connected = is_connected
        self.delay = delay
        self._on_sent = on_sent
        self._heap: list[tuple[int, int, _Job]] = []
        self._seq = itertools.count()
        self._by_key: dict[Hashable, _Job] = {}
        self._waiting: list[tuple[_Job, asyncio.TimerHandle]] = []
        self._wakeup = asyncio.Event()
        self._running = asyncio.Event()
        self._running.set()
        self._task: asyncio.Task[None] | None = None
        self._current: _Job | None = None  # the job being written
        self._stopped = False
        self.stats = QueueStats()

    def __len__(self) -> int:
        return sum(1 for *_, job in self._heap if not job.done)

    def start(self) -> asyncio.Task[None]:
        """Run the worker as a task of its own (tests, scripts)."""
        self._task = asyncio.get_running_loop().create_task(self.run())
        return self._task

    async def stop(self) -> None:
        """Cancel every job; works whether the worker runs via start() or run()."""
        self._stopped = True
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        for *_, job in self._heap:
            job.finish(SendResult.CANCELLED)
        for job, handle in self._waiting:
            handle.cancel()
            job.finish(SendResult.CANCELLED)
        self._heap.clear()
        self._waiting.clear()
        self._by_key.clear()

    def pause(self) -> None:
        """Hold back sends (e.g. while the FAM14 bus memory is read)."""
        self._running.clear()

    def resume(self) -> None:
        self._running.set()

    def submit(
        self,
        telegram: RadioTelegram,
        priority: Priority = Priority.USER,
        *,
        key: Hashable | None = None,
        expect: Callable[[RadioTelegram], bool] | None = None,
        timeout: float = DEFAULT_CONFIRM_TIMEOUT,
    ) -> asyncio.Future[SendResult]:
        """Queue a telegram.

        key: commands with the same key (e.g. device + channel) replace a still waiting one.
        expect: predicate for the actuator's answer; without an answer within timeout the
        telegram is sent again, up to MAX_RETRIES times.
        """
        future: asyncio.Future[SendResult] = asyncio.get_running_loop().create_future()
        if not self._is_connected():
            self.stats.failed += 1
            future.set_result(SendResult.FAILED)
            return future
        job = _Job(telegram, priority, key, expect, timeout, future)
        if key is not None:
            if (old := self._by_key.get(key)) is not None and not old.done:
                old.finish(SendResult.REPLACED)
                self.stats.replaced += 1
            self._by_key[key] = job
        self._push(job)
        return future

    def on_telegram(self, telegram: RadioTelegram) -> None:
        """Feed received telegrams; resolves confirmations."""
        for item in list(self._waiting):
            job, handle = item
            if job.expect is not None and job.expect(telegram):
                handle.cancel()
                self._waiting.remove(item)
                self.stats.confirmed += 1
                job.finish(SendResult.CONFIRMED)

    def _push(self, job: _Job) -> None:
        heapq.heappush(self._heap, (job.priority, next(self._seq), job))
        self._wakeup.set()

    async def run(self) -> None:
        """Worker loop; runs until cancelled."""
        try:
            await self._work()
        finally:  # cancelled while writing: nobody waits for that job in vain
            if self._current is not None:
                self._current.finish(SendResult.CANCELLED)
                self._current = None

    async def _work(self) -> None:
        while True:
            await self._running.wait()
            if not self._heap:
                self._wakeup.clear()
                await self._wakeup.wait()
                continue
            *_, job = heapq.heappop(self._heap)
            if job.done:
                continue
            if job.key is not None and self._by_key.get(job.key) is job and job.expect is None:
                del self._by_key[job.key]
            self._current = job
            await self._transmit(job)
            self._current = None
            await asyncio.sleep(self.delay)

    async def _transmit(self, job: _Job) -> None:
        wait = time.monotonic() - job.queued_at
        try:
            async with asyncio.timeout(SEND_TIMEOUT):
                await self._send(job.telegram)
        except (OSError, ValueError) as err:  # TimeoutError is an OSError
            _LOGGER.warning("Sending %s failed: %s", job.telegram, err)
            self.stats.failed += 1
            job.finish(SendResult.FAILED)
            return
        if job.attempts == 0:
            self.stats.sent += 1
            self.stats.total_wait += wait
            self.stats.max_wait = max(self.stats.max_wait, wait)
        job.attempts += 1
        if self._on_sent:
            self._on_sent(job.telegram)
        if job.expect is None:
            job.finish(SendResult.SENT)
            return
        if self._stopped:  # stopped while writing: no confirmation, no retry
            job.finish(SendResult.CANCELLED)
            return
        handle = asyncio.get_running_loop().call_later(job.timeout, self._timed_out, job)
        self._waiting.append((job, handle))

    def _timed_out(self, job: _Job) -> None:
        self._waiting = [(j, h) for j, h in self._waiting if j is not job]
        if job.done:
            return
        if job.attempts <= MAX_RETRIES:
            self.stats.retries += 1
            self._push(job)
            return
        self.stats.unconfirmed += 1
        if job.key is not None and self._by_key.get(job.key) is job:
            del self._by_key[job.key]
        job.finish(SendResult.UNCONFIRMED)
