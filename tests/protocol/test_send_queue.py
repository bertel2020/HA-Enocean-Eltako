"""Send queue (E9)."""

import asyncio

import pytest

from custom_components.enocean_eltako.protocol.send_queue import Priority, SendQueue, SendResult
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg


def tg(n: int, sender: int = 0xFFB74481) -> RadioTelegram:
    return RadioTelegram(Rorg.BS4, bytes([n, 0, 0, 0x08]), sender)


class Recorder:
    def __init__(self) -> None:
        self.sent: list[RadioTelegram] = []

    async def __call__(self, telegram: RadioTelegram) -> None:
        self.sent.append(telegram)


@pytest.fixture
async def queue():
    rec = Recorder()
    q = SendQueue(rec, delay=0)
    q.rec = rec
    yield q
    await q.stop()


async def test_priority_order(queue: SendQueue) -> None:
    futures = [
        queue.submit(tg(3), Priority.BACKGROUND),
        queue.submit(tg(2), Priority.AUTOMATION),
        queue.submit(tg(0), Priority.SAFETY),
        queue.submit(tg(1), Priority.USER),
    ]
    queue.start()
    assert await asyncio.gather(*futures) == [SendResult.SENT] * 4
    assert [t.data[0] for t in queue.rec.sent] == [0, 1, 2, 3]


async def test_fifo_within_priority_and_scene_without_loss(queue: SendQueue) -> None:
    futures = [queue.submit(tg(i, 0xFFB74481 + i), Priority.AUTOMATION) for i in range(16)]
    queue.start()
    assert await asyncio.gather(*futures) == [SendResult.SENT] * 16
    assert [t.data[0] for t in queue.rec.sent] == list(range(16))
    assert queue.stats.sent == 16 and len(queue) == 0


async def test_same_key_replaces_waiting_command(queue: SendQueue) -> None:
    first = queue.submit(tg(10), key=("dimmer", 1))
    second = queue.submit(tg(80), key=("dimmer", 1))
    other = queue.submit(tg(5), key=("dimmer", 2))
    queue.start()
    assert await first == SendResult.REPLACED
    assert await second == SendResult.SENT
    assert await other == SendResult.SENT
    assert [t.data[0] for t in queue.rec.sent] == [80, 5]
    assert queue.stats.replaced == 1


async def test_confirmation(queue: SendQueue) -> None:
    queue.start()
    fut = queue.submit(tg(1), expect=lambda t: t.sender == 0x00000012, timeout=1)
    await asyncio.sleep(0.01)
    queue.on_telegram(RadioTelegram(Rorg.BS4, bytes(4), 0x00000099))
    assert not fut.done()
    queue.on_telegram(RadioTelegram(Rorg.BS4, bytes(4), 0x00000012))
    assert await fut == SendResult.CONFIRMED
    assert queue.stats.confirmed == 1


async def test_retries_then_unconfirmed(queue: SendQueue) -> None:
    queue.start()
    fut = queue.submit(tg(1), expect=lambda t: False, timeout=0.02)
    assert await asyncio.wait_for(fut, 1) == SendResult.UNCONFIRMED
    assert len(queue.rec.sent) == 3  # first try + 2 retries
    assert queue.stats.retries == 2 and queue.stats.unconfirmed == 1


async def test_not_connected_fails_immediately() -> None:
    q = SendQueue(Recorder(), is_connected=lambda: False)
    assert await q.submit(tg(1)) == SendResult.FAILED


async def test_write_error_fails_job() -> None:
    async def broken(_):
        raise ConnectionError("gone")

    q = SendQueue(broken, delay=0)
    q.start()
    assert await q.submit(tg(1)) == SendResult.FAILED
    await q.stop()


async def test_pause_holds_sends(queue: SendQueue) -> None:
    queue.start()
    queue.pause()
    fut = queue.submit(tg(1))
    await asyncio.sleep(0.05)
    assert not fut.done()
    queue.resume()
    assert await fut == SendResult.SENT


async def test_stop_cancels_waiting(queue: SendQueue) -> None:
    fut = queue.submit(tg(1))
    await queue.stop()
    assert await fut == SendResult.CANCELLED


async def test_delay_spaces_telegrams() -> None:
    times = []

    async def send(_):
        times.append(asyncio.get_running_loop().time())

    q = SendQueue(send, delay=0.03)
    q.start()
    await asyncio.gather(q.submit(tg(1)), q.submit(tg(2)))
    await q.stop()
    assert times[1] - times[0] >= 0.025
