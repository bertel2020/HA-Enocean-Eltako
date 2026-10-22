"""Eltako formats of virtual sensors: Home Assistant values sent as if from an Eltako sensor.

A5-06-01:eltako (FAH60): Eltako's own layout instead of the official A5-06-01 (see below).

A5-13-01:eltako (FWS61): the official A5-13-01 and A5-13-02 layouts, sent under one ID and
    told apart by the identifier in DB0.7...4 (1 and 2), which the official profiles do not set.
"""

from __future__ import annotations

from ..model import encode
from ..std.profiles import PROFILES
from ..teach_in import encode_teach_in_4bs

# A5-06-01:eltako, the FAH60 format (Eltako's own layout, not the official A5-06-01):
# DB3 = twilight 0...100 lx (valid only while DB2 = 0), DB2 = 300...30000 lx over 0...255,
# DB0 = 0x0F. Teach-in as an FAH60 sends it.
BRIGHTNESS_TEACH_IN = bytes.fromhex("18080D87")
BRIGHTNESS_TWILIGHT_MAX = 100.0
BRIGHTNESS_RANGE = (300.0, 30000.0)


def encode_brightness(lux: float) -> bytes:
    """Below 300 lx the twilight byte (0...100 lx, higher values clamp to 100), else DB2."""
    low, high = BRIGHTNESS_RANGE
    if lux < low:
        return bytes([round(max(0.0, min(BRIGHTNESS_TWILIGHT_MAX, lux))), 0, 0, 0x0F])
    raw = round((min(lux, high) - low) / (high - low) * 255)
    return bytes([round(BRIGHTNESS_TWILIGHT_MAX), max(1, raw), 0, 0x0F])


# A5-13-01:eltako, the FWS61 format: two telegrams under one ID, identifier 1 (dawn,
# temperature, wind, day/night, rain; official A5-13-01) and 2 (sun west/south/east in klx;
# official A5-13-02). Teach-in: 4BS with EEP A5-13-01 and Eltako as manufacturer.
WEATHER_TEACH_IN = encode_teach_in_4bs("A5-13-01")
WEATHER_TEMPERATURE_RANGE = (-40.0, 80.0)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def encode_weather(
    dawn_lux: float, celsius: float, wind_ms: float, night: bool, rain: bool
) -> bytes:
    data = bytearray(
        encode(
            PROFILES["A5-13-01"],
            {
                "DWS": _clamp(dawn_lux, 0.0, 999.0),
                "TMP": _clamp(celsius, *WEATHER_TEMPERATURE_RANGE),
                "WND": _clamp(wind_ms, 0.0, 70.0),
                "D/N": int(night),
                "RAN": int(rain),
                "LRNB": 1,
            },
        )
    )
    data[3] = (data[3] & 0x0F) | 0x10  # identifier 1
    return bytes(data)


def encode_sun(west_klx: float, south_klx: float, east_klx: float) -> bytes:
    data = bytearray(
        encode(
            PROFILES["A5-13-02"],
            {
                "SNW": _clamp(west_klx, 0.0, 150.0),
                "SNS": _clamp(south_klx, 0.0, 150.0),
                "SNE": _clamp(east_klx, 0.0, 150.0),
                "LRNB": 1,
            },
        )
    )
    data[3] = (data[3] & 0x0F) | 0x20  # identifier 2
    return bytes(data)
