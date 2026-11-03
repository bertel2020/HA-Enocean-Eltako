"""Checks of the documented Eltako bus, and the load of its power supplies.

A pure function of the installation store's content and of what Home Assistant holds, so it is
tested without Home Assistant. The panel shows the result as it is: each finding has a level, a
code with its arguments (the panel words it, in German or English) and what it is about.

Power supplies: when every power supply of a bus has a place (and the master too), a supply
feeds the modules of its section, the rail in bus order up to a separator bridge (TB14) or the
end of a cabinet; otherwise the address ranges written down before the store existed decide, as
the bus view always did: a supply feeds the addresses of its range, a lone one without a range
all of them, and without any supply the one inside the FAM14 feeds the whole bus.
"""

from __future__ import annotations

from typing import Any

from .bus_devices import ADDRESSES
from .installation_data import (
    _span,
    address_count,
    channel_address,
    legacy_range,
    power_of,
    role,
    rows_by_id,
    supply_of,
    watts,
)

RESERVE_LIMIT = 2 / 3  # above this share of its rated power a supply should get company
NOT_CONSUMERS = ("master", "supply", "foreign", "accessory")
# ventilation of the FSNT14 (manual FAM14 30014000-7 and operating manual series 14, 10/2026,
# "mounting in the distribution panel"): with a load of the power supply above 4 W half a TE of
# air on its left side to the neighbouring devices, above 6 W in addition half a TE between the
# FSNT14 and the FAM14 (spacer DS14)
AIR_LEFT_WATTS = 4.0
AIR_FAM14_WATTS = 6.0


def _item(level: str, code: str, targets: list[dict[str, str]], **args: Any) -> dict[str, Any]:
    return {"level": level, "code": code, "args": args, "targets": targets}


def _module(module: dict[str, Any]) -> dict[str, str]:
    return {"type": "module", "id": module["id"]}


def _channel(module: dict[str, Any], n: int) -> dict[str, str]:
    return {"type": "channel", "id": f"{module['id']}:{n}"}


def _runs(numbers: list[int]) -> list[str]:
    """1, 2, 3, 7 -> ["1-3", "7"]."""
    runs: list[str] = []
    for n in sorted(set(numbers)):
        if runs and int(runs[-1].split("-")[-1]) == n - 1:
            runs[-1] = f"{runs[-1].split('-')[0]}-{n}"
        else:
            runs.append(str(n))
    return runs


