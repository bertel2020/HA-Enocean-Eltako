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


def test_what_an_id_in_a_pool_is() -> None:
    """Ours, kept for another system, or foreign: in a pool but allocated to nobody."""
    registry = SenderRegistry()
    pool = registry.create_pool("radio", BASE + 1, 127)
    registry.reserve(BASE + 4, "device alias")
    pool.assign(BASE + 2, "device:a:central")
    pool.reserve_external(BASE + 3)
    assert registry.status(BASE + 2) == "ours"
    assert registry.status(BASE + 4) == "ours"  # reserved here
    assert registry.status(BASE + 3) == "external"
    assert registry.status(BASE + 5) == "foreign"  # in the pool, allocated to nobody
    assert registry.status(BASE) is None  # the base ID itself is not in the pool
    pool.release(BASE + 2)  # a deleted device: still ours until the teach-out is confirmed
    assert registry.status(BASE + 2) == "ours"


def test_an_external_id_is_never_handed_out_and_needs_no_teach_out() -> None:
    pool = SenderPool(BASE + 1, 127)
    pool.reserve_external(BASE + 1)
    assert pool.allocate("a") == BASE + 2  # the kept ID is skipped
    pool.release_external(BASE + 1)
    assert pool.get(BASE + 1) is None and pool.next_free() == BASE + 1  # at once, no BLOCKED
    pool.assign(BASE + 3, "device:x:central")
    pool.release_external(BASE + 3)  # a device's own ID is not touched
    assert pool.get(BASE + 3) is not None
    with pytest.raises(SenderIdError) as err:
        pool.reserve_external(BASE + 3)  # allocated to a device
    assert err.value.reason == "in_use"
    pool.release(BASE + 3)
    with pytest.raises(SenderIdError) as blocked:
        pool.reserve_external(BASE + 3)  # waiting for its teach-out
    assert blocked.value.reason == "blocked"
    with pytest.raises(SenderIdError) as out:
        pool.reserve_external(BASE + 200)
    assert out.value.reason == "out_of_range"
