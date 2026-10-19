"""One-time import of the old `eltako:` YAML configuration (home-assistant-eltako).

Only the plan is built here: which catalog kind, ID, senders and options each old entry
becomes. The import flow shows it and creates the device subentries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.const import Platform

from .catalog import (
    OPT_DEVICE_CLASS,
    OPT_INVERT,
    OPT_PLATFORM,
    OPT_ROUTING,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
)
from .protocol.ids import format_id, parse_id

LEGACY_DOMAIN = "eltako"
# old gateway types -> name shown in the flow
LEGACY_GATEWAYS = {
    "fam14": "Eltako FAM14",
    "fgw14usb": "Eltako FGW14-USB",
    "fam-usb": "Eltako FAM-USB",
    "enocean-usb300": "EnOcean USB300",
    "esp3-gateway": "ESP3",
    "mgw-lan": "MGW LAN",
}
DEVICE_CLASSES = {"door", "window", "garage_door", "opening"}

# (old platform, old EEP) -> catalog kind
KINDS: dict[tuple[str, str], str] = {
    ("light", "M5-38-08"): "switch",
    ("light", "A5-38-08"): "dimmer",
    ("switch", "M5-38-08"): "switch",
    ("switch", "F6-02-01"): "switch",
    ("switch", "F6-02-02"): "switch",
    ("cover", "G5-3F-7F"): "cover",
    ("binary_sensor", "F6-02-01"): "rocker",
    ("binary_sensor", "F6-02-02"): "rocker",
    ("binary_sensor", "D5-00-01"): "contact",
    ("binary_sensor", "F6-10-00"): "window_handle",
    ("binary_sensor", "A5-08-01"): "fbh",
    ("binary_sensor", "A5-13-01"): "weather",
    ("sensor", "A5-04-02"): "temp_humidity",
    ("sensor", "A5-08-01"): "fbh",
    ("sensor", "A5-09-04"): "co2",
    ("sensor", "A5-10-06"): "room_controller",
    ("sensor", "A5-12-01"): "meter",
    ("sensor", "A5-13-01"): "weather",
    ("sensor", "F6-10-00"): "window_handle",
    ("climate", "A5-10-06"): "heating_actuator",
}
# (catalog kind, old sender EEP) -> sender profile
PROFILES: dict[tuple[str, str], str] = {
    ("switch", "A5-38-08"): "central",
    ("switch", "F6-02-01"): "rocker",
    ("switch", "F6-02-02"): "rocker",
    ("dimmer", "A5-38-08"): "central",
    ("dimmer", "F6-02-01"): "rocker",
    ("dimmer", "F6-02-02"): "rocker",
    ("cover", "H5-3F-7F"): "controller",
    ("cover", "F6-02-01"): "direction_rocker",
    ("cover", "F6-02-02"): "direction_rocker",
    ("heating_actuator", "A5-10-06"): "controller",
}


@dataclass
class PlannedDevice:
    name: str
    device_id: int
    kind: str
    senders: dict[str, int] = field(default_factory=dict)  # profile -> sender ID
    options: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)  # "light M5-38-08", for the preview

    @property
    def needs_temperature_sensor(self) -> bool:
        return self.kind == "heating_actuator"


@dataclass
class ImportPlan:
    create: list[PlannedDevice] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)  # names already set up here
    skipped: list[str] = field(default_factory=list)  # "name (platform EEP): reason"


def find_legacy_config(config: dict[str, Any]) -> dict[str, Any] | None:
    """The `eltako:` block, also when it sits in a package."""
    if isinstance(block := config.get(LEGACY_DOMAIN), dict):
        return block
    packages = (config.get("homeassistant") or {}).get("packages") or {}
    for package in packages.values():
        if isinstance(package, dict) and isinstance(block := package.get(LEGACY_DOMAIN), dict):
            return block
    return None


def legacy_gateways(block: dict[str, Any]) -> list[dict[str, Any]]:
    gateways = block.get("gateway") or []
    return [g for g in (gateways if isinstance(gateways, list) else [gateways]) if g]


def gateway_label(gateway: dict[str, Any]) -> str:
    kind = LEGACY_GATEWAYS.get(str(gateway.get("device_type", "")).lower(), "Gateway")
    name = gateway.get("name") or kind
    return f"{name} ({kind}, {gateway.get('base_id', '?')})"


def _id(text: Any) -> int | None:
    """Old IDs may carry " left"/" right" (rocker sides); one device either way."""
    try:
        return parse_id(str(text).split(" ")[0])
    except ValueError:
        return None


def build_plan(gateway: dict[str, Any], existing_ids: set[str]) -> ImportPlan:
    """Map every device of one old gateway to a catalog kind; merge entries of one ID."""
    plan = ImportPlan()
    by_id: dict[int, PlannedDevice] = {}
    devices = gateway.get("devices") or {}
    for platform in ("light", "switch", "cover", "climate", "sensor", "binary_sensor", "button"):
        for entry in devices.get(platform) or []:
            _plan_entry(plan, by_id, platform, entry)
    for device in by_id.values():
        if format_id(device.device_id) in existing_ids:
            plan.existing.append(device.name)
        else:
            plan.create.append(device)
    return plan


def _plan_entry(
    plan: ImportPlan, by_id: dict[int, PlannedDevice], platform: str, entry: dict[str, Any]
) -> None:
    eep = str(entry.get("eep", "")).upper()
    name = str(entry.get("name") or entry.get("id"))
    source = f"{platform} {eep}"
    device_id = _id(entry.get("id"))
    kind = KINDS.get((platform, eep))
    if device_id is None or kind is None:
        plan.skipped.append(f"{name} ({source})")
        return
    planned = by_id.get(device_id)
    if planned is not None and planned.kind != kind:
        plan.skipped.append(f"{name} ({source}): {planned.name} already uses this ID")
        return
    if planned is None:
        planned = by_id[device_id] = PlannedDevice(name, device_id, kind)
    planned.sources.append(source)
    _apply_options(planned, platform, entry)
    if isinstance(sender := entry.get("sender"), dict):
        _add_sender(plan, planned, sender)
    if platform == "climate" and isinstance(thermostat := entry.get("thermostat"), dict):
        # the room controller (FUTH) on the wall becomes a device of its own
        _plan_entry(
            plan,
            by_id,
            "sensor",
            {"id": thermostat.get("id"), "eep": "A5-10-06", "name": f"{name} Thermostat"},
        )


def _apply_options(planned: PlannedDevice, platform: str, entry: dict[str, Any]) -> None:
    options = planned.options
    if planned.kind == "switch":
        options[OPT_PLATFORM] = Platform.LIGHT if platform == "light" else Platform.SWITCH
    if planned.kind == "cover":
        options.setdefault(OPT_TIME_OPENS, entry.get("time_opens") or 30)
        options.setdefault(OPT_TIME_CLOSES, entry.get("time_closes") or 30)
    if planned.kind == "contact":
        device_class = entry.get("device_class")
        options[OPT_DEVICE_CLASS] = device_class if device_class in DEVICE_CLASSES else "window"
        options[OPT_INVERT] = bool(entry.get("invert_signal"))


def _add_sender(plan: ImportPlan, planned: PlannedDevice, sender: dict[str, Any]) -> None:
    eep = str(sender.get("eep", "")).upper()
    profile = PROFILES.get((planned.kind, eep))
    sender_id = _id(sender.get("id"))
    if profile is None or sender_id is None:
        plan.skipped.append(f"{planned.name}: sender {sender.get('id')} ({eep})")
        return
    planned.senders.setdefault(profile, sender_id)
    if (
        planned.kind == "cover"
        and profile == "direction_rocker"
        and "controller" not in (planned.senders)
    ):
        planned.options[OPT_ROUTING] = "direction_rocker"
    elif planned.kind == "cover":
        planned.options[OPT_ROUTING] = "controller"
