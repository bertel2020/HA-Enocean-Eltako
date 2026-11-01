"""What Eltako publishes about the RS485 bus of the series 14, for the installation documentation.

Technical facts only (numbers), no copied text. Source of every value: Eltako, "RS485-Bus-
Reiheneinbaugeräte Baureihe 14, Planungshilfe und Betriebsanleitung", edition 07/2014, chapter 1
(table "maximaler Leistungsbedarf" and the text above it). That edition predates newer devices
(F3Z14D, for one): a type missing here has no value, it is not zero. Home Assistant adds nothing.
"""

from __future__ import annotations

import re

SOURCE = "Eltako Planungshilfe RS485-Bus Baureihe 14, 07/2014"
ADDRESSES = 126  # device addresses 1..126 on one FAM14; a multi-channel actuator takes one each
SUPPLY_WATTS = 12.0  # what the supply inside the FAM14 delivers to all devices on the bus

# type -> the most one device takes from the bus, in watts
POWER: dict[str, float] = {
    "FAE14LPR": 0.42,
    "FAE14SSR": 0.40,
    "FAM14": 0.80,
    "FFR14": 0.63,
    "FGSM14": 0.20,
    "FGW14": 0.50,
    "FHK14": 0.42,
    "FMS14": 0.63,
    "FMSR14": 0.10,
    "FMZ14": 0.40,
    "FRP14": 0.50,
    "FSB14": 0.42,
    "FSG14/1-10V": 0.20,
    "FSR14-2X": 0.14,
    "FSR14-4X": 0.70,
    "FSR14SSR": 0.40,
    "FSU14": 0.14,
    "FTD14": 0.53,
    "FTN14": 0.14,
    "FTS14EM": 0.13,
    "FTS14KS": 0.36,
    "FTS14FA": 0.50,
    "FTS14TG": 0.42,
    "FUD14": 0.20,
    "FUD14/800W": 0.20,
    "FWZ14": 0.10,
    "FZK14": 0.14,
}


def _key(model: str) -> str:
    return re.sub(r"\s+", "", model).upper()


def bus_power(model: str | None) -> float | None:
    """The watts a type takes from the bus; None when the table does not list it."""
    return POWER.get(_key(model or ""))
