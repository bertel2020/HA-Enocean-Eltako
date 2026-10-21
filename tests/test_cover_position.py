"""Shutter position model (I6)."""

import pytest

from custom_components.enocean_eltako.cover_position import CoverPosition, margin


def test_margin() -> None:
    assert margin(10) == 2.0
    assert margin(30) == 3.0


def test_anchor_by_full_driven_time_and_partial_inaccuracy() -> None:
    cover = CoverPosition(20, 20)
    cover.driven(cover.full_run_time(up=True), up=True)
    assert (cover.position, cover.inaccuracy) == (100, 0)
    cover.driven(10, up=False)
    assert cover.position == 50
    assert cover.inaccuracy == pytest.approx(1 + 50 * 0.03)
    cover.driven(5, up=False)
    assert cover.position == 25
    assert cover.inaccuracy == pytest.approx(2 * 1 + 75 * 0.03)


def test_partial_run_and_nearer_end() -> None:
    cover = CoverPosition(20, 30, position=50, inaccuracy=0)
    assert cover.partial_run(75) == (True, 5.0)
    assert cover.partial_run(20) == (False, 9.0)
    assert cover.partial_run(50) is None
    assert cover.nearer_end() == 100
    assert CoverPosition(20, 20).partial_run(10) is None
    assert CoverPosition(20, 20).nearer_end() == 100  # unknown: open, never close unasked
    assert CoverPosition(20, 20, position=10).nearer_end() == 0


def test_overrun_into_end_and_penalties() -> None:
    cover = CoverPosition(20, 20, position=90, inaccuracy=3)
    cover.driven(4, up=True)  # 20 points up from 90: overrun
    assert cover.position == 100 and cover.inaccuracy == 3
    cover.restarted()
    cover.no_answer()
    assert cover.inaccuracy == 33


def test_vent_slots_position_one_is_down_with_slots_open() -> None:
    from custom_components.enocean_eltako.cover_position import CoverPosition

    # 30 s down incl. 4 s for the slots, 30 s up
    cover = CoverPosition(time_opens=30, time_closes=30, vent_time=4)
    cover.anchor(100)
    up, seconds = cover.partial_run(1)
    assert not up and seconds == 26  # down to the bottom, slots stay open
    cover.driven(26, up=False)
    assert cover.position == 1
    cover.driven(4, up=False)  # the slots close
    assert cover.position == 0
    up, seconds = cover.partial_run(50)
    assert up and round(seconds, 2) == round(4 + 49 / 99 * 26, 2)  # slots open first
    cover.driven(2, up=True)  # half the slot time: slots open
    assert cover.position == 1


def test_vent_slots_stay_open_when_stopped_early() -> None:
    from custom_components.enocean_eltako.cover_position import CoverPosition

    cover = CoverPosition(time_opens=30, time_closes=30, vent_time=4)
    cover.anchor(100)
    cover.driven(27, up=False)  # 1 s into the slot zone
    assert cover.position == 1


def test_blind_turns_slats_before_height() -> None:
    from custom_components.enocean_eltako.cover_position import CoverPosition

    cover = CoverPosition(time_opens=40, time_closes=40, tilt_time=1.5)
    cover.anchor(100)
    assert cover.tilt == 100
    cover.driven(1.5, up=False)  # only the slats close
    assert cover.position == 100 and cover.tilt == 0
    cover.driven(19.25, up=False)  # half the height
    assert cover.position == 50 and cover.tilt == 0
    up, seconds = cover.tilt_run(40)
    assert up and round(seconds, 2) == 0.6
    cover.driven(0.6, up=True)
    assert cover.tilt == 40 and cover.position == 50
    up, seconds = cover.partial_run(60)
    assert up and round(seconds, 2) == round(0.9 + 0.1 * 38.5, 2)  # slats open, then height
