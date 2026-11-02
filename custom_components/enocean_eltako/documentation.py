"""Installation documentation: what the integration knows of the installation, per gateway.

One versioned structure for the panel's print view, CSV and JSON. It holds what Home Assistant
knows (devices, the sender IDs it assigned, the sender ID pool, wall switches), not what an
actuator has really learned.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .bus_devices import ADDRESSES, SOURCE, SUPPLY_WATTS, bus_power
from .catalog import OPT_WALL_OFF, OPT_WALL_ON, OPT_WALL_SWITCH
from .const import CONF_BASE_ID, CONF_MODEL, DOMAIN
from .device import EnOceanDevice
from .discovery import pending
from .heard import heard_by
from .notes import Notes, device_key
from .protocol.ids import format_id, parse_id
from .protocol.models import MODELS

VERSION = 2  # 2: typed device fields, links, the event log; the import still takes 1
IMPORTABLE_VERSIONS = (1, VERSION)


def _signal(device: EnOceanDevice) -> dict[str, Any] | None:
    """When a device was last heard and how well; a virtual device has no telegrams (None)."""
    if device.virtual is not None:
        return None
    heard = heard_by(device)
    rssi = [row["rssi"] for row in heard["gateways"] if row["rssi"] is not None]
    return {
        "last": device.stats.last_seen,
        "rssi": max(rssi, default=None),
        "repeater_only": heard["repeater_only"],
    }


def _device(hass: HomeAssistant, device: EnOceanDevice, notes: Notes) -> dict[str, Any]:
    entry = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, device.unique_prefix), device.entry.entry_id
    )
    area = ar.async_get(hass).async_get_area(entry.area_id) if entry and entry.area_id else None
    options = device.options
    wall = None
    if wall_switch := options.get(OPT_WALL_SWITCH):
        wall = {
            "id": wall_switch,
            "on": options.get(OPT_WALL_ON),
            "off": options.get(OPT_WALL_OFF),
        }
    model = device.model
    test = notes.tests.get(device_key(device.subentry), {})
    return {
        "name": device.subentry.title,
        "key": device.subentry.subentry_id,
        "note_key": device_key(device.subentry),
        "model": device._model_label,
        "kind": model.id,
        "category": model.category,
        "virtual": device.virtual is not None,
        "id": format_id(device.device_id),
        "eep": str(model.receive) if model.receive else None,
        "eep_extra": [str(ref) for ref in model.receive_extra],
        # a device sending from several IDs (FUTH): each with its own profile
        "ids": [
            {"id": format_id(radio_id), "eep": str(link.eep)}
            for radio_id, link in device.linked.items()
        ],
        "area": area.name if area else None,
        "labels": sorted(entry.labels) if entry else [],
        "entities": len(er.async_entries_for_device(er.async_get(hass), entry.id)) if entry else 0,
        "senders": [
            {
                "profile": profile,
                "id": format_id(sender),
                "ute": not model.sender_profile(profile).teach_in,
                "test": test.get("results", {}).get(profile),
            }
            for profile, sender in device.senders.items()
        ],
        "signal": _signal(device),
        "wall_switch": wall,
        "bus_power_table": bus_power(device._model_label),
        **notes.device(device_key(device.subentry)),
        "test_time": test.get("time"),
    }


def _heard(entry: Any, notes: Notes) -> list[dict[str, Any]]:
    """Unknown senders heard (also before the last restart) that are not set up or hidden."""
    rows: dict[str, dict[str, Any]] = {}
    for t in pending(entry):
        rows[format_id(t.sender)] = {
            "id": format_id(t.sender),
            "rorg": f"{t.telegram.rorg:02X}",
            "dbm": t.telegram.dbm,
            "last": t.timestamp,
        }
    hub = entry.runtime_data.hub
    configured = {s.unique_id.split("_")[0] for s in entry.subentries.values() if s.unique_id}
    hidden = {format_id(s) for s in hub.hidden.get(entry.entry_id, ())}
    for sender, values in notes.heard.items():
        if sender in rows or sender in configured or sender in hidden:
            continue
        if hub.senders.in_pool(parse_id(sender)):
            continue
        rows[sender] = {
            "id": sender,
            "rorg": values["rorg"],
            "dbm": values["dbm"],
            "last": values["last"],
        }
    newest = sorted(rows.values(), key=lambda r: r["last"], reverse=True)
    return [
        {**r, "last": dt_util.utc_from_timestamp(r["last"]).isoformat(timespec="seconds")}
        for r in newest
    ]


def _status(test: str | None) -> str:
    """What a sender test says of a link: answered, no answer, or never tested."""
    if test == "confirmed":
        return "confirmed"
    return "no_answer" if test in ("unconfirmed", "failed") else "unverified"


def build_links(devices: list[dict[str, Any]], notes: Notes) -> list[dict[str, Any]]:
    """Who is taught into which actuator, each link with where it comes from.

    assigned: a sender Home Assistant holds for the actuator (with the last teach-in sent and the
    last sender test as evidence); declared: the wall switch set in the device's options;
    entered: written down by the user. What an actuator has really learned is not readable.
    """
    by_key = {d["note_key"]: d for d in devices}  # the address: it survives adding a device again
    links: list[dict[str, Any]] = []
    for d in devices:
        key = d["note_key"]
        info = notes.link_info
        for s in d["senders"]:
            link_key = f"assigned|{key}|{s['profile']}"
            links.append(
                {
                    "key": link_key,
                    "source": "assigned",
                    "from_kind": "ha",
                    "from_id": s["id"],
                    "from_name": "",
                    "to_key": key,
                    "to_id": d["id"],
                    "to_name": d["name"],
                    "role": s["profile"],
                    "learn": info.get(link_key, {}).get("learn", ""),
                    "status": _status(s["test"]),
                    "teach_in": notes.last_teach_in(key, s["profile"]),
                    "tested": d["test_time"] if s["test"] else None,
                }
            )
        if wall := d["wall_switch"]:
            link_key = f"declared|{key}|{wall['id']}"
            links.append(
                {
                    "key": link_key,
                    "source": "declared",
                    "from_kind": "wall",
                    "from_id": wall["id"],
                    "from_name": "",
                    "to_key": key,
                    "to_id": d["id"],
                    "to_name": d["name"],
                    "role": f"{wall.get('on') or '?'} / {wall.get('off') or '?'}",
                    "learn": info.get(link_key, {}).get("learn", ""),
                    "status": "declared",
                    "teach_in": None,
                    "tested": None,
                }
            )
    for e in notes.links:
        target = by_key.get(e["to_key"])
        links.append(
            {
                "key": f"entered|{e['id']}",
                "id": e["id"],
                "source": "entered",
                "from_kind": "entered",
                "from_id": e["from_id"],
                "from_name": e["from_name"],
                "to_key": e["to_key"],
                "to_id": target["id"] if target else "",
                "to_name": target["name"] if target else e["to_name"],
                "role": e["role"],
                "learn": e["learn"],
                "status": "entered",
                "teach_in": None,
                "tested": None,
            }
        )
    return links


def collect(hass: HomeAssistant) -> dict[str, Any]:
    """Every loaded gateway with its devices, sender ID pools and hidden senders."""
    from .websocket import _pool_rows, _pools  # noqa: PLC0415 - websocket imports this module

    pools = _pools(hass)
    gateways = []
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        runtime = entry.runtime_data
        notes = runtime.hub.notes[entry.entry_id]
        devices = sorted(
            (_device(hass, d, notes) for d in runtime.devices.values()),
            key=lambda d: (d["virtual"], str(d["name"]).casefold()),
        )
        gateways.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "model": entry.data.get(CONF_MODEL),
                "model_name": model.name
                if (model := MODELS.get(entry.data.get(CONF_MODEL, "")))
                else None,
                "base_id": entry.data.get(CONF_BASE_ID),
                "note": notes.gateway,
                "supplies": notes.supplies,
                "manual": [{**m, "bus_power_table": bus_power(m["name"])} for m in notes.manual],
                "devices": devices,
                "links": build_links(devices, notes),
                "pools": [
                    {
                        "id": pool_id,
                        "kind": kind,
                        "start": format_id(store.pool.start),
                        "end": format_id(store.pool.start + store.pool.size - 1),
                        "senders": [
                            {k: row[k] for k in ("id", "device", "ref", "profile", "state")}
                            for row in _pool_rows(hass, store)
                        ],
                    }
                    for pool_id, (kind, owner, store) in pools.items()
                    if owner.entry_id == entry.entry_id
                ],
                "heard": _heard(entry, notes),
                "log": notes.log,
                "hidden_senders": sorted(
                    format_id(s) for s in runtime.hub.hidden.get(entry.entry_id, ())
                ),
            }
        )
    return {
        "bus_info": {"addresses": ADDRESSES, "supply_watts": SUPPLY_WATTS, "source": SOURCE},
        "version": VERSION,
        "generated": dt_util.utcnow().isoformat(timespec="seconds"),
        "gateways": gateways,
    }
