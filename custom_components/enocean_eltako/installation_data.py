"""The installation of the Eltako bus as the user documents it: buses, cabinets, modules, channels.

Pure functions on plain dicts (the content of the installation store), testable without Home
Assistant: cleaning what was stored or imported, checking an edit, taking over what the notes of
a gateway hold from before the store existed (notes version 7), and the values the notes keep as
a readable copy. Concept: docs/mockups/eltako-bus-konzept.md, section 4.

A module is one device on the DIN rail (an FSR14-4x, say); each of its channels has one bus
address, first_address + n - 1. A channel is a device in Home Assistant (entry_id + device_key,
the subentry's unique ID), an entry written by hand in the notes (entry_id + manual_id) or only
written down here (name, function).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from .bus_devices import ADDRESSES, ROLES, bus_type, is_bus_model

MAX_BUSES = 8
MAX_CABINETS = 20
MAX_ROWS = 12  # per cabinet
MAX_MODULES = 300
MAX_CHANNELS = 16  # per module
MAX_ROW_TE = 48
DEFAULT_ROW_TE = 12  # the user's decision: 12 TE per row unless set otherwise
MODULE_ROLES = (*ROLES, "foreign")  # foreign: on the rail, not on the bus (a circuit breaker)
OFF_BUS = ("foreign", "accessory")  # on the rail, without address, load or channels
NEXT_KINDS = ("", "bbv14", "fba14", "cable")
VIA = ("radio", "wired")
TEXT = {"name": 80, "type": 40, "note": 500, "circuit": 80, "fuse": 40, "revision": 40}
_WATTS = re.compile(r"\d{1,4}([.,]\d{1,3})?")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ID = re.compile(r"[0-9A-Fa-f]{2}(-[0-9A-Fa-f]{2}){3}")
_RANGE = re.compile(r"(\d{1,3})-(\d{1,3})")
_SLOT = re.compile(r"(?:[^\d]*\s)?(\d{1,2})(?:\s*[.,]\s*(0|5))?")
BUS_FIELDS = ("bus_address", "feedback_id", "bus_power")


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def empty() -> dict[str, Any]:
    return {"buses": [], "cabinets": [], "modules": []}


def watts(text: str | None) -> float | None:
    """A number of watts as the user writes it (1,2 or 1.2); None when it is none."""
    text = str(text or "").strip()
    return float(text.replace(",", ".")) if _WATTS.fullmatch(text) else None


def _half(value: Any) -> float | None:
    """A position or width in steps of half a TE."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number * 2 == int(number * 2) else None


def _text(value: Any, length: int) -> str:
    return str(value or "").strip()[:length]


# ---- reading a module --------------------------------------------------------------------------


def role(module: dict[str, Any]) -> str:
    """What a module is on the bus: the role written down, else the catalog's, else other."""
    if module.get("role") in MODULE_ROLES:
        return str(module["role"])
    found = bus_type(module.get("type"))
    return found.role if found else "other"


def te_of(module: dict[str, Any]) -> float:
    """Its width in TE: written down, else the catalog's, else one."""
    if module.get("te"):
        return float(module["te"])
    found = bus_type(module.get("type"))
    return float(found.te) if found and found.te else 1.0


def address_count(module: dict[str, Any]) -> int:
    """How many bus addresses it takes: the catalog's, at least its highest channel number."""
    if role(module) in ("master", "supply", *OFF_BUS):
        return 0
    found = bus_type(module.get("type"))
    count = found.addresses if found and found.addresses is not None else 0
    count = max(count, *(c["n"] for c in module.get("channels", [])), 0)
    return count or 1


def channel_address(module: dict[str, Any], n: int) -> int | None:
    first = module.get("first_address")
    return None if first is None else int(first) + n - 1


def power_of(module: dict[str, Any]) -> tuple[float | None, str]:
    """What it takes from the bus and where the value comes from: user, table or none."""
    if (value := watts(module.get("power"))) is not None:
        return value, "user"
    found = bus_type(module.get("type"))
    if found and found.power is not None:
        return found.power, "table"
    return None, ""


def supply_of(module: dict[str, Any]) -> float | None:
    """What a master or power supply delivers to the bus, in watts."""
    if (value := watts(module.get("supply_watts"))) is not None:
        return value
    found = bus_type(module.get("type"))
    if found and found.supply is not None:
        return found.supply
    return 12.0 if role(module) in ("master", "supply") else None


def legacy_range(module: dict[str, Any]) -> tuple[int, int] | None:
    if match := _RANGE.fullmatch(str(module.get("legacy_range") or "")):
        return int(match[1]), int(match[2])
    return None


