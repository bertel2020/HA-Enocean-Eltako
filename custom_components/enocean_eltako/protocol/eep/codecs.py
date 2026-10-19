"""Decoders by EEP reference: standard profiles from the generated table, Eltako variants
from eep/eltako/. The two never share a code path."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..telegram import RadioTelegram, Rorg
from . import EEPRef
from .eltako import heating, sensors, shutter, switching
from .model import decode
from .std.profiles import PROFILES

Decoder = Callable[[RadioTelegram], dict[str, Any] | None]


def _std(eep: str) -> Decoder:
    profile = PROFILES[eep]
    lrn_field = "LRNB" if profile.rorg == Rorg.BS4 else "LRN"

    def decode_std(telegram: RadioTelegram) -> dict[str, Any] | None:
        if telegram.rorg != profile.rorg:
            return None
        values = decode(profile, telegram.data, telegram.status)
        if values.get(lrn_field, 1) == 0:
            return None  # teach-in telegram
        return values or None

    return decode_std


def _eltako(rorg: int, fn: Callable[[bytes], dict[str, Any] | None]) -> Decoder:
    def decode_eltako(telegram: RadioTelegram) -> dict[str, Any] | None:
        return fn(telegram.data) if telegram.rorg == rorg else None

    return decode_eltako


def _shutter_status(telegram: RadioTelegram) -> dict[str, Any] | None:
    if telegram.rorg not in (Rorg.RPS, Rorg.BS4):
        return None
    return shutter.decode_status(telegram.data)


DECODERS: dict[EEPRef, Decoder] = {
    **{EEPRef(eep, "std"): _std(eep) for eep in PROFILES},
    EEPRef("M5-38-08", "eltako"): _eltako(Rorg.RPS, switching.decode_switch_status),
    EEPRef("A5-38-08", "eltako"): _eltako(Rorg.BS4, switching.decode_dim_status),
    EEPRef("G5-3F-7F", "eltako"): _shutter_status,
    EEPRef("A5-08-01", "eltako"): _eltako(Rorg.BS4, sensors.decode_fbh),
    EEPRef("M5-10-06", "eltako"): lambda t: (
        heating.decode_status(t.data) if t.rorg in (Rorg.RPS, Rorg.BS4) else None
    ),
    EEPRef("A5-10-06", "eltako"): _eltako(Rorg.BS4, sensors.decode_room_controller),
    EEPRef("A5-12-01", "eltako"): _eltako(Rorg.BS4, sensors.decode_meter),
    EEPRef("A5-13-01", "eltako"): _eltako(Rorg.BS4, sensors.decode_weather),
}


def decode_telegram(ref: EEPRef, telegram: RadioTelegram) -> dict[str, Any] | None:
    """Decoded values, or None for teach-in, foreign or undecodable telegrams."""
    decoder = DECODERS.get(ref)
    return decoder(telegram) if decoder else None
