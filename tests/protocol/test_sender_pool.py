"""Sender ID pool (E3)."""

import pytest

from custom_components.enocean_eltako.protocol.sender_pool import (
    BUS_POOL_START,
    SenderIdError,
    SenderPool,
    SenderRegistry,
    SenderState,
)

BASE = 0xFFB74480


def test_allocate_sequential_and_exhaust() -> None:
    pool = SenderPool(BASE)
    assert pool.allocate("a") == BASE
    assert pool.allocate("b") == BASE + 1
    for i in range(126):
        pool.allocate(f"x{i}")
    with pytest.raises(SenderIdError) as err:
        pool.allocate("too_many")
    assert err.value.reason == "pool_exhausted"


def test_assign_checks_range_and_owner() -> None:
    pool = SenderPool(BASE)
    pool.assign(BASE + 5, "cover")
    pool.assign(BASE + 5, "cover")  # idempotent for the same owner
    with pytest.raises(SenderIdError, match="in_use"):
        pool.assign(BASE + 5, "light")
    with pytest.raises(SenderIdError, match="out_of_range"):
        pool.assign(BASE + 128, "light")
    assert pool.next_free() == BASE


def test_released_id_stays_blocked_until_teach_out() -> None:
    pool = SenderPool(BASE)
    sender = pool.allocate("cover")
    pool.release(sender)
    assert pool.get(sender).state is SenderState.BLOCKED
    assert pool.allocate("new") == BASE + 1
    with pytest.raises(SenderIdError, match="blocked"):
        pool.assign(sender, "new")
    pool.confirm_teach_out(sender)
    assert pool.next_free() == sender


def test_roundtrip() -> None:
    pool = SenderPool(BASE)
    pool.allocate("a")
    pool.release(pool.allocate("b"))
    data = pool.as_dict()
    assert data["allocations"]["FF-B7-44-81"] == {"owner": "b", "state": "blocked"}
    restored = SenderPool(BASE)
    restored.load(data)
    assert restored.as_dict() == data


def test_registry_prevents_collisions_across_gateways() -> None:
    reg = SenderRegistry()
    bus_a = reg.create_pool("bus_a", BUS_POOL_START)
    bus_b = reg.create_pool("bus_b", BUS_POOL_START)
    radio = reg.create_pool("fam_usb", BASE)
    assert bus_a.allocate("fsr14") == BUS_POOL_START
    assert bus_b.allocate("fsb14") == BUS_POOL_START + 1  # skips the ID used by bus_a
    with pytest.raises(SenderIdError, match="in_use"):
        bus_b.assign(BUS_POOL_START, "other")
    unreserve = reg.reserve(BASE, "device FF-B7-44-80")
    assert radio.allocate("x") == BASE + 1
    unreserve()
    assert radio.next_free() == BASE
    reg.remove_pool("bus_a")
    bus_b.assign(BUS_POOL_START, "other")