# ---- cleaning what is stored or imported -------------------------------------------------------


def _clean_channel(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    try:
        n = int(raw["n"])
    except (KeyError, TypeError, ValueError):
        return None
    if not 1 <= n <= MAX_CHANNELS:
        return None
    feedback = _text(raw.get("feedback_id"), 16)
    return {
        "n": n,
        "entry_id": _text(raw.get("entry_id"), 64) or None,
        "device_key": _text(raw.get("device_key"), 64) or None,
        "manual_id": _text(raw.get("manual_id"), 32) or None,
        "name": _text(raw.get("name"), 80),
        "function": _text(raw.get("function"), 200),
        "feedback_id": feedback,
        "unused": bool(raw.get("unused")),
    }


def _clean_module(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    channels: dict[int, dict[str, Any]] = {}
    for item in raw.get("channels") or []:
        if (channel := _clean_channel(item)) is not None:
            channels.setdefault(channel["n"], channel)
    first = raw.get("first_address")
    try:
        first = int(first) if first not in (None, "") else None
    except (TypeError, ValueError):
        first = None
    if first is not None and not 1 <= first <= ADDRESSES:
        first = None
    slot = _half(raw.get("slot")) if raw.get("row") else None
    te = _half(raw.get("te")) if raw.get("te") not in (None, "") else None
    return {
        "id": _text(raw["id"], 32),
        "bus": _text(raw.get("bus"), 32),
        "type": _text(raw.get("type"), TEXT["type"]),
        "role": raw.get("role") if raw.get("role") in MODULE_ROLES else "",
        "name": _text(raw.get("name"), TEXT["name"]),
        "row": _text(raw.get("row"), 32) if slot is not None else None,
        "slot": slot,
        "te": te if te and 0 < te <= MAX_ROW_TE else None,
        "spacer_before": bool(raw.get("spacer_before")),
        "separator_after": bool(raw.get("separator_after")),
        "terminator": bool(raw.get("terminator")),
        "first_address": first,
        "supply_watts": _text(raw.get("supply_watts"), 8)
        if _WATTS.fullmatch(_text(raw.get("supply_watts"), 8))
        else "",
        "legacy_range": _text(raw.get("legacy_range"), 7)
        if _RANGE.fullmatch(_text(raw.get("legacy_range"), 7))
        else "",
        "legacy_location": _text(raw.get("legacy_location"), 120),
        "origin": _text(raw.get("origin"), 64) or None,
        "supply_id": _text(raw.get("supply_id"), 32) or None,
        "placeholder": bool(raw.get("placeholder")),
        "power": _text(raw.get("power"), 8) if _WATTS.fullmatch(_text(raw.get("power"), 8)) else "",
        "circuit": _text(raw.get("circuit"), TEXT["circuit"]),
        "fuse": _text(raw.get("fuse"), TEXT["fuse"]),
        "installed": _text(raw.get("installed"), 10)
        if _DATE.fullmatch(_text(raw.get("installed"), 10))
        else "",
        "revision": _text(raw.get("revision"), TEXT["revision"]),
        "note": _text(raw.get("note"), TEXT["note"]),
        "channels": sorted(channels.values(), key=lambda c: c["n"]),
    }


def _clean_row(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    try:
        te = int(raw.get("te") or DEFAULT_ROW_TE)
    except (TypeError, ValueError):
        te = DEFAULT_ROW_TE
    nxt: dict[str, Any] = raw["next"] if isinstance(raw.get("next"), dict) else {}
    length = nxt.get("length_m")
    try:
        length = round(float(length), 1) if length not in (None, "") else None
    except (TypeError, ValueError):
        length = None
    return {
        "id": _text(raw["id"], 32),
        "name": _text(raw.get("name"), 60),
        "te": min(max(te, 1), MAX_ROW_TE),
        "next": {
            "kind": nxt.get("kind") if nxt.get("kind") in NEXT_KINDS else "",
            "length_m": length if length is None or 0 <= length <= 1000 else None,
        },
    }


def _clean_cabinet(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    rows = [r for r in map(_clean_row, raw.get("rows") or []) if r is not None]
    return {
        "id": _text(raw["id"], 32),
        "name": _text(raw.get("name"), 60),
        "area_id": _text(raw.get("area_id"), 64) or None,
        "note": _text(raw.get("note"), TEXT["note"]),
        "rows": rows[:MAX_ROWS],
    }


def _clean_bus(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not raw.get("id"):
        return None
    access = []
    for item in raw.get("access") or []:
        if isinstance(item, dict) and item.get("entry_id"):
            via = item.get("via") if item.get("via") in VIA else "radio"
            access.append({"entry_id": _text(item["entry_id"], 64), "via": via})
    base = _text(raw.get("base_id"), 11).upper()
    return {
        "id": _text(raw["id"], 32),
        "name": _text(raw.get("name"), 60),
        "master": _text(raw.get("master"), 32) or None,
        "base_id": base if _ID.fullmatch(base) else "",
        "access": access,
        "bus_group": _text(raw.get("bus_group"), 32) or None,
        "note": _text(raw.get("note"), TEXT["note"]),
    }


def normalize(raw: Any) -> dict[str, Any]:
    """What was stored or imported, with every field present and nothing that does not fit."""
    raw = raw if isinstance(raw, dict) else {}
    buses = [b for b in map(_clean_bus, raw.get("buses") or []) if b][:MAX_BUSES]
    cabinets = [c for c in map(_clean_cabinet, raw.get("cabinets") or []) if c][:MAX_CABINETS]
    modules = [m for m in map(_clean_module, raw.get("modules") or []) if m][:MAX_MODULES]
    bus_ids = {b["id"] for b in buses}
    row_ids = {r["id"] for c in cabinets for r in c["rows"]}
    for module in modules:
        if module["bus"] not in bus_ids:
            module["bus"] = buses[0]["id"] if buses else ""
        if module["row"] not in row_ids:
            module["row"], module["slot"] = None, None
    module_ids = {m["id"] for m in modules}
    for bus in buses:
        if bus["master"] not in module_ids:
            bus["master"] = None
    return {"buses": buses, "cabinets": cabinets, "modules": modules}


# ---- places ------------------------------------------------------------------------------------


def rows_by_id(data: dict[str, Any]) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {r["id"]: (c, r) for c in data["cabinets"] for r in c["rows"]}


def _span(module: dict[str, Any]) -> tuple[float, float]:
    """The part of the rail a module takes, its spacer to the left included (in TE)."""
    start = float(module["slot"]) - (0.5 if module.get("spacer_before") else 0)
    return start, float(module["slot"]) + te_of(module)


def place_problem(data: dict[str, Any], module: dict[str, Any]) -> str | None:
    """Why a module cannot sit where it says (None: it fits): grid, row width, overlap."""
    if module.get("row") is None:
        return None
    found = rows_by_id(data).get(module["row"])
    if found is None:
        return "unknown_row"
    slot = module.get("slot")
    if slot is None or _half(slot) is None or slot < 1:
        return "invalid_slot"
    start, end = _span(module)
    if start < 1 or end > found[1]["te"] + 1:
        return "row_full"
    for other in data["modules"]:
        if other["id"] == module["id"] or other.get("row") != module["row"]:
            continue
        if other.get("slot") is None:
            continue
        o_start, o_end = _span(other)
        if start < o_end and o_start < end:
            return "overlap"
    return None


def place_text(data: dict[str, Any], module: dict[str, Any]) -> str:
    """Cabinet · row · slot, the way the notes write a place; empty without one."""
    found = rows_by_id(data).get(module.get("row") or "")
    if found is None or module.get("slot") is None:
        return ""
    slot = float(module["slot"])
    number = str(int(slot)) if slot == int(slot) else str(slot).replace(".", ",")
    return " · ".join(p for p in (found[0]["name"], found[1]["name"], number) if p)


def parse_place(text: str) -> tuple[str, str, float | None]:
    """Cabinet, row and slot of a place written "cabinet · row · slot" (or with commas)."""
    value = str(text or "")
    parts = [p.strip() for p in value.split("·" if "·" in value else ",")]
    cabinet = parts[0] if parts else ""
    row = parts[1] if len(parts) > 1 else ""
    slot = None
    if len(parts) > 2 and (match := _SLOT.fullmatch(",".join(parts[2:]).strip())):
        slot = float(match[1]) + (0.5 if match[2] == "5" else 0)
        slot = slot if slot >= 1 else None
    return cabinet, row, slot


def place_from_text(data: dict[str, Any], module: dict[str, Any], text: str) -> bool:
    """Put a module where a place written as text says, creating cabinet and row by name.

    Only a complete place (cabinet, row and a slot that is a number) that fits is taken; else
    the module stays without a place and keeps the text (legacy_location).
    """
    cabinet_name, row_name, slot = parse_place(text)
    if not (cabinet_name and row_name and slot is not None):
        module["legacy_location"] = _text(text, 120)
        return False
    cabinet = next(
        (c for c in data["cabinets"] if c["name"].casefold() == cabinet_name.casefold()), None
    )
    if cabinet is None and len(data["cabinets"]) < MAX_CABINETS:
        cabinet = {"id": new_id(), "name": cabinet_name[:60], "area_id": None, "note": ""}
        cabinet["rows"] = []
        data["cabinets"].append(cabinet)
    if cabinet is None:
        module["legacy_location"] = _text(text, 120)
        return False
    row = next((r for r in cabinet["rows"] if r["name"].casefold() == row_name.casefold()), None)
    if row is None and len(cabinet["rows"]) < MAX_ROWS:
        row = {"id": new_id(), "name": row_name[:60], "te": DEFAULT_ROW_TE}
        row["next"] = {"kind": "", "length_m": None}
        cabinet["rows"].append(row)
    if row is None:
        module["legacy_location"] = _text(text, 120)
        return False
    needed = int(slot + te_of(module) - 1 + 0.5)
    if needed > row["te"] and needed <= MAX_ROW_TE:
        row["te"] = needed  # a written place beyond 12 TE: the row is wider
    module["row"], module["slot"] = row["id"], slot
    if place_problem(data, module) is not None:
        module["row"], module["slot"] = None, None
        module["legacy_location"] = _text(text, 120)
        return False
    module["legacy_location"] = ""
    return True


# ---- an edit from the panel --------------------------------------------------------------------


def blank_module(bus: str, **fields: Any) -> dict[str, Any]:
    module = _clean_module({"id": new_id(), "bus": bus, **fields})
    assert module is not None
    return module


def check_module(data: dict[str, Any], raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """A module as the panel sends it, cleaned and checked against the others.

    Returns (module, "") or (None, reason): the bus must exist, the place fit (half-TE grid,
    row width, no overlap), the addresses lie in 1..126 and a device be a channel only once.
    Duplicate addresses are kept (and reported by the checks): the documentation may record
    what is wrong in the cabinet.
    """
    module = _clean_module({**raw, "id": raw.get("id") or new_id()})
    if module is None:
        return None, "invalid_format"
    if module["bus"] not in {b["id"] for b in data["buses"]}:
        return None, "unknown_bus"
    for field in ("power", "supply_watts", "installed", "legacy_range"):
        if str(raw.get(field) or "").strip() and not module[field]:
            return None, f"invalid_{field}"
    if raw.get("row") and module["row"] is None:
        return None, "invalid_slot"
    if raw.get("te") not in (None, "") and module["te"] is None:
        return None, "invalid_te"
    if raw.get("first_address") not in (None, "") and module["first_address"] is None:
        return None, "invalid_address"
    if len(raw.get("channels") or []) > MAX_CHANNELS or len(module["channels"]) != len(
        raw.get("channels") or []
    ):
        return None, "invalid_channel"
    if module["first_address"] is not None:
        if module["first_address"] + address_count(module) - 1 > ADDRESSES:
            return None, "address_range"
    if (problem := place_problem(data, module)) is not None:
        return None, problem
    taken = {
        (c["entry_id"], c["device_key"]): m["id"]
        for m in data["modules"]
        for c in m["channels"]
        if c["device_key"]
    }
    seen = set()
    for channel in module["channels"]:
        if channel["device_key"]:
            key = (channel["entry_id"], channel["device_key"])
            if taken.get(key, module["id"]) != module["id"] or key in seen:
                return None, "device_in_use"
            seen.add(key)
    if module["id"] not in {m["id"] for m in data["modules"]} and len(data["modules"]) >= (
        MAX_MODULES
    ):
        return None, "too_many"
    return module, ""


def check_cabinet(data: dict[str, Any], raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """A cabinet with its rows as the panel sends it; a row may not get narrower than its use."""
    if len(raw.get("rows") or []) > MAX_ROWS:
        return None, "too_many"
    rows = [
        {**r, "id": r.get("id") or new_id()} if isinstance(r, dict) else r
        for r in raw.get("rows") or []
    ]
    cabinet = _clean_cabinet({**raw, "id": raw.get("id") or new_id(), "rows": rows})
    if cabinet is None or len(cabinet["rows"]) != len(rows):
        return None, "invalid_format"
    is_new = cabinet["id"] not in {c["id"] for c in data["cabinets"]}
    if is_new and len(data["cabinets"]) >= MAX_CABINETS:
        return None, "too_many"
    widths = {r["id"]: r["te"] for r in cabinet["rows"]}
    for module in data["modules"]:
        if module.get("row") in widths and module.get("slot") is not None:
            if _span(module)[1] > widths[module["row"]] + 1:
                return None, "row_full"
    return cabinet, ""


def check_bus(data: dict[str, Any], raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    bus = _clean_bus({**raw, "id": raw.get("id") or new_id()})
    if bus is None:
        return None, "invalid_format"
    if str(raw.get("base_id") or "").strip() and not bus["base_id"]:
        return None, "invalid_base_id"
    if bus["master"] is not None:
        master = next((m for m in data["modules"] if m["id"] == bus["master"]), None)
        if master is None or master["bus"] != bus["id"]:
            return None, "unknown_master"
    if bus["id"] not in {b["id"] for b in data["buses"]} and len(data["buses"]) >= MAX_BUSES:
        return None, "too_many"
    return bus, ""


# ---- taking over the notes of a gateway (notes version 7 -> 8) ---------------------------------


def bus_for(
    data: dict[str, Any], entry_id: str, wired: bool, group: str | None
) -> dict[str, Any] | None:
    """The bus a gateway reaches (a bus group shares one), created when there is none."""
    bus = None
    if wired and group:
        bus = next((b for b in data["buses"] if b.get("bus_group") == group), None)
    if bus is None:
        bus = next(
            (b for b in data["buses"] if any(a["entry_id"] == entry_id for a in b["access"])),
            None,
        )
    if bus is None:
        if len(data["buses"]) >= MAX_BUSES:
            return None
        bus = {"id": new_id(), "name": "", "master": None, "base_id": "", "access": []}
        bus |= {"bus_group": None, "note": ""}
        data["buses"].append(bus)
    if not any(a["entry_id"] == entry_id for a in bus["access"]):
        bus["access"].append({"entry_id": entry_id, "via": "wired" if wired else "radio"})
    if wired and group:
        bus["bus_group"] = group
    return bus


def ensure_master(data: dict[str, Any], bus: dict[str, Any]) -> None:
    """A bus has a master: a documented FAM14 (or FTS14KS), else a placeholder without place."""
    ids = {m["id"]: m for m in data["modules"] if m["bus"] == bus["id"]}
    if bus.get("master") in ids:
        return
    if found := next((m for m in ids.values() if role(m) == "master"), None):
        bus["master"] = found["id"]
        return
    if len(data["modules"]) >= MAX_MODULES:
        return
    master = blank_module(bus["id"], type="FAM14", placeholder=True)
    data["modules"].append(master)
    bus["master"] = master["id"]


def _has_bus_fields(values: dict[str, Any]) -> bool:
    return any(str(values.get(f) or "").strip() for f in BUS_FIELDS)


def _address(text: Any) -> int | None:
    text = str(text or "").strip()
    return int(text) if text.isdigit() and 1 <= int(text) <= ADDRESSES else None


def absorb(data: dict[str, Any], gateway: dict[str, Any], *, models: bool = True) -> int:
    """Take over what the notes of one gateway hold for the bus; how many modules were added.

    gateway: {entry_id, title, wired, bus_group, devices: [{key, name, model, group, location,
    bus_address, feedback_id, bus_power}], supplies: [notes supply], manual: [notes entry]}.
    Devices with a bus field or a type of the series 14 become channels: those with the same
    "part of" text and type and addresses within one device form one module (channel = address
    minus the first one plus one), any other is a module of its own. Supplies become power
    supply modules that keep their address range; entries by hand with a bus address become a
    module with one channel. What is taken already (by device, entry or supply) is left alone,
    so it can run again (an import of an old export); without models, a device needs a bus
    field (a type of the series 14 alone is then a check: "not assigned").
    """
    entry_id = gateway["entry_id"]
    devices = [
        d
        for d in gateway.get("devices", [])
        if _has_bus_fields(d) or (models and is_bus_model(d.get("model")))
    ]
    manual = [m for m in gateway.get("manual", []) if _address(m.get("bus_address"))]
    supplies = [s for s in gateway.get("supplies", []) if isinstance(s, dict) and s.get("id")]
    if not (devices or manual or supplies):
        return 0
    bus = bus_for(data, entry_id, bool(gateway.get("wired")), gateway.get("bus_group"))
    if bus is None:
        return 0
    channels = {(c["entry_id"], c["device_key"]) for m in data["modules"] for c in m["channels"]}
    manuals = {(c["entry_id"], c["manual_id"]) for m in data["modules"] for c in m["channels"]}
    supply_ids = {(m["origin"], m["supply_id"]) for m in data["modules"] if m["supply_id"]}
    added = 0

    def add(module: dict[str, Any], location: str) -> None:
        nonlocal added
        if len(data["modules"]) >= MAX_MODULES:
            return
        data["modules"].append(module)
        if location:
            place_from_text(data, module, location)
        added += 1

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for device in devices:
        if (entry_id, device["key"]) in channels:
            continue
        group = str(device.get("group") or "").strip()
        model = str(device.get("model") or "").strip()
        key = (group.casefold(), model.casefold()) if group else ("", device["key"])
        groups.setdefault(key, []).append(device)
    for (group, _model), members in groups.items():
        found = bus_type(members[0].get("model"))
        capacity = found.addresses if found and found.addresses else len(members)
        chunks: list[dict[str, Any]] = []
        addressed = sorted(
            (d for d in members if _address(d.get("bus_address"))),
            key=lambda d: _address(d["bus_address"]) or 0,
        )
        for device in addressed:
            addr = _address(device["bus_address"]) or 0
            chunk = chunks[-1] if chunks else None
            if chunk and chunk["first"] is not None and 0 <= addr - chunk["first"] < capacity:
                n = addr - chunk["first"] + 1
                if n not in chunk["members"]:
                    chunk["members"][n] = device
                    continue
            chunks.append({"first": addr, "members": {1: device}})
        for device in (d for d in members if not _address(d.get("bus_address"))):
            chunk = (
                next((c for c in chunks if len(c["members"]) < capacity), None) if group else None
            )
            if chunk is None:
                chunk = {"first": None, "members": {}}
                chunks.append(chunk)
            n = next(i for i in range(1, MAX_CHANNELS + 2) if i not in chunk["members"])
            chunk["members"][n] = device
        for chunk in chunks:
            ordered = sorted(chunk["members"].items())
            if ordered[-1][0] > MAX_CHANNELS:
                continue
            first_device = ordered[0][1]
            power = next((d["bus_power"] for _, d in ordered if watts(d.get("bus_power"))), "")
            module = blank_module(
                bus["id"],
                type=str(first_device.get("model") or ""),
                name=str(members[0].get("group") or "") if group else "",
                first_address=chunk["first"],
                power=power,
                channels=[
                    {
                        "n": n,
                        "entry_id": entry_id,
                        "device_key": d["key"],
                        "feedback_id": d.get("feedback_id", ""),
                    }
                    for n, d in ordered
                ],
            )
            location = next((str(d["location"]) for _, d in ordered if d.get("location")), "")
            add(module, location)
    for supply in supplies:
        if (entry_id, supply["id"]) in supply_ids:
            continue
        first, last = _address(supply.get("first")), _address(supply.get("last"))
        module = blank_module(
            bus["id"],
            type=str(supply.get("name") or "FSNT14-12V/12W"),
            role="supply",
            supply_watts=supply.get("watts", ""),
            legacy_range=f"{first or 1}-{last or ADDRESSES}" if first or last else "",
            circuit=supply.get("circuit", ""),
            fuse=supply.get("fuse", ""),
            note=supply.get("note", ""),
            origin=entry_id,
            supply_id=supply["id"],
        )
        add(module, str(supply.get("location") or ""))
    for entry in manual:
        if (entry_id, entry.get("id")) in manuals:
            continue
        model = str(entry.get("model") or "")
        name = str(entry.get("name") or "")
        module = blank_module(
            bus["id"],
            type=model or (name if is_bus_model(name) else ""),
            first_address=_address(entry.get("bus_address")),
            power=entry.get("bus_power", ""),
            circuit=entry.get("circuit", ""),
            fuse=entry.get("fuse", ""),
            installed=entry.get("installed", ""),
            origin=entry_id,
            channels=[
                {
                    "n": 1,
                    "entry_id": entry_id,
                    "manual_id": entry["id"],
                    "name": name,
                    "function": entry.get("function", ""),
                    "feedback_id": entry.get("feedback_id", ""),
                }
            ],
        )
        add(module, str(entry.get("location") or ""))
    ensure_master(data, bus)
    return added


# ---- the copy the notes keep -------------------------------------------------------------------


def _first_linked(module: dict[str, Any]) -> int | None:
    linked = [c["n"] for c in module["channels"] if c["device_key"] or c["manual_id"]]
    return min(linked) if linked else None


def channel_values(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    """The bus fields each device in Home Assistant gets in the notes: address, feedback ID and
    the module's power (on its first linked channel only, so a module counts once)."""
    values = {}
    for module in data["modules"]:
        first = _first_linked(module)
        for channel in module["channels"]:
            if not (channel["entry_id"] and channel["device_key"]):
                continue
            address = channel_address(module, channel["n"])
            values[(channel["entry_id"], channel["device_key"])] = {
                "bus_address": "" if address is None else str(address),
                "feedback_id": channel["feedback_id"],
                "bus_power": module["power"] if channel["n"] == first else "",
            }
    return values


def manual_values(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    """The fields an entry by hand gets back in the notes from its channel."""
    values = {}
    for module in data["modules"]:
        first = _first_linked(module)
        for channel in module["channels"]:
            if not (channel["entry_id"] and channel["manual_id"]):
                continue
            address = channel_address(module, channel["n"])
            values[(channel["entry_id"], channel["manual_id"])] = {
                "name": channel["name"],
                "function": channel["function"],
                "bus_address": "" if address is None else str(address),
                "feedback_id": channel["feedback_id"],
                "bus_power": module["power"] if channel["n"] == first else "",
                "circuit": module["circuit"],
                "fuse": module["fuse"],
                "installed": module["installed"],
            }
    return values


def supply_values(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    """The fields a power supply of the notes gets back from its module."""
    values = {}
    for module in data["modules"]:
        if not (module["origin"] and module["supply_id"]):
            continue
        span = legacy_range(module)
        values[(module["origin"], module["supply_id"])] = {
            "name": module["type"],
            "watts": module["supply_watts"],
            "first": str(span[0]) if span else "",
            "last": str(span[1]) if span else "",
            "location": place_text(data, module) or module["legacy_location"],
            "circuit": module["circuit"],
            "fuse": module["fuse"],
            "note": module["note"],
        }
    return values


# ---- what the old fields of the panel write (the notes), taken over into the store -------------


def _find_channel(
    data: dict[str, Any], entry_id: str, field: str, value: str
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for module in data["modules"]:
        for channel in module["channels"]:
            if channel["entry_id"] == entry_id and channel[field] == value:
                return module, channel
    return None


def _drop_channel(data: dict[str, Any], module: dict[str, Any], channel: dict[str, Any]) -> None:
    """Remove a channel; a module left without any (and not a supply or master) goes as well."""
    module["channels"] = [c for c in module["channels"] if c is not channel]
    if not module["channels"] and role(module) not in ("master", "supply"):
        data["modules"] = [m for m in data["modules"] if m is not module]


def _set_address(module: dict[str, Any], n: int, text: str) -> None:
    """A channel's address written in the old field: its module's addresses follow."""
    address = _address(text)
    if address is None:
        if not text.strip() and len([c for c in module["channels"] if not c["unused"]]) <= 1:
            module["first_address"] = None
        return
    first = address - n + 1
    if first >= 1 and first + address_count(module) - 1 <= ADDRESSES:
        module["first_address"] = first


def _set_power(module: dict[str, Any], n: int, text: str) -> None:
    if watts(text) is not None:
        module["power"] = text.strip()
    elif not text.strip() and n == _first_linked(module):
        module["power"] = ""


def apply_device(
    data: dict[str, Any],
    gateway: dict[str, Any],
    device: dict[str, Any],
    values: dict[str, str],
    *,
    create: bool = True,
) -> bool:
    """The bus fields of a device written in an old field of the panel (or imported in the
    notes): its channel follows, or a module of its own is made for it. True if anything changed.
    """
    before = repr(data)
    found = _find_channel(data, gateway["entry_id"], "device_key", device["key"])
    if found is None:
        if create and _has_bus_fields(values):
            absorb(
                data, {**gateway, "devices": [{**device, **values}], "supplies": [], "manual": []}
            )
        return repr(data) != before
    module, channel = found
    if "bus_address" in values:
        _set_address(module, channel["n"], str(values["bus_address"]))
    if "feedback_id" in values:
        channel["feedback_id"] = _text(values["feedback_id"], 16)
    if "bus_power" in values:
        _set_power(module, channel["n"], str(values["bus_power"]))
    return repr(data) != before


def sync_supplies(
    data: dict[str, Any], gateway: dict[str, Any], supplies: list[dict[str, str]]
) -> bool:
    """The power supplies of a gateway's notes as the old bus view writes them: their modules
    follow (changed, added, removed). True if anything changed."""
    before = repr(data)
    entry_id = gateway["entry_id"]
    mine = {
        m["supply_id"]: m for m in data["modules"] if m["origin"] == entry_id and m["supply_id"]
    }
    given = {s["id"] for s in supplies if s.get("id")}
    data["modules"] = [
        m
        for m in data["modules"]
        if not (m["origin"] == entry_id and m["supply_id"] not in (None, *given))
    ]
    for supply in supplies:
        module = mine.get(supply.get("id", ""))
        if module is None:
            continue
        first, last = _address(supply.get("first")), _address(supply.get("last"))
        module["type"] = _text(supply.get("name"), TEXT["type"]) or module["type"]
        module["supply_watts"] = supply.get("watts", "") if watts(supply.get("watts")) else ""
        module["legacy_range"] = f"{first or 1}-{last or ADDRESSES}" if first or last else ""
        for field in ("circuit", "fuse", "note"):
            module[field] = _text(supply.get(field), TEXT[field])
        text = str(supply.get("location") or "").strip()
        if text != (place_text(data, module) or module["legacy_location"]):
            module["row"], module["slot"] = None, None
            if text:
                place_from_text(data, module, text)
            else:
                module["legacy_location"] = ""
    absorb(data, {**gateway, "devices": [], "manual": [], "supplies": supplies})
    return repr(data) != before


def sync_manual(
    data: dict[str, Any], gateway: dict[str, Any], entries: list[dict[str, str]]
) -> bool:
    """The entries by hand of a gateway's notes: one with a bus address is a channel (taken over
    or followed), one without (or removed) is no longer. True if anything changed."""
    before = repr(data)
    entry_id = gateway["entry_id"]
    given = {e["id"]: e for e in entries if e.get("id")}
    for module in list(data["modules"]):
        for channel in list(module["channels"]):
            if channel["entry_id"] != entry_id or not channel["manual_id"]:
                continue
            entry = given.get(channel["manual_id"])
            if entry is None or _address(entry.get("bus_address")) is None:
                _drop_channel(data, module, channel)
                continue
            _set_address(module, channel["n"], str(entry.get("bus_address") or ""))
            _set_power(module, channel["n"], str(entry.get("bus_power") or ""))
            channel["feedback_id"] = _text(entry.get("feedback_id"), 16)
            channel["name"] = _text(entry.get("name"), 80)
            channel["function"] = _text(entry.get("function"), 200)
            for field in ("circuit", "fuse"):
                module[field] = _text(entry.get(field), TEXT[field])
            installed = _text(entry.get("installed"), 10)
            module["installed"] = installed if _DATE.fullmatch(installed) else ""
    absorb(data, {**gateway, "devices": [], "supplies": [], "manual": entries})
    return repr(data) != before


def move_module(data: dict[str, Any], module_id: str, direction: int) -> str:
    """Arrange on the rail: swap a module with its neighbour on that side, or at the end of the
    row move it by half a TE. "" when done, else why not (nothing changed then)."""
    module = next((m for m in data["modules"] if m["id"] == module_id), None)
    if module is None:
        return "not_found"
    if module.get("row") is None:
        return "invalid_slot"
    row = sorted(
        (m for m in data["modules"] if m.get("row") == module["row"] and m.get("slot") is not None),
        key=lambda m: m["slot"],
    )
    index = row.index(module)
    before = {m["id"]: m["slot"] for m in row}
    neighbour = row[index + direction] if 0 <= index + direction < len(row) else None

    def spacer(m: dict[str, Any]) -> float:
        return 0.5 if m.get("spacer_before") else 0.0

    if neighbour is not None:
        left, right = (neighbour, module) if direction < 0 else (module, neighbour)
        start = left["slot"] - spacer(left)
        right["slot"] = start + spacer(right)
        left["slot"] = right["slot"] + te_of(right) + spacer(left)
    else:
        module["slot"] = module["slot"] + 0.5 * direction
    for moved in (module, neighbour):
        if moved is not None and (problem := place_problem(data, moved)) is not None:
            for m in row:
                m["slot"] = before[m["id"]]
            return "row_full" if problem == "invalid_slot" else problem  # at the edge of the row
    return ""


def remove_module(data: dict[str, Any], module_id: str) -> dict[str, Any] | None:
    """Take a module out; a bus whose master it was gets none (the checks say so)."""
    module: dict[str, Any] | None = next((m for m in data["modules"] if m["id"] == module_id), None)
    if module is None:
        return None
    data["modules"] = [m for m in data["modules"] if m["id"] != module_id]
    for bus in data["buses"]:
        if bus["master"] == module_id:
            bus["master"] = None
    return module
