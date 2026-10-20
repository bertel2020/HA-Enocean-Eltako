"""Takeover from the old eltako integration: its YAML devices become device subentries.

The old integration keeps its devices in configuration.yaml under "eltako:", per gateway
(matched to ours by the base ID) and platform. Each device keeps its ID, name and sender
ID, so actuators go on reacting to the sender IDs they learned. A rocker sender ID may
carry " left" or " right": the rocker the old integration pressed (left when missing).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config import async_hass_config_yaml
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .catalog import (
    CATALOG,
    CENTRAL,
    CONTROLLER,
    COOLING_SWITCH,
    DIRECTION_ROCKER,
    GENERIC_EEP,
    GENERIC_EEPS,
    HEATING_CONTROLLER,
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
    SUBENTRY_SCHEMA,
)
from .protocol.ids import format_id, parse_id

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


def _sensor(device: TakeoverDevice, eep: str, conf: Mapping[str, Any]) -> None:
    if (model_id := SENSOR_MODELS.get(eep)) is not None:
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
                _sensor(device, eep, conf)
            elif platform in (Platform.LIGHT, Platform.SWITCH, Platform.COVER, Platform.CLIMATE):
                _actuator(device, str(platform), eep, conf)
            else:  # buttons: Home Assistant as a rocker, set up as a virtual rocker instead
                device.reason = "takeover_unsupported"
    return devices


def subentry_data(device: TakeoverDevice, senders: Mapping[str, int]) -> dict[str, Any]:
    """Subentry data as the device flow saves it (schema, model, ID, senders, options)."""
    assert device.model is not None
    data: dict[str, Any] = {
        "schema": SUBENTRY_SCHEMA,
        CONF_MODEL: device.model,
        CONF_DEVICE_ID: format_id(device.device_id),
        **device.data,
    }
    if senders:
        data[CONF_SENDERS] = [
            {CONF_PROFILE: p, CONF_SENDER_ID: format_id(s)} for p, s in senders.items()
        ]
    return data
