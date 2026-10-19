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


def test_overrun_into_end_and_penalties() -> None:
    cover = CoverPosition(20, 20, position=90, inaccuracy=3)
    cover.driven(4, up=True)  # 20 points up from 90: overrun
    assert cover.position == 100 and cover.inaccuracy == 3
    cover.restarted()
    cover.no_answer()
    assert cover.inaccuracy == 33
