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

from .catalog import OPT_WALL_OFF, OPT_WALL_ON, OPT_WALL_SWITCH
from .const import CONF_BASE_ID, CONF_MODEL, DOMAIN
from .device import EnOceanDevice
from .discovery import pending
from .notes import Notes, device_key
from .protocol.ids import format_id
from .protocol.models import MODELS

VERSION = 1


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
        "model": device._model_label,
        "kind": model.id,
        "category": model.category,
        "virtual": device.virtual is not None,
        "id": format_id(device.device_id),
        "eep": str(model.receive) if model.receive else None,
        "eep_extra": [str(ref) for ref in model.receive_extra],
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
        "wall_switch": wall,
        "note": notes.devices.get(device_key(device.subentry), ""),
        "test_time": test.get("time"),
    }


def collect(hass: HomeAssistant) -> dict[str, Any]:
    """Every loaded gateway with its devices, sender ID pools and hidden senders."""
    from .websocket import _pool_rows, _pools  # noqa: PLC0415 - websocket imports this module

    pools = _pools(hass)
    gateways = []
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        runtime = entry.runtime_data
        notes = runtime.hub.notes[entry.entry_id]
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
                "manual": notes.manual,
                "devices": sorted(
                    (_device(hass, d, notes) for d in runtime.devices.values()),
                    key=lambda d: (d["virtual"], str(d["name"]).casefold()),
                ),
                "pools": [
                    {
                        "id": pool_id,
                        "kind": kind,
                        "start": format_id(store.pool.start),
                        "end": format_id(store.pool.start + store.pool.size - 1),
                        "senders": [
                            {k: row[k] for k in ("id", "device", "profile", "state")}
                            for row in _pool_rows(hass, store)
                        ],
                    }
                    for pool_id, (kind, owner, store) in pools.items()
                    if owner.entry_id == entry.entry_id
                ],
                # unknown senders heard since the restart that are not set up (and not hidden)
                "heard": [
                    {
                        "id": format_id(t.sender),
                        "rorg": f"{t.telegram.rorg:02X}",
                        "dbm": t.telegram.dbm,
                        "last": dt_util.utc_from_timestamp(t.timestamp).isoformat(
                            timespec="seconds"
                        ),
                    }
                    for t in pending(entry)
                ],
                "hidden_senders": sorted(
                    format_id(s) for s in runtime.hub.hidden.get(entry.entry_id, ())
                ),
            }
        )
    return {
        "version": VERSION,
        "generated": dt_util.utcnow().isoformat(timespec="seconds"),
        "gateways": gateways,
    }
