"""Send queue: confirmation timeout and the number of repeats of a command."""

from __future__ import annotations

import asyncio

from custom_components.enocean_eltako.protocol.send_queue import (
    BUS_CONFIRM_TIMEOUT,
    DEFAULT_CONFIRM_TIMEOUT,
    SendQueue,
    SendResult,
)
from custom_components.enocean_eltako.protocol.telegram import RadioTelegram, Rorg

TELEGRAM = RadioTelegram(Rorg.RPS, b"\x70", 0xFFB74481, 0x30)


def test_a_bus_actuator_gets_longer_than_the_fam14_needs_to_poll() -> None:
    assert DEFAULT_CONFIRM_TIMEOUT < 10 < BUS_CONFIRM_TIMEOUT  # the FAM14 needs up to 10 s


async def _unanswered(retries: int | None) -> tuple[SendResult, int]:
    sent: list[RadioTelegram] = []

    async def send(telegram: RadioTelegram) -> None:
        sent.append(telegram)

    queue = SendQueue(send)
    task = asyncio.create_task(queue.run())
    kwargs = {} if retries is None else {"retries": retries}
    result = await queue.submit(TELEGRAM, expect=lambda t: False, timeout=0.02, **kwargs)
    task.cancel()
    return result, len(sent)


async def test_an_unanswered_command_is_repeated_twice_by_default() -> None:
    assert await _unanswered(None) == (SendResult.UNCONFIRMED, 3)


async def test_a_command_without_retries_is_sent_once() -> None:
    assert await _unanswered(0) == (SendResult.UNCONFIRMED, 1)
