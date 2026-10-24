"""Takeover from the old eltako integration: its YAML devices become device subentries.

The old integration keeps its devices in configuration.yaml under "eltako:", per gateway
(matched to ours by the base ID) and platform. Each device keeps its ID, name and sender
ID, so actuators go on reacting to the sender IDs they learned. A rocker sender ID may
carry " left" or " right": the rocker the old integration pressed (left when missing).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from homeassistant.config import async_hass_config_yaml
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.translation import async_get_translations

from .catalog import (
    CATALOG,
    CENTRAL,
    CONTROLLER,
    COOLING_SWITCH,
    DIRECTION_ROCKER,
    GENERIC_EEP,
    GENERIC_EEPS,
    GROUP_VIRTUAL,
    HEATING_CONTROLLER,
    OPT_BUTTONS,
    OPT_DEVICE_CLASS,
    OPT_INVERT,
    OPT_PLATFORM,
    OPT_ROCKER_OFF,
    OPT_ROCKER_ON,
    OPT_TILT_TIME,
    OPT_TIME_CLOSES,
    OPT_TIME_OPENS,
    ROCKER,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_EEP,
    CONF_MODEL,
    CONF_PROFILE,
    CONF_SENDER_ID,
    CONF_SENDERS,
    DOMAIN,
    SUBENTRY_DEVICE,
    SUBENTRY_SCHEMA,
)
from .entity_ids import gateway_prefix, object_id
from .protocol.ids import format_id, parse_id
from .protocol.sender_pool import SenderIdError
from .subentry_flow import sender_owner

if TYPE_CHECKING:
    from . import EnOceanEltakoConfigEntry

_LOGGER = logging.getLogger(__name__)

OLD_DOMAIN = "eltako"

# receive-only devices of the old binary_sensor and sensor platforms, by their EEP
SENSOR_MODELS = {
    "A5-04-02": "temp_humidity",
    "A5-08-01": "fbh",
    "A5-09-04": "co2",
    "A5-09-0C": "tvoc",
    "A5-10-06": "room_controller",
    "A5-12-01": "meter",
    "A5-12-02": "gas_meter",
    "A5-12-03": "water_meter",
    "A5-13-01": "weather",
    "A5-30-01": "digital_input",
    "A5-30-03": "digital_inputs",
    "D2-14-40": "multisensor",
    "D2-14-41": "multisensor_contact",
    "D5-00-01": "contact",
    "F6-02-01": "rocker",
    "F6-02-02": "rocker",
    "F6-10-00": "window_handle",
}
ROCKER_EEPS = ("F6-02-01", "F6-02-02")


@dataclass(slots=True)
class TakeoverDevice:
    """One device of the old configuration and the subentry it becomes."""

    device_id: int
    name: str
    old: str  # "platform EEP" as in the old configuration
    model: str | None = None  # catalog model, GENERIC_EEP, or None when it cannot be taken over
    data: dict[str, Any] = field(default_factory=dict)  # options of the subentry
    senders: dict[str, int] = field(default_factory=dict)  # profile -> sender ID
    reason: str | None = None  # why not (translation key)
    new_id: int | None = (
        None  # a virtual device's ID is its sender, which may differ from the old ID
    )

    @property
    def target_id(self) -> int:
        return self.device_id if self.new_id is None else self.new_id


def new_ids(devices: list[TakeoverDevice] | None) -> dict[int, int]:
    """Old device ID -> its ID here: a virtual rocker's ID is its sender, not the old ID."""
    return {d.device_id: d.target_id for d in devices or []}


async def async_old_config(hass: HomeAssistant) -> Mapping[str, Any] | None:
    """The "eltako:" section of configuration.yaml (includes resolved), None when absent."""
    try:
        config = await async_hass_config_yaml(hass)
    except (HomeAssistantError, OSError):
        return None
    section = config.get(OLD_DOMAIN)
    return section if isinstance(section, Mapping) else None


