"""How the gateways hear a device: the signal data of the device list, details and documentation."""

from __future__ import annotations

from typing import Any

REPEATER_ONLY_MIN = 3  # telegrams heard before 'only via a repeater' is claimed


def heard_by(device: Any) -> dict[str, Any]:
    """Which gateways hear a device, how well, the best one, and whether only repeaters carry it."""
    hass = device.hass
    rows = []
    for entry_id, heard in device.stats.heard.items():
        entry = hass.config_entries.async_get_entry(entry_id)
        rows.append(
            {
                "entry_id": entry_id,
                "name": entry.title if entry else entry_id,
                "count": heard.count,
                "direct": heard.direct,
                "rssi": heard.rssi,
                "last": heard.last,
            }
        )
    rows.sort(key=lambda r: (r["rssi"] is None, -(r["rssi"] or 0), r["name"]))
    with_signal = [r for r in rows if r["rssi"] is not None]
    total = sum(r["count"] for r in rows)
    return {
        "gateways": rows,
        "best": with_signal[0]["entry_id"] if len(rows) > 1 and with_signal else None,
        # radio only: a bus has no repeaters; a few telegrams, none of them direct
        "repeater_only": bool(with_signal)
        and total >= REPEATER_ONLY_MIN
        and not any(r["direct"] for r in rows),
    }