def bus_order(data: dict[str, Any], modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The placed modules in the order the bus runs: cabinet, row, slot."""
    position = {}
    for i, cabinet in enumerate(data["cabinets"]):
        for j, row in enumerate(cabinet["rows"]):
            position[row["id"]] = (i, j)
    placed = [m for m in modules if m.get("row") in position and m.get("slot") is not None]
    return sorted(placed, key=lambda m: (*position[m["row"]], m["slot"]))


def _state(load: float, capacity: float | None) -> str:
    if capacity is None:
        return "ok"
    if not capacity or load > capacity:
        return "over"
    return "reserve" if load > capacity * RESERVE_LIMIT else "ok"


def supply_loads(data: dict[str, Any], bus: dict[str, Any]) -> dict[str, Any]:
    """The load of each power supply of a bus, and the modules no supply feeds."""
    modules = [m for m in data["modules"] if m["bus"] == bus["id"]]
    supplies = [m for m in modules if role(m) == "supply"]
    master = next((m for m in modules if m["id"] == bus.get("master")), None)
    feeding = [*supplies, *([master] if master and not master["placeholder"] else [])]
    if supplies and all(m.get("row") for m in feeding):
        return _by_place(data, modules)
    consumers = [m for m in modules if role(m) not in NOT_CONSUMERS and m["first_address"]]
    groups = []
    if supplies:
        for supply in supplies:
            groups.append({"module": supply["id"], "range": legacy_range(supply), "members": []})
    else:
        groups.append({"module": master["id"] if master else None, "range": None, "members": []})
    lone = len(groups) == 1 and groups[0]["range"] is None
    unfed = []
    for module in consumers:
        address = module["first_address"]
        found = (
            groups[0]
            if lone
            else next(
                (g for g in groups if g["range"] and g["range"][0] <= address <= g["range"][1]),
                None,
            )
        )
        if found is None:
            unfed.append(module["id"])
        else:
            found["members"].append(module)
    by_id = {m["id"]: m for m in modules}
    result = []
    for group in groups:
        source = by_id.get(group["module"] or "")
        capacity = supply_of(source) if source else 12.0
        if source is not None and role(source) == "master":
            # no supply written down: the master's own one (or the FSNT14 that came with it)
            capacity = watts(source.get("supply_watts")) or supply_of(source) or 12.0
        load = round(sum(power_of(m)[0] or 0 for m in group["members"]), 2)
        result.append(
            {
                "module": group["module"],
                "range": "-".join(map(str, group["range"])) if group["range"] else None,
                "capacity": capacity,
                "load": load,
                "state": _state(load, capacity),
                "members": [m["id"] for m in group["members"]],
                "without_value": [m["id"] for m in group["members"] if power_of(m)[0] is None],
            }
        )
    return {"mode": "range", "supplies": result, "unfed": unfed}


def master_supply(master: dict[str, Any], section: list[dict[str, Any]]) -> tuple[float, str]:
    """What a FAM14 itself delivers to its section, and why: "entered" (written down), "fsnt14"
    (0 W: an FSNT14 right beside it in the same section is the supply that came with it), or
    "integrated" (the catalog's 12 W).

    Eltako: a FAM14 up to production week 07/22 has its supply unit integrated (12 V DC-1A, the
    left half of its 2 TE, manual 30014000-2 and operating manual series 14); a later FAM14
    comes with an FSNT14-12V/12W of its own (manual 30014000-7) that delivers the 12 W. That an
    FSNT14 directly beside the FAM14 is that enclosed one is an assumption; a value written down
    for the FAM14 (0 or 12 W) decides instead.
    """
    if (value := watts(master.get("supply_watts"))) is not None:
        return value, "entered"
    if master.get("row") is not None:
        for other in section:
            if other is master or other.get("row") != master["row"] or role(other) != "supply":
                continue
            if not str(other.get("type", "")).upper().startswith("FSNT14"):
                continue
            left, right = (other, master) if other["slot"] < master["slot"] else (master, other)
            if float(right["slot"]) - _span(left)[1] <= 0.5:
                return 0.0, "fsnt14"
    return supply_of(master) or 12.0, "integrated"


def _by_place(data: dict[str, Any], modules: list[dict[str, Any]]) -> dict[str, Any]:
    """Sections of the rail between separator bridges (TB14) and cabinet ends."""
    rows = rows_by_id(data)
    sections: list[list[dict[str, Any]]] = []
    last_cabinet, cut = None, True
    for module in bus_order(data, modules):
        if role(module) in ("foreign", "accessory"):
            continue
        cabinet = rows[module["row"]][0]["id"]
        if cut or cabinet != last_cabinet:
            sections.append([])
        sections[-1].append(module)
        last_cabinet, cut = cabinet, module["separator_after"]
    result = []
    for members in sections:
        own = {m["id"]: master_supply(m, members) for m in members if role(m) == "master"}
        feeders = [
            m
            for m in members
            if role(m) == "supply" or (role(m) == "master" and own[m["id"]][0] > 0)
        ]
        consumers = [m for m in members if role(m) != "supply"]
        capacity = round(
            sum((own[m["id"]][0] if m["id"] in own else supply_of(m) or 0) for m in feeders), 2
        )
        load = round(sum(power_of(m)[0] or 0 for m in consumers), 2)
        result.append(
            {
                "module": feeders[0]["id"] if feeders else None,
                "modules": [m["id"] for m in feeders],
                "range": None,
                "capacity": capacity if feeders else 0,
                "load": load,
                "state": _state(load, capacity) if feeders else "none",
                "members": [m["id"] for m in consumers],
                "without_value": [m["id"] for m in consumers if power_of(m)[0] is None],
                "master_supply": [
                    {"module": i, "watts": w, "from": source} for i, (w, source) in own.items()
                ],
            }
        )
    placed = {m["id"] for s in sections for m in s}
    unfed = [
        m["id"]
        for m in modules
        if m["id"] not in placed and role(m) not in NOT_CONSUMERS and m["first_address"]
    ]
    for i, section in enumerate(result):
        section["section"] = chr(65 + i) if i < 26 else str(i + 1)
    return {"mode": "place", "supplies": result, "unfed": unfed}


def run_checks(
    data: dict[str, Any],
    devices: dict[tuple[str, str], dict[str, Any]],
    loaded: set[str],
    observed: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Every finding per bus, the supplies' loads, and the bus devices without a module.

    observed: per bus what was heard on demand (Installation.observe): the addresses that
    answered and the base ID candidates; compared with what is documented.

    devices: the devices of the loaded gateways, (entry_id, device_key) -> {"name", "model",
    "bus": whether it looks like a bus device (a type of the series 14 or a bus field)}.
    """
    result: dict[str, Any] = {"buses": {}, "unassigned": []}
    linked = {(c["entry_id"], c["device_key"]) for m in data["modules"] for c in m["channels"]}
    for key, device in sorted(devices.items()):
        if device.get("bus") and key not in linked:
            result["unassigned"].append({"entry_id": key[0], "device_key": key[1]})
    for bus in data["buses"]:
        found = _bus_checks(data, bus, devices, loaded, result["unassigned"])
        if observed and bus["id"] in observed:
            found["items"] += _observed_checks(data, bus, observed[bus["id"]])
        result["buses"][bus["id"]] = found
    return result


def _observed_checks(
    data: dict[str, Any], bus: dict[str, Any], seen: dict[str, Any]
) -> list[dict[str, Any]]:
    """Heard on the bus versus documented. Experimental: the reading rests on Eltako's
    description of the confirmation telegrams, not on a test with a FAM14 (assumed=True)."""
    items: list[dict[str, Any]] = []
    documented: dict[int, list[tuple[dict[str, Any], int]]] = {}
    for module in (m for m in data["modules"] if m["bus"] == bus["id"]):
        for channel in module["channels"]:
            if not channel["unused"] and (a := channel_address(module, channel["n"])) is not None:
                documented.setdefault(a, []).append((module, channel["n"]))
    heard = {int(a): x for a, x in seen.get("answers", {}).items()}
    unknown = sorted(a for a in heard if a not in documented)
    if unknown:
        items.append(
            _item(
                "warning",
                "heard_undocumented",
                [{"type": "heard", "id": str(a)} for a in unknown],
                count=len(unknown),
                addresses=_runs(unknown),
                assumed=True,
            )
        )
    # one round of the FAM14 takes up to about 10 s: silence says something only after a while
    if seen.get("seconds", 0) >= 30 and (heard or seen.get("base_id")):
        silent = [
            (m, n) for a, users in sorted(documented.items()) if a not in heard for m, n in users
        ]
        if silent:
            items.append(
                _item(
                    "info",
                    "documented_silent",
                    [_channel(m, n) for m, n in silent],
                    count=len(silent),
                    assumed=True,
                )
            )
    if not bus.get("base_id") and seen.get("candidates"):
        base, count = seen["candidates"][0]
        items.append(
            _item(
                "info",
                "base_id_candidate",
                [{"type": "bus", "id": bus["id"]}],
                base_id=base,
                count=count,
                assumed=True,
            )
        )
    return items


def _bus_checks(
    data: dict[str, Any],
    bus: dict[str, Any],
    devices: dict[tuple[str, str], dict[str, Any]],
    loaded: set[str],
    unassigned: list[dict[str, str]],
) -> dict[str, Any]:
    modules = [m for m in data["modules"] if m["bus"] == bus["id"]]
    items: list[dict[str, Any]] = []
    by_address: dict[int, list[tuple[dict[str, Any], int]]] = {}
    by_feedback: dict[str, list[tuple[dict[str, Any], int]]] = {}
    for module in modules:
        for channel in module["channels"]:
            if channel["unused"]:
                continue
            if (address := channel_address(module, channel["n"])) is not None:
                by_address.setdefault(address, []).append((module, channel["n"]))
            if channel["feedback_id"]:
                by_feedback.setdefault(channel["feedback_id"].upper(), []).append(
                    (module, channel["n"])
                )
    for address, users in sorted(by_address.items()):
        if len(users) > 1:
            items.append(
                _item("error", "address_twice", [_channel(m, n) for m, n in users], address=address)
            )
    for feedback, users in sorted(by_feedback.items()):
        if len(users) > 1:
            items.append(
                _item(
                    "error",
                    "feedback_twice",
                    [_channel(m, n) for m, n in users],
                    feedback_id=feedback,
                )
            )
    masters = [m for m in modules if role(m) == "master" and not m["placeholder"]]
    master = next((m for m in modules if m["id"] == bus.get("master")), None)
    if master is None:
        items.append(_item("error", "no_master", [{"type": "bus", "id": bus["id"]}]))
    elif master["placeholder"]:
        items.append(_item("info", "master_placeholder", [_module(master)]))
    if len(masters) > 1:
        items.append(_item("error", "two_masters", [_module(m) for m in masters]))
    for module in modules:
        if module["first_address"] is not None:
            last = module["first_address"] + address_count(module) - 1
            if last > ADDRESSES:
                items.append(_item("error", "address_range", [_module(module)], last=last))
    loads = supply_loads(data, bus)
    by_id = {m["id"]: m for m in modules}
    for supply in loads["supplies"]:
        target = [_module(by_id[supply["module"]])] if supply["module"] in by_id else []
        args = {"load": supply["load"], "capacity": supply["capacity"]}
        if supply["state"] == "over":
            items.append(_item("error", "supply_over", target, **args))
        elif supply["state"] == "none":
            members = [_module(by_id[i]) for i in supply["members"] if i in by_id]
            items.append(_item("error", "section_without_supply", members, load=supply["load"]))
        elif supply["state"] == "reserve":
            items.append(_item("warning", "supply_reserve", target, **args))
    if loads["unfed"] and loads["mode"] == "range":
        items.append(
            _item(
                "warning",
                "unfed",
                [_module(by_id[i]) for i in loads["unfed"]],
                count=len(loads["unfed"]),
            )
        )
    consumers = [m for m in modules if role(m) not in NOT_CONSUMERS]
    without_address = [_module(m) for m in consumers if m["first_address"] is None]
    if without_address:
        items.append(_item("warning", "no_address", without_address, count=len(without_address)))
    without_place = [_module(m) for m in modules if m.get("row") is None and not m["placeholder"]]
    if without_place:
        items.append(_item("warning", "no_place", without_place, count=len(without_place)))
    access = {a["entry_id"] for a in bus["access"]}
    mine = [u for u in unassigned if u["entry_id"] in access]
    if mine:
        items.append(
            _item(
                "warning",
                "unassigned",
                [{"type": "device", "id": f"{u['entry_id']}|{u['device_key']}"} for u in mine],
                count=len(mine),
            )
        )
    missing = []
    documented = []
    for module in modules:
        for channel in module["channels"]:
            if channel["unused"]:
                continue
            if channel["device_key"]:
                key = (channel["entry_id"], channel["device_key"])
                if channel["entry_id"] in loaded and key not in devices:
                    missing.append(_channel(module, channel["n"]))
            elif not channel["manual_id"]:
                documented.append(_channel(module, channel["n"]))
    if missing:
        items.append(_item("warning", "ha_missing", missing, count=len(missing)))
    items += _rail_checks(data, modules, loads)
    used = sorted(by_address)
    if used:
        gaps = sorted(set(range(1, used[-1] + 1)) - set(used))
        if gaps:
            items.append(
                _item(
                    "info",
                    "gaps",
                    [{"type": "view", "id": "addresses"}],
                    ranges=_runs(gaps),
                    highest=used[-1],
                )
            )
    if documented:
        items.append(_item("info", "documented_only", documented, count=len(documented)))
    without = [m for m in consumers if m["first_address"] is not None and power_of(m)[0] is None]
    if without:
        items.append(_item("info", "no_power", [_module(m) for m in without], count=len(without)))
    return {
        "items": items,
        "supplies": loads,
        "used": len(used),
        "duplicates": [a for a, u in sorted(by_address.items()) if len(u) > 1],
    }


def _rail_checks(
    data: dict[str, Any], modules: list[dict[str, Any]], loads: dict[str, Any]
) -> list[dict[str, Any]]:
    """What the rail says: air around a loaded power supply, the FUD14's spacer, the terminating
    resistor at the end of the bus, and how a row hands the bus on to the next."""
    items: list[dict[str, Any]] = []
    order = [m for m in bus_order(data, modules) if role(m) not in ("foreign", "accessory")]
    if not order:
        return items
    rows = rows_by_id(data)
    placed = bus_order(data, modules)
    no_air: list[dict[str, str]] = []
    # the load of each power supply: its section's (by place) or its address range's
    load_of = {}
    for supply in loads["supplies"]:
        for module_id in [*supply.get("modules", []), supply["module"]]:
            if module_id:
                load_of[module_id] = supply["load"]

    def air(left: dict[str, Any], right: dict[str, Any]) -> float:
        """Free TE between two neighbours in a row (a spacer of the right one counts)."""
        return float(right["slot"]) - _span(left)[1]

    for i, module in enumerate(placed):
        if role(module) != "supply" or (load := load_of.get(module["id"])) is None:
            continue
        left = placed[i - 1] if i and placed[i - 1]["row"] == module["row"] else None
        right = (
            placed[i + 1] if i + 1 < len(placed) and placed[i + 1]["row"] == module["row"] else None
        )
        if load > AIR_LEFT_WATTS and left is not None and air(left, module) < 0.5:
            items.append(
                _item(
                    "warning",
                    "supply_air_left",
                    [_module(module), _module(left)],
                    load=load,
                    watts=AIR_LEFT_WATTS,
                )
            )
        if load > AIR_FAM14_WATTS:
            for a, b in ((left, module), (module, right)):
                if a is None or b is None:
                    continue
                fam = a if a is not module else b
                if role(fam) == "master" and air(a, b) < 0.5:
                    items.append(
                        _item(
                            "warning",
                            "supply_air_fam14",
                            [_module(module), _module(fam)],
                            load=load,
                            watts=AIR_FAM14_WATTS,
                        )
                    )
    for module in placed:
        if not str(module.get("type", "")).upper().startswith("FUD14"):
            continue
        before = [m for m in placed if m["row"] == module["row"] and m["slot"] < module["slot"]]
        gap = _span(module)[0] - max((_span(m)[1] for m in before), default=1.0)
        if not module["spacer_before"] and gap < 0.5 and before:
            no_air.append(_module(module))
    if no_air:
        items.append(_item("info", "fud14_spacer", no_air, count=len(no_air)))
    terminators = [m for m in modules if m["terminator"]]
    if not terminators:
        items.append(_item("warning", "terminator_missing", [_module(order[-1])]))
    elif len(terminators) > 1:
        items.append(_item("warning", "terminator_twice", [_module(m) for m in terminators]))
    elif terminators[0]["id"] != order[-1]["id"]:
        items.append(
            _item("warning", "terminator_not_last", [_module(terminators[0]), _module(order[-1])])
        )
    used_rows: list[str] = []
    for module in order:
        if module["row"] not in used_rows:
            used_rows.append(module["row"])
    for row_id in used_rows[:-1]:
        cabinet, row = rows[row_id]
        if not (row.get("next") or {}).get("kind"):
            items.append(
                _item(
                    "warning",
                    "row_link_missing",
                    [{"type": "row", "id": row_id}],
                    cabinet=cabinet["name"],
                    row=row["name"],
                )
            )
    return items
