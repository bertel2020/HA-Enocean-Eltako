"""Telegrams of virtual sensors: Home Assistant values sent as if from an EnOcean sensor.

Encoded from the official standard profiles: D5-00-01 contact (CO 1 = closed),
A5-02-05 temperature 0...40 degC, A5-07-01 occupancy (PIRS >= 128 = motion). Data telegrams
set the LRN bit; the teach-in of D5-00-01 is the same byte with LRN = 0, the 4BS profiles
send a teach-in with EEP and manufacturer. The Eltako formats (FAH60 brightness, FWS61
weather station) are in eltako/virtual.py.
"""

from __future__ import annotations

from .model import encode
from .std.profiles import PROFILES
from .teach_in import encode_teach_in_4bs

CONTACT_TEACH_IN = encode(PROFILES["D5-00-01"], {"CO": 0, "LRN": 0})
TEMPERATURE_TEACH_IN = encode_teach_in_4bs("A5-02-05")
MOTION_TEACH_IN = encode_teach_in_4bs("A5-07-01")
TEMPERATURE_RANGE = (0.0, 40.0)


def encode_contact(closed: bool) -> bytes:
    return encode(PROFILES["D5-00-01"], {"CO": int(closed), "LRN": 1})


def encode_temperature(celsius: float) -> bytes:
    """Clamped to the profile range 0...40 degC."""
    low, high = TEMPERATURE_RANGE
    return encode(PROFILES["A5-02-05"], {"TMP": max(low, min(high, celsius)), "LRNB": 1})


def encode_motion(motion: bool) -> bytes:
    return encode(PROFILES["A5-07-01"], {"PIRS": 255 if motion else 0, "LRNB": 1, "SVA": 0})
