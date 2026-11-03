"""What Eltako publishes about the RS485 bus of the series 14, for the installation documentation.

Technical facts only (numbers), no copied text. Source of the power values: Eltako, "RS485-Bus-
Reiheneinbaugeräte Baureihe 14, Planungshilfe und Betriebsanleitung", edition 07/2014, chapter 1
(table "maximaler Leistungsbedarf" and the text above it). That edition predates newer devices
(F3Z14D, for one): a type missing there has no power value, it is not zero. Widths (TE, 18 mm
each) and the number of bus addresses come from the planning guide and the devices' manuals; the
values marked "assumed" in BUS_TYPES are not confirmed by a data sheet yet (see
docs/mockups/eltako-bus-konzept.md, section 2.4). Home Assistant adds nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SOURCE = "Eltako Planungshilfe RS485-Bus Baureihe 14, 07/2014"
ADDRESSES = 126  # device addresses 1..126 on one FAM14; a multi-channel actuator takes one each
SUPPLY_WATTS = 12.0  # what the supply inside the FAM14 delivers to all devices on the bus
# the Eltako series 14 (FSR14, FUD14, FSB14, F3Z14D ...) hangs on the FAM14 bus
BUS_MODEL = re.compile(r"^F[A-Z0-9]{1,4}14", re.IGNORECASE)

# what a type is on the bus
ROLES = ("master", "supply", "actuator", "meter", "input", "gateway", "other")


@dataclass(frozen=True)
class BusType:
    """One type of the series 14: width, bus addresses, power from and to the bus, role."""

    name: str  # the type designation as Eltako writes it
    role: str  # one of ROLES
    te: float | None = None  # width in TE (18 mm); None: not known
    addresses: int | None = None  # bus addresses it takes (one per channel); None: not known
    power: float | None = None  # the most it takes from the bus, in watts (planning guide)
    supply: float | None = None  # what it delivers to the bus, in watts (master, power supply)
    assumed: tuple[str, ...] = ()  # "te", "addresses": not confirmed by a data sheet yet


_TYPES = (
    BusType("FAM14", "master", te=2, addresses=0, power=0.80, supply=12.0),
    BusType("FTS14KS", "master", power=0.36),
    BusType("FSNT14-12V/12W", "supply", te=1, addresses=0, supply=12.0),
    BusType("FSR14-4x", "actuator", te=1, addresses=4, power=0.70),
    BusType("FSR14-2x", "actuator", te=1, addresses=2, power=0.14),
    BusType("FSR14SSR", "actuator", te=1, addresses=2, power=0.40, assumed=("addresses",)),
    BusType("F4SR14-LED", "actuator", te=1, addresses=4),
    BusType("FSB14", "actuator", te=1, addresses=2, power=0.42),
    BusType("FUD14", "actuator", te=1, addresses=1, power=0.20),
    BusType("FUD14/800W", "actuator", te=1, addresses=1, power=0.20),
    BusType("FTN14", "actuator", te=1, addresses=1, power=0.14),
    BusType("FSU14", "actuator", te=1, addresses=1, power=0.14, assumed=("addresses",)),
    BusType("FWZ14", "meter", te=1, addresses=1, power=0.10),
    BusType("FWZ14-65A", "meter", te=1, addresses=1, power=0.10),
    BusType("F3Z14D", "meter", te=1, addresses=3, assumed=("te",)),  # one per meter input
    BusType("DSZ14DRS", "meter", te=4, addresses=1, assumed=("te",)),
    BusType("FTS14EM", "input", te=1, power=0.13),
    BusType("FTS14TG", "input", te=1, addresses=1, power=0.42),
    BusType("FGW14", "gateway", te=1, addresses=1, power=0.50),
    BusType("FGW14-USB", "gateway", te=1, addresses=1, power=0.50),
    BusType("FAE14LPR", "actuator", power=0.42),
    BusType("FAE14SSR", "actuator", power=0.40),
    BusType("FFR14", "actuator", power=0.63),
    BusType("FGSM14", "other", power=0.20),
    BusType("FHK14", "actuator", power=0.42),
    BusType("FMS14", "actuator", power=0.63),
    BusType("FMSR14", "input", power=0.10),
    BusType("FMZ14", "actuator", power=0.40),
    BusType("FRP14", "other", power=0.50),
    BusType("FSG14/1-10V", "actuator", power=0.20),
    BusType("FTD14", "other", power=0.53),
    BusType("FTS14FA", "input", power=0.50),
    BusType("FZK14", "actuator", power=0.14),
)


def _key(model: str) -> str:
    return re.sub(r"\s+", "", model).upper()


BUS_TYPES: dict[str, BusType] = {_key(t.name): t for t in _TYPES}

# type -> the most one device takes from the bus, in watts (the planning guide's table)
POWER: dict[str, float] = {k: t.power for k, t in BUS_TYPES.items() if t.power is not None}


def bus_type(model: str | None) -> BusType | None:
    """The catalog entry of a type, written in any case and spacing; None when not listed."""
    return BUS_TYPES.get(_key(model or ""))


def bus_power(model: str | None) -> float | None:
    """The watts a type takes from the bus; None when the table does not list it."""
    return POWER.get(_key(model or ""))


def is_bus_model(model: str | None) -> bool:
    """A type of the series 14 that hangs on the bus (by its name)."""
    return bool(model) and (bus_type(model) is not None or bool(BUS_MODEL.match(model or "")))
