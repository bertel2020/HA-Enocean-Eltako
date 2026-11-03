"""What Eltako publishes about the RS485 bus of the series 14, for the installation documentation.

Technical facts only (numbers and type designations), no copied text. Sources (all from
eltako.com, read 2026-11-03):

- [B] "Operating manual for series 14 RS485 bus DIN rail mounted devices", edition 10/2026:
  table "maximum power requirement (existing relay excited)", device address assignment.
- [K] Main catalogue, chapter 1 "Series 14" (English and German): width of each device
  ("1 module = 18 mm"), channels, the power table of the 12 V supply (it lists FFR14, FGSM14,
  FTS14GBZ and FZK14, which [B] no longer does), chapter 2 (FTS14EM, FTS14KS, FTS14TG, FTS14FA).
- [T] "Inhalte der Eltako-Funktelegramme": device addresses of F3Z14D, FSU14 (8), FMSR14 (5),
  FDG14 (DALI groups 0-15), confirmation telegrams.
- [M] Manuals FAM14 (30014000-7) and FGW14 (30014017-1).
- [P] Planning guide 07/2014 (the values of the first version of this table).

A value a source does not give is None, and the field is listed in `assumed` with a value only
where it is an assumption (an "-2x" type with two channels, say). Home Assistant adds nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SOURCE = "Eltako operating manual series 14 RS485 bus 10/2026, main catalogue chapter 1"
ADDRESSES = 126  # device addresses 1..126 on one FAM14; a multi-channel actuator takes one each
SUPPLY_WATTS = 12.0  # what the supply inside the FAM14 delivers to all devices on the bus
# the Eltako series 14 (FSR14, FUD14, FSB14, F3Z14D ...) hangs on the FAM14 bus
BUS_MODEL = re.compile(r"^(F[A-Z0-9]{1,4}14|BGW14|DSZ14)", re.IGNORECASE)

# what a type is on the bus; accessory: on the rail, but no bus device (spacer, bus coupler ...)
ROLES = ("master", "supply", "actuator", "meter", "input", "gateway", "other", "accessory")


@dataclass(frozen=True)
class BusType:
    """One type of the series 14: width, bus addresses, power from and to the bus, role."""

    name: str  # the type designation as Eltako writes it
    role: str  # one of ROLES
    te: float | None = None  # width in TE (18 mm); None: not known
    addresses: int | None = None  # bus addresses it takes (one per channel); None: not known
    power: float | None = None  # the most it takes from the bus, in watts ([B], else [K]/[P])
    supply: float | None = None  # what it delivers to the bus, in watts (master, power supply)
    assumed: tuple[str, ...] = ()  # "te", "addresses": not confirmed by a source yet


_TYPES = (
    # masters and power supplies
    # FAM14 up to week 07/22: supply 12 V DC-1A integrated (left half of its 2 TE) [M][B]; later
    # ones come with an FSNT14-12V/12W of their own [M] that delivers the 12 W instead (the
    # section rule in installation_checks.master_supply keeps them from counting twice). The
    # catalogue's power table says "FAM14 resp. FTS14KS: 12 V DC/8 W" [K], against 12 W in [M][B].
    BusType("FAM14", "master", te=2, addresses=0, power=0.80, supply=12.0),
    BusType("FTS14KS", "master", te=2, addresses=0, power=0.40, supply=8.0),  # [K] ch. 2
    BusType("FSNT14-12V/12W", "supply", te=1, addresses=0, supply=12.0),  # [K]
    # switching actuators
    BusType("FSR14-4x", "actuator", te=1, addresses=4, power=0.70),  # [K][B]
    BusType("FSR14-2x", "actuator", te=1, addresses=2, power=0.14),
    BusType("FSR14M-2x", "actuator", addresses=2, power=0.14, assumed=("addresses",)),  # [B]
    BusType("FSR14SSR", "actuator", te=1, addresses=2, power=0.40),  # [K] 2-channel
    BusType("F4SR14-LED", "actuator", te=2, addresses=4, power=1.00),  # [K] 2 modules
    BusType("FMS14", "actuator", te=1, power=0.63),
    BusType("FMZ14", "actuator", te=1, addresses=1, power=0.40),
    BusType("FTN14", "actuator", te=1, addresses=1, power=0.14),
    BusType("FSB14", "actuator", te=1, addresses=2, power=0.42),  # [K] 2 channels
    BusType("F2L14", "actuator", te=1, power=0.14),
    BusType("FZK14", "actuator", power=0.14),  # [K] power table only
    # dimmers
    BusType("FUD14", "actuator", te=1, addresses=1, power=0.20),
    BusType("FUD14/800W", "actuator", te=2, addresses=1, power=0.20),  # [K] 2 modules
    BusType("FLUD14", "other", te=1),  # [K] capacity enhancer of the FUD14/800W, power "–" [B]
    BusType("FSG14/1-10V", "actuator", te=1, addresses=1, power=0.20),
    BusType("FDG14", "gateway", te=2, addresses=16, power=0.40),  # [K][T] DALI groups 0-15
    BusType("FD2G14", "gateway", power=0.50),  # [B]
    BusType("FRGBW14", "actuator", power=0.10),  # [B]
    # heating and cooling, single room control
    BusType("FHK14", "actuator", te=1, power=0.42),
    BusType("F4HK14", "actuator", te=1, addresses=4, power=0.70),  # [K] 4 channels
    BusType("FAE14SSR", "actuator", te=1, addresses=2, power=0.40),  # [K] 2 zones
    BusType("FAE14LPR", "actuator", te=1, addresses=2, power=0.42),
    BusType("FFR14", "actuator", power=0.63),  # [K] power table only
    # timers, sensors, meters
    BusType("FSU14", "actuator", te=1, addresses=8, power=0.14),  # [K][T] 8 channels
    BusType("FMSR14", "input", te=1, addresses=5, power=0.10),  # [K][T] 5 channels
    BusType("F3Z14D", "meter", te=1, addresses=3, power=0.10),  # [K][T][B] 3 S0 inputs
    BusType("FWZ14-65A", "meter", te=1, addresses=1, power=0.10, assumed=("addresses",)),
    BusType("FWZ14", "meter", te=1, addresses=1, power=0.10, assumed=("addresses",)),  # [P]
    BusType("DSZ14DRS-3x80A", "meter", te=4, power=None),  # [K] 4 modules = 70 mm
    BusType("DSZ14WDRS-3x5A", "meter", te=4, power=None),  # [K]
    BusType("FSDG14", "meter", te=1, addresses=2, power=0.40),  # [K] usage ch. 1, delivery ch. 2
    # gateways and bus devices without load
    BusType("FGW14", "gateway", te=1, addresses=1, power=0.50),  # [K][B][M] address at pos. 10
    BusType("FGW14-USB", "gateway", te=1, addresses=1, power=0.30),  # [K][B]
    BusType("BGW14", "gateway", te=1, power=0.30),  # [K][B]
    BusType("FWG14MS", "gateway", te=1, power=0.30),  # [K][B]
    BusType("FGSM14", "gateway", power=0.20),  # [K] power table only
    BusType("FPLG14", "gateway", power=0.40),  # [B]
    BusType("FPLT14", "gateway", power=0.40),  # [B]
    BusType("FSM14-UC", "input", te=1, power=0.10),  # [K] 4 channels by radio; [B] "FSM14"
    BusType("FRP14", "other", te=1, power=0.50),  # [K] repeater
    BusType("FTD14", "other", te=1, power=0.53),  # [K] telegram duplicator
    # pushbutton inputs of the bus
    BusType("FTS14EM", "input", te=2, addresses=0, power=0.13),  # [K] 10 inputs, no address [B]
    BusType("FTS14TG", "input", te=2.5, addresses=1, power=0.42),  # [K] 2.5 modules, address [B]
    BusType("FTS14FA", "input", te=1, power=0.50),  # [K]
    BusType("FTS14GBZ", "input", power=0.10),  # [K] power table only
    # accessories on the rail (no bus device; TB14 and BBV14 are jumpers, not modules)
    BusType("FBA14", "accessory", te=1, addresses=0),  # [K] bus coupler, power "–" [B]
    BusType("STE14", "accessory", te=1, addresses=0),  # [K] power input 230 V, power "–" [B]
    BusType("DS14", "accessory", te=0.5, addresses=0),  # [K] spacer, 9 mm
    BusType("GBA14", "accessory", te=1, addresses=0),  # [K] housing for operating instructions
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
    """A type of the series 14 that hangs on the bus (by its name); accessories do not."""
    found = bus_type(model)
    if found is not None:
        return found.role != "accessory"
    return bool(model) and bool(BUS_MODEL.match(model or ""))