def old_gateways(config: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    gateways = config.get("gateway") or []
    if isinstance(gateways, Mapping):
        gateways = [gateways]
    return [g for g in gateways if isinstance(g, Mapping)]


def find_gateway(config: Mapping[str, Any], base_id: int) -> Mapping[str, Any] | None:
    for gateway in old_gateways(config):
        try:
            if parse_id(str(gateway.get("base_id", ""))) == base_id:
                return gateway
        except ValueError:
            continue
    return None


def _parse_sender(text: Any) -> tuple[int, str]:
    """ "FF-B7-44-B9 left" -> (ID, "left"); raises ValueError."""
    parts = str(text).split()
    if not parts or len(parts) > 2:
        raise ValueError(text)
    side = parts[1].lower() if len(parts) == 2 else "left"
    if side not in ("left", "right"):
        raise ValueError(text)
    return parse_id(parts[0]), side


def _rocker_buttons(side: str) -> dict[str, str]:
    rocker = "a" if side == "left" else "b"
    return {OPT_ROCKER_ON: f"{rocker}0", OPT_ROCKER_OFF: f"{rocker}1"}


def _sensor(device: TakeoverDevice, platform: str, eep: str, conf: Mapping[str, Any]) -> None:
    if platform == Platform.BINARY_SENSOR and eep in ROCKER_EEPS:
        model_id: str | None = "rocker_contact"  # a contact kept as state, not a button's events
    else:
        model_id = SENSOR_MODELS.get(eep)
    if model_id is not None:
        device.model = model_id
        options = CATALOG[model_id].options
        if OPT_DEVICE_CLASS in options and conf.get("device_class"):
            device.data[OPT_DEVICE_CLASS] = conf["device_class"]
        if OPT_INVERT in options and "invert_signal" in conf:
            device.data[OPT_INVERT] = bool(conf["invert_signal"])
    elif eep in GENERIC_EEPS:
        device.model = GENERIC_EEP
        device.data[CONF_EEP] = f"{eep}:std"
    else:
        device.reason = "takeover_unsupported"


def _actuator(device: TakeoverDevice, platform: str, eep: str, conf: Mapping[str, Any]) -> None:
    sender_conf = conf.get("sender")
    if not isinstance(sender_conf, Mapping):
        device.reason = "takeover_no_sender"
        return
    try:
        sender, side = _parse_sender(sender_conf.get("id"))
    except ValueError:
        device.reason = "takeover_bad_sender"
        return
    sender_eep = str(sender_conf.get("eep", "")).upper()
    if platform in (Platform.LIGHT, Platform.SWITCH):
        if eep in ROCKER_EEPS:  # a switch reporting as a rocker: the old one toggled per press
            device.reason = "takeover_unsupported"
            return
        device.model = "dimmer" if platform == Platform.LIGHT and eep == "A5-38-08" else "switch"
        if device.model == "switch":
            device.data[OPT_PLATFORM] = platform
            # the old switch platform reversed commands and state with invert_signal
            if platform == Platform.SWITCH and conf.get("invert_signal"):
                device.data[OPT_INVERT] = True
        if sender_eep == "A5-38-08":
            device.senders[CENTRAL.id] = sender
        elif sender_eep in ROCKER_EEPS:
            device.senders[ROCKER.id] = sender
            device.data.update(_rocker_buttons(side))
    elif platform == Platform.COVER:
        device.model = "cover"
        if sender_eep == "H5-3F-7F":
            device.senders[CONTROLLER.id] = sender
        elif sender_eep in ROCKER_EEPS:
            device.senders[DIRECTION_ROCKER.id] = sender
            device.data.update(_rocker_buttons(side))
        for old, new in (("time_opens", OPT_TIME_OPENS), ("time_closes", OPT_TIME_CLOSES)):
            if conf.get(old):
                device.data[new] = float(conf[old])
        if conf.get("time_tilts"):  # tenths of a second in the old integration
            device.data[OPT_TILT_TIME] = round(float(conf["time_tilts"]) / 10, 1)
    elif platform == Platform.CLIMATE:
        device.model = "heating_actuator"
        if sender_eep == "A5-10-06":
            device.senders[HEATING_CONTROLLER.id] = sender
        cooling = conf.get("cooling_mode")
        if isinstance(cooling, Mapping) and isinstance(cooling.get("sender"), Mapping):
            try:
                device.senders[COOLING_SWITCH.id] = _parse_sender(cooling["sender"].get("id"))[0]
            except ValueError:
                pass
    if not device.senders:
        device.model = None
        device.reason = "takeover_bad_sender"


def _button(device: TakeoverDevice, conf: Mapping[str, Any]) -> None:
    """The old button platform: Home Assistant pressed the top button of the sender's rocker."""
    if not isinstance(sender_conf := conf.get("sender"), Mapping):
        device.reason = "takeover_no_sender"
        return
    try:
        sender, side = _parse_sender(sender_conf.get("id"))
    except ValueError:
        device.reason = "takeover_bad_sender"
        return
    device.model = "virtual_rocker"
    device.new_id = sender  # a virtual device's ID is its sender
    device.senders[ROCKER.id] = sender
    device.data[OPT_BUTTONS] = [_rocker_buttons(side)[OPT_ROCKER_ON]]  # left 0x30, right 0x70


def plan(gateway: Mapping[str, Any]) -> list[TakeoverDevice]:
    """The devices of one old gateway and what each becomes; first entry of an ID wins."""
    devices: list[TakeoverDevice] = []
    seen: set[int] = set()
    platforms = gateway.get("devices") or {}
    if not isinstance(platforms, Mapping):
        return devices
    for platform, entries in platforms.items():
        for conf in entries if isinstance(entries, list) else [entries]:
            if not isinstance(conf, Mapping):
                continue
            try:
                device_id = parse_id(str(conf.get("id", "")).split()[0])
            except (ValueError, IndexError):
                continue
            eep = str(conf.get("eep", "")).upper()
            device = TakeoverDevice(
                device_id, str(conf.get("name") or format_id(device_id)), f"{platform} {eep}"
            )
            devices.append(device)
            if device_id in seen:
                device.reason = "takeover_duplicate"
                continue
            seen.add(device_id)
            if platform in (Platform.BINARY_SENSOR, Platform.SENSOR):
                _sensor(device, str(platform), eep, conf)
            elif platform in (Platform.LIGHT, Platform.SWITCH, Platform.COVER, Platform.CLIMATE):
                _actuator(device, str(platform), eep, conf)
            elif platform == Platform.BUTTON:
                _button(device, conf)
            else:
                device.reason = "takeover_unsupported"
    targets: set[int] = set()
    for device in devices:  # two buttons on one sender, or a button on another device's ID
        if device.model is None:
            continue
        if device.target_id in targets:
            device.model, device.reason = None, "takeover_duplicate"
        targets.add(device.target_id)
    return devices


def subentry_data(device: TakeoverDevice, senders: Mapping[str, int]) -> dict[str, Any]:
    """Subentry data as the device flow saves it (schema, model, ID, senders, options)."""
    assert device.model is not None
    data: dict[str, Any] = {
        "schema": SUBENTRY_SCHEMA,
        CONF_MODEL: device.model,
        CONF_DEVICE_ID: format_id(device.target_id),
        **device.data,
    }
    if senders:
        data[CONF_SENDERS] = [
            {CONF_PROFILE: p, CONF_SENDER_ID: format_id(s)} for p, s in senders.items()
        ]
    return data


# ---- the old integration's registry entries -------------------------------------------------

# "eltako_gw1_ff_c2_4a_a2" (the device) or "eltako_gw1_ff_c2_4a_a2_id" (a further entity of it)
_OLD_UNIQUE_ID = re.compile(r"^eltako_gw\d+_((?:[0-9a-f]{2}_){3}[0-9a-f]{2})(?:_(.+))?$")
ASSISTANTS = ("conversation", "cloud.alexa", "cloud.google_assistant")


def old_entities(hass: HomeAssistant) -> dict[int, list[er.RegistryEntry]]:
    """The old integration's entity registry entries by the device ID in their unique ID."""
    found: dict[int, list[er.RegistryEntry]] = {}
    for entry in er.async_get(hass).entities.values():
        if entry.platform != OLD_DOMAIN or not entry.unique_id:
            continue
        if (match := _OLD_UNIQUE_ID.match(entry.unique_id)) is None:
            continue  # the gateway's own entities
        device_id = parse_id(match.group(1).replace("_", "-"))
        found.setdefault(device_id, []).append(entry)
    return found


def old_suffix(entry: er.RegistryEntry) -> str | None:
    match = _OLD_UNIQUE_ID.match(entry.unique_id)
    return match.group(2) if match else None


def old_active(hass: HomeAssistant) -> bool:
    """The old integration is set up, so its entity IDs are still taken."""
    return any(
        e.state is ConfigEntryState.LOADED for e in hass.config_entries.async_entries(OLD_DOMAIN)
    )


def primary_entity(entries: list[er.RegistryEntry]) -> er.RegistryEntry | None:
    """The entity that is the device itself (light, switch ...): it has no name of its own."""
    return next((e for e in entries if e.original_name is None), None)


# platforms whose main entity has no name of its own: its ID is the device name alone
MAIN_PLATFORMS = (Platform.LIGHT, Platform.SWITCH, Platform.COVER, Platform.CLIMATE)


async def async_predicted_ids(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    devices: list[TakeoverDevice],
    old: dict[int, list[er.RegistryEntry]],
) -> dict[str, str]:
    """Old entity ID -> the one its new counterpart will probably get.

    Home Assistant gives the ID only when the entity is added; until then it is predicted
    for the main entity and the ID sensor. A taken ID gets "_2" (and so on), as it would.
    """
    texts = await async_get_translations(hass, hass.config.language, "entity", [DOMAIN])
    id_name = texts.get(f"component.{DOMAIN}.entity.sensor.enocean_id.name", "EnOcean ID")
    prefix = gateway_prefix(entry.options)
    registry = er.async_get(hass)
    reserved: set[str] = set()

    def free(domain: str, name: str | None, device_name: str) -> str:
        base = f"{domain}.{object_id(prefix, device_name, name)}"
        candidate, n = base, 2
        while (
            candidate in reserved
            or registry.async_is_registered(candidate)
            or hass.states.get(candidate) is not None
        ):
            candidate, n = f"{base}_{n}", n + 1
        reserved.add(candidate)
        return candidate

    found: dict[str, str] = {}
    for device in devices:
        if device.model is None:
            continue
        entries = old.get(device.device_id, [])
        model = CATALOG.get(device.model)
        platform = device.data.get(OPT_PLATFORM) or (model.platforms[0] if model else None)
        if (main := primary_entity(entries)) is not None and platform in MAIN_PLATFORMS:
            found[main.entity_id] = free(str(platform), None, device.name)
        if model is not None and model.group == GROUP_VIRTUAL:
            continue  # sends only: no ID sensor
        for entity in entries:
            if old_suffix(entity) == "id":
                found[entity.entity_id] = free(Platform.SENSOR, id_name, device.name)
    return found


# What the takeover can carry over, each chosen on its own in the panel
CARRY_OPTIONS = ("area", "labels", "voice", "names", "icons", "visibility")


@dataclass(slots=True)
class Carried:
    """What the user had set on the old device and its entities."""

    area_id: str | None = None
    labels: set[str] = field(default_factory=set)
    name: str | None = None  # the device's name given in Home Assistant
    entities: list[er.RegistryEntry] = field(default_factory=list)
    main: er.RegistryEntry | None = None

    def available(self) -> set[str]:
        """The options this device has something for."""
        found = set()
        if self.area_id:
            found.add("area")
        if self.labels or any(e.labels for e in self.entities):
            found.add("labels")
        if any(_exposure(e) for e in self.entities):
            found.add("voice")
        if self.name or any(e.name for e in self.entities):
            found.add("names")
        if any(e.icon for e in self.entities):
            found.add("icons")
        if any(_user_hidden(e) for e in self.entities):
            found.add("visibility")
        return found


def carried_from(hass: HomeAssistant, entries: list[er.RegistryEntry]) -> Carried:
    carried = Carried(entities=list(entries), main=primary_entity(entries))
    devices = dr.async_get(hass)
    for entry in entries:
        if entry.device_id and (old := devices.async_get(entry.device_id)) is not None:
            carried.area_id = carried.area_id or old.area_id
            carried.labels |= set(old.labels)
            carried.name = carried.name or old.name_by_user
    if carried.main is not None:
        carried.area_id = carried.area_id or carried.main.area_id
    return carried


def area_name(hass: HomeAssistant, area_id: str) -> str:
    area = ar.async_get(hass).async_get_area(area_id)
    return area.name if area is not None else area_id


def label_names(hass: HomeAssistant, label_ids: set[str]) -> list[str]:
    registry = lr.async_get(hass)
    return [label.name if (label := registry.async_get_label(i)) else i for i in label_ids]


def carry_details(hass: HomeAssistant, carried: Carried) -> dict[str, Any]:
    """The values behind the options, as the old device and its entities have them.

    The preview shows them before the takeover, the report keeps them. Entities appear by
    their old entity ID, and only when something is set on them.
    """
    entities = []
    for entry in sorted(carried.entities, key=lambda e: (e is not carried.main, e.entity_id)):
        values: dict[str, Any] = {}
        if entry.labels:
            values["labels"] = sorted(label_names(hass, entry.labels))
        if entry.name:
            values["name"] = entry.name
        if entry.icon:
            values["icon"] = entry.icon
        hidden = []
        if entry.hidden_by is er.RegistryEntryHider.USER:
            hidden.append("hidden")
        if entry.disabled_by is er.RegistryEntryDisabler.USER:
            hidden.append("disabled")
        if hidden:
            values["visibility"] = hidden
        if exposure := _exposure(entry):
            values["voice"] = exposure
        if values:
            entities.append({"old": entry.entity_id, **values})
    return {
        "area": area_name(hass, carried.area_id) if carried.area_id else None,
        "labels": sorted(label_names(hass, carried.labels)),
        "name": carried.name,
        "entities": entities,
    }


def _exposure(entry: er.RegistryEntry) -> dict[str, bool]:
    """assistant -> should expose, as set for this entity."""
    options: Mapping[str, Any] = entry.options  # typed by integration, assistants are no domains
    found = {}
    for assistant in ASSISTANTS:
        should = (options.get(assistant) or {}).get("should_expose")
        if isinstance(should, bool):
            found[assistant] = should
    return found


def _user_hidden(entry: er.RegistryEntry) -> bool:
    return entry.hidden_by is er.RegistryEntryHider.USER or (
        entry.disabled_by is er.RegistryEntryDisabler.USER
    )


def new_entity(
    old: er.RegistryEntry, old_primary: er.RegistryEntry | None, new: list[er.RegistryEntry]
) -> er.RegistryEntry | None:
    """The new entity that replaces an old one: the main one, the ID sensor, or the same kind."""
    if old is old_primary:
        return primary_entity(new)
    if old_suffix(old) == "id":
        return next((e for e in new if e.translation_key == "enocean_id"), None)
    same = [
        e
        for e in new
        if e.domain == old.domain
        and old.original_device_class
        and e.original_device_class == old.original_device_class
    ]
    return same[0] if len(same) == 1 else None


@dataclass(slots=True)
class Change:
    """One registry update that carries something over."""

    kind: str  # "device", "entity" or "expose"
    target: str  # device ID, or entity ID
    values: dict[str, Any]


def carry_changes(
    carried: Carried, device: dr.DeviceEntry, new: list[er.RegistryEntry]
) -> dict[str, list[Change]]:
    """Per option what is still missing on the new device; set values are never overwritten."""
    changes: dict[str, list[Change]] = {option: [] for option in CARRY_OPTIONS}
    if carried.area_id and device.area_id is None:
        changes["area"].append(Change("device", device.id, {"area_id": carried.area_id}))
    if carried.labels - device.labels:
        changes["labels"].append(
            Change("device", device.id, {"labels": set(device.labels) | carried.labels})
        )
    if carried.name and not device.name_by_user:
        changes["names"].append(Change("device", device.id, {"name_by_user": carried.name}))
    for old in carried.entities:
        if (target := new_entity(old, carried.main, new)) is None:
            continue
        if old.labels - target.labels:
            changes["labels"].append(
                Change("entity", target.entity_id, {"labels": set(target.labels) | old.labels})
            )
        if old.name and not target.name:
            changes["names"].append(Change("entity", target.entity_id, {"name": old.name}))
        if old.icon and not target.icon:
            changes["icons"].append(Change("entity", target.entity_id, {"icon": old.icon}))
        if old.hidden_by is er.RegistryEntryHider.USER and target.hidden_by is None:
            changes["visibility"].append(
                Change("entity", target.entity_id, {"hidden_by": er.RegistryEntryHider.USER})
            )
        if old.disabled_by is er.RegistryEntryDisabler.USER and target.disabled_by is None:
            changes["visibility"].append(
                Change("entity", target.entity_id, {"disabled_by": er.RegistryEntryDisabler.USER})
            )
        now = _exposure(target)
        for assistant, should in _exposure(old).items():
            if now.get(assistant) is not should:
                changes["voice"].append(
                    Change("expose", target.entity_id, {"assistant": assistant, "should": should})
                )
    return {option: found for option, found in changes.items() if found}


def registered_device(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, device: Any
) -> dr.DeviceEntry | None:
    """The device registry entry of one of our devices (identifiers are not unique per domain)."""
    wanted = (DOMAIN, device.unique_prefix)
    return next(
        (
            d
            for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
            if wanted in d.identifiers
        ),
        None,
    )


def missing_carried(
    hass: HomeAssistant, entry: EnOceanEltakoConfigEntry, carried: dict[int, Carried]
) -> dict[int, dict[str, list[Change]]]:
    """Per set-up device (by ID) what the old integration had that the new device lacks."""
    entities = er.async_get(hass)
    found = {}
    for device in entry.runtime_data.devices.values():
        if (what := carried.get(device.device_id)) is None or device.channel != 1:
            continue
        if (registered := registered_device(hass, entry, device)) is None:
            continue
        new = er.async_entries_for_device(entities, registered.id, include_disabled_entities=True)
        found[device.device_id] = carry_changes(what, registered, new)
    return found


def apply_carried(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    carried: dict[int, Carried],
    options: set[str],
) -> int:
    """Carry the chosen options over to the new devices; the number of devices changed."""
    from homeassistant.components.homeassistant.exposed_entities import async_expose_entity

    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    done = 0
    for changes in missing_carried(hass, entry, carried).values():
        chosen = [c for option, found in changes.items() if option in options for c in found]
        for change in chosen:
            if change.kind == "device":
                devices.async_update_device(change.target, **change.values)
            elif change.kind == "entity":
                entities.async_update_entity(change.target, **change.values)
            else:
                try:
                    async_expose_entity(
                        hass, change.values["assistant"], change.target, change.values["should"]
                    )
                except Exception:  # an assistant that is not set up: the rest still goes over
                    _LOGGER.debug("Could not expose %s to %s", change.target, change.values)
        done += bool(chosen)
    return done


@dataclass(slots=True)
class TakeoverResult:
    count: int
    skipped: list[str]
    carried: int


async def async_take_over(
    hass: HomeAssistant,
    entry: EnOceanEltakoConfigEntry,
    devices: list[TakeoverDevice],
    *,
    carry: set[str],
) -> TakeoverResult:
    """Subentries with the old sender IDs, one reload, then what is chosen to carry over."""
    if not devices:
        return TakeoverResult(0, [], 0)
    runtime = entry.runtime_data
    pool = runtime.senders.pool
    old = old_entities(hass)
    carried = {d.target_id: carried_from(hass, old.get(d.device_id, [])) for d in devices}
    existing = {s.unique_id for s in entry.subentries.values()}
    runtime.suspend_reload()
    skipped: list[str] = []
    added = 0
    try:
        for device in devices:
            if (unique_id := format_id(device.target_id)) in existing:
                skipped.append(f"{unique_id} ({device.name}): takeover_exists")
                continue
            existing.add(unique_id)
            senders: dict[str, int] = {}
            for profile, sender in device.senders.items():
                try:
                    pool.assign(sender, sender_owner(device.target_id, profile))
                except SenderIdError as err:
                    skipped.append(f"{format_id(sender)} ({device.name}): {err.reason}")
                    continue
                senders[profile] = sender
            hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=MappingProxyType(subentry_data(device, senders)),
                    subentry_type=SUBENTRY_DEVICE,
                    title=device.name,
                    unique_id=unique_id,
                ),
            )
            added += 1
    finally:  # what was added stays: its senders saved, the entry set up again
        await runtime.senders.async_save()
        await hass.config_entries.async_reload(entry.entry_id)
    done = 0
    if carry and entry.state is ConfigEntryState.LOADED:
        try:
            done = apply_carried(hass, entry, carried, carry)
        except Exception:
            _LOGGER.exception("Could not carry area and labels over from the old integration")
    return TakeoverResult(added, skipped, done)
