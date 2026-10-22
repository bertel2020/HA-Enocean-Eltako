"""Device catalog: device kinds with receive/send profiles and platforms.

Every model names its EEP variant explicitly (EEPRef), there is no silent default.
Phase 2 covers the device kinds of the reference system; names are translated
(config_subentries.device.step.user selector "model").
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from homeassistant.const import Platform

from .const import CONF_CUSTOM, CONF_EEP, CONF_MODEL
from .custom_devices import DEFINITIONS, CustomDevice
from .protocol.eep import EEPRef, virtual, vld
from .protocol.eep.eltako import heating, shutter, switching
from .protocol.eep.eltako import virtual as eltako_virtual
from .protocol.eep.model import Field, encode
from .protocol.eep.std.profiles import PROFILES
from .protocol.telegram import Rorg

OPT_PLATFORM = "platform"
OPT_TIME_OPENS = "time_opens"
OPT_TIME_CLOSES = "time_closes"
OPT_VENT_TIME = "vent_time"  # shutters: seconds at the end of the down run closing the slots
OPT_TILT_TIME = "tilt_time"  # blinds: seconds for a full turn of the slats (0 = shutter)
OPT_INVERT = "invert"
OPT_DEVICE_CLASS = "device_class"
OPT_ON_BUTTON = "on_button"  # rocker as contact: button that switches on
OPT_OFF_BUTTON = "off_button"  # button that switches off, or "released"
OPT_TEMPERATURE_SENSOR = "temperature_sensor"  # heating: entity with the room temperature
OPT_SEND_INTERVAL = "send_interval"  # heating: seconds between controller telegrams
OPT_LONG_PRESS = "long_press"  # E6: seconds held for a long press
OPT_DOUBLE_PRESS = "double_press"  # E6: max seconds between the presses of a double press
OPT_STATUS_REQUEST = "status_request"  # E2: actuator answers "send confirmation" (FL62, FD62)
OPT_UNAVAILABLE_WHEN_SILENT = "unavailable_when_silent"  # E5: entities unavailable when silent
OPT_CALIBRATION = "calibration"  # I6 cover: passive | before_move
OPT_FIELDS = "fields"  # device added by EEP: the profile values shown as sensors
OPT_SOURCE = "source"  # I9 virtual sensor: the HA entity whose state is sent
OPT_WEATHER_TEMPERATURE = "weather_temperature"  # I9 weather: entity per value (optional)
OPT_WEATHER_WIND = "weather_wind"
OPT_WEATHER_RAIN = "weather_rain"
OPT_WEATHER_BRIGHTNESS = "weather_brightness"
WEATHER_SOURCES = (
    OPT_WEATHER_TEMPERATURE,
    OPT_WEATHER_WIND,
    OPT_WEATHER_RAIN,
    OPT_WEATHER_BRIGHTNESS,
)
OPT_WHEN_UNAVAILABLE = "when_unavailable"  # I9: source unavailable -> skip | safe value
OPT_PRIORITY = "priority"  # I9 contact: sent ahead of everything else (lock-out protection)
OPT_CHANNEL = "channel"  # VLD actuators: output channel (D2-01 I/O, D2-05 CHN)
OPT_WALL_SWITCH = "wall_switch"  # I4: rocker whose presses set the (assumed) on/off state
OPT_WALL_ON = "wall_on_button"  # I4: its button that switches on
OPT_WALL_OFF = "wall_off_button"  # I4: its button that switches off (same button = toggle)
OPT_ROUTING = "routing"  # cover: which sender moves it (controller | direction_rocker | both)
OPT_STATUS_CHANNEL = "status_channel"  # switch: "1" reports 0x70/0x50, "2" 0x30/0x10
OPT_TENTHS = "run_time_tenths"  # cover: controller run times in 100 ms (newer firmware)
OPT_ROCKER_ON = "rocker_on_button"  # rocker sender: the button it presses for on / up
OPT_ROCKER_OFF = "rocker_off_button"  # rocker sender: the button it presses for off / down
OPT_BUTTONS = "buttons"  # virtual rocker: the buttons it offers (all four when absent)


@dataclass(frozen=True, slots=True)
class SenderProfile:
    """One way to command an actuator, with its own sender ID (several in parallel)."""

    id: str  # central | rocker | controller | direction_rocker
    eep: EEPRef
    rorg: int
    teach_in: bytes  # 4BS teach-in telegram, or the rocker press that teaches it in
    switch_fn: Callable[[bool], bytes] | None = None  # on/off command, if the profile has one


def _std_switch(on: bool) -> bytes:
    """A5-38-08 command 2 in the standard variant: EDIM 0/100 % (raw 0/255), SW on/off."""
    profile = PROFILES["A5-38-08"]
    case = next(
        i for i, c in enumerate(profile.cases) if c.conditions and c.conditions[0].value == 2
    )
    return encode(profile, {"EDIM": 100 if on else 0, "RMP": 0, "LRNB": 1, "SW": int(on)}, case)


# E2: "request confirmation telegram" understood by FL62, FR62, FD62 (4BS from the central sender)
STATUS_REQUEST = bytes.fromhex("00000008")
ROCKER_PRESS_UP = bytes([0x70])  # B0: on / up
ROCKER_PRESS_DOWN = bytes([0x50])  # BI: off / down
# F6-02-01 R1 << 5 with the energy bow: A = left rocker, B = right; 0 = top, 1 = bottom
ROCKER_CODES = {"a1": 0x10, "a0": 0x30, "b1": 0x50, "b0": 0x70}
ROCKER_STATUS_PRESSED = 0x30
ROCKER_STATUS_RELEASED = 0x20

CENTRAL = SenderProfile(
    "central", EEPRef("A5-38-08", "eltako"), Rorg.BS4, switching.TEACH_IN, switching.encode_switch
)
# Permundo PSC132/PSC234: standard A5-38-08 command 2, confirmed by D2-01-09 status
PSC_CONTROLLER = SenderProfile(
    "controller", EEPRef("A5-38-08", "std"), Rorg.BS4, switching.TEACH_IN, _std_switch
)
ROCKER = SenderProfile("rocker", EEPRef("F6-02-01", "std"), Rorg.RPS, ROCKER_PRESS_UP)
CONTROLLER = SenderProfile("controller", EEPRef("H5-3F-7F", "eltako"), Rorg.BS4, shutter.TEACH_IN)
HEATING_CONTROLLER = SenderProfile(
    "controller", EEPRef("A5-10-06", "eltako"), Rorg.BS4, heating.TEACH_IN
)
# E8 cooling: a rocker press 0x50 (as a heating/cooling switch would send it, e.g. an FTS14EM
# input) puts Eltako heating actuators into cooling mode; it has to be repeated while cooling
COOLING_PRESS = bytes([0x50])
COOLING_SWITCH = SenderProfile("cooling", EEPRef("F6-02-01", "std"), Rorg.RPS, COOLING_PRESS)
DIRECTION_ROCKER = SenderProfile(
    "direction_rocker", EEPRef("F6-02-01", "std"), Rorg.RPS, ROCKER_PRESS_UP
)
# VLD actuators of other manufacturers learn by UTE: no teach-in telegram of our own, the
# teach-in button arms the answer to the actuator's UTE query (teach_in is empty)
UTE_TEACH_IN = b""
VLD_SWITCH = SenderProfile(
    "vld",
    EEPRef("D2-01-00", "std"),
    Rorg.VLD,
    UTE_TEACH_IN,
    lambda on: vld.encode_set_output(0, 100 if on else 0),
)
VLD_BLIND = SenderProfile("vld", EEPRef("D2-05-00", "std"), Rorg.VLD, UTE_TEACH_IN)
# I9 virtual sensors: HA sends as the sensor; the sender ID is also the device's ID
VIRTUAL_CONTACT = SenderProfile(
    "contact", EEPRef("D5-00-01", "std"), Rorg.BS1, virtual.CONTACT_TEACH_IN
)
VIRTUAL_TEMPERATURE = SenderProfile(
    "temperature", EEPRef("A5-02-05", "std"), Rorg.BS4, virtual.TEMPERATURE_TEACH_IN
)
VIRTUAL_MOTION = SenderProfile(
    "motion", EEPRef("A5-07-01", "std"), Rorg.BS4, virtual.MOTION_TEACH_IN
)
VIRTUAL_BRIGHTNESS = SenderProfile(
    "brightness", EEPRef("A5-06-01", "eltako"), Rorg.BS4, eltako_virtual.BRIGHTNESS_TEACH_IN
)
VIRTUAL_WEATHER = SenderProfile(
    "weather", EEPRef("A5-13-01", "eltako"), Rorg.BS4, eltako_virtual.WEATHER_TEACH_IN
)


GROUP_ELTAKO = "eltako"
GROUP_ENOCEAN = "enocean"  # other manufacturers
GROUP_VIRTUAL = "virtual"  # I9: Home Assistant sends as a sensor or rocker
GROUPS = (GROUP_ELTAKO, GROUP_ENOCEAN)  # catalog menus by category
CATEGORIES = ("lighting", "covers", "climate", "buttons", "sensors", "meters", "virtual")
GENERIC_EEP = "eep"  # model id of a device added by EEP alone (receive-only sensors)
CUSTOM = "custom"  # I8: model id of a device of the user's definitions


@dataclass(frozen=True, slots=True)
class DeviceModel:
    id: str
    receive: EEPRef | None
    platforms: tuple[Platform, ...]  # first is the default; a choice when more than one
    category: str = ""  # flow menu, one of CATEGORIES
    group: str = GROUP_ELTAKO
    base: str | None = None  # catalog entry whose behaviour this one shares
    senders: tuple[SenderProfile, ...] = ()  # first is the primary (required) profile
    any_sender: bool = False  # every profile commands alone: none required, at least one
    receive_extra: tuple[EEPRef, ...] = ()  # further profiles sent under the same ID
    interval: int | None = None  # expected seconds between telegrams; None = only on change
    manufacturer: str = "Eltako"
    options: tuple[str, ...] = ()
    examples: str = ""  # models shown in the flow

    @property
    def kind(self) -> str:
        """Behaviour key of the platforms: entries of other manufacturers share it."""
        return self.base or self.id

    @property
    def actuator(self) -> bool:
        return bool(self.senders)

    def sender_profile(self, profile_id: str) -> SenderProfile:
        return next(p for p in self.senders if p.id == profile_id)

    # kept for the first sender, used in diagnostics and the flow description
    @property
    def send(self) -> EEPRef | None:
        return self.senders[0].eep if self.senders else None


def _ref(text: str) -> EEPRef:
    return EEPRef.parse(text)


CATALOG: dict[str, DeviceModel] = {
    m.id: m
    for m in (
        DeviceModel(
            "switch",
            _ref("M5-38-08:eltako"),
            (Platform.LIGHT, Platform.SWITCH),
            category="lighting",
            senders=(ROCKER, CENTRAL),
            any_sender=True,
            options=(
                OPT_STATUS_REQUEST,
                OPT_INVERT,
                OPT_WALL_SWITCH,
                OPT_ROCKER_ON,
                OPT_STATUS_CHANNEL,
            ),
            examples="FSR61, FSR14, FL62, FSR71",
        ),
        DeviceModel(
            "dimmer",
            _ref("A5-38-08:eltako"),
            (Platform.LIGHT,),
            category="lighting",
            senders=(ROCKER, CENTRAL),
            any_sender=True,
            options=(OPT_STATUS_REQUEST, OPT_ROCKER_ON),
            examples="FUD14, FUD61, FD62",
        ),
        DeviceModel(
            "cover",
            _ref("G5-3F-7F:eltako"),
            (Platform.COVER,),
            category="covers",
            senders=(CONTROLLER, DIRECTION_ROCKER),
            options=(
                OPT_TIME_OPENS,
                OPT_TIME_CLOSES,
                OPT_VENT_TIME,
                OPT_TILT_TIME,
                OPT_ROUTING,
                OPT_CALIBRATION,
                OPT_TENTHS,
                OPT_ROCKER_ON,
            ),
            examples="FSB14, FSB61, FSB71, FJ62",
        ),
        DeviceModel(
            "psc",
            _ref("D2-01-09:std"),
            (Platform.SWITCH, Platform.LIGHT, Platform.SENSOR),
            category="lighting",
            group=GROUP_ENOCEAN,
            senders=(PSC_CONTROLLER,),
            # D2-01-09 state over ESP3, and over Eltako ESP2 gateways as ORG 0xD2
            receive_extra=(_ref("A5-12-01:std"), _ref("M5-38-08:eltako")),
            interval=600,  # power repeated every 10 min
            manufacturer="Permundo",
            examples="Permundo PSC132, PSC234",
        ),
        DeviceModel(
            "window_handle",
            _ref("F6-10-00:std"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            category="buttons",
            options=(OPT_INVERT,),
            examples="FTKE, FFG7B",
        ),
        DeviceModel(
            "contact",
            _ref("D5-00-01:std"),
            (Platform.BINARY_SENSOR,),
            category="buttons",
            options=(OPT_DEVICE_CLASS, OPT_INVERT),
            examples="FTK, FTKB",
        ),
        DeviceModel(
            "rocker",
            _ref("F6-02-01:std"),
            (Platform.EVENT,),
            category="buttons",
            options=(OPT_LONG_PRESS, OPT_DOUBLE_PRESS),
            examples="F4T55E, FT55, FT4F",
        ),
        DeviceModel(
            "rocker_contact",
            _ref("F6-02-01:std"),
            (Platform.BINARY_SENSOR,),
            category="buttons",
            options=(OPT_ON_BUTTON, OPT_OFF_BUTTON, OPT_DEVICE_CLASS, OPT_INVERT),
            examples="FTS14EM, FSM61, garage door controllers",
        ),
        DeviceModel(
            "meter",
            _ref("A5-12-01:eltako"),
            (Platform.SENSOR,),
            category="meters",
            interval=600,
            examples="FWZ12, FSDG14, DSZ14",
        ),
        DeviceModel(
            "gas_meter",
            _ref("A5-12-02:eltako"),
            (Platform.SENSOR,),
            category="meters",
            interval=600,
            examples="F3Z14D",
        ),
        DeviceModel(
            "water_meter",
            _ref("A5-12-03:eltako"),
            (Platform.SENSOR,),
            category="meters",
            interval=600,
            examples="F3Z14D",
        ),
        DeviceModel(
            "temp_humidity",
            _ref("A5-04-02:std"),
            (Platform.SENSOR,),
            category="sensors",
            interval=1800,
            examples="FAFT60, FFT65B",
        ),
        DeviceModel(
            "fbh",
            _ref("A5-08-01:eltako"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            category="sensors",
            interval=1800,
            examples="FBH65, FBH65S, FABH65S",
        ),
        DeviceModel(
            "voc",
            _ref("A5-09-05:std"),
            (Platform.SENSOR,),
            category="sensors",
            examples="FLT58",
        ),
        DeviceModel(
            "tvoc",
            _ref("A5-09-0C:std"),
            (Platform.SENSOR,),
            category="sensors",
            examples="FLGTF",
        ),
        DeviceModel(
            "multisensor",
            _ref("D2-14-40:std"),
            (Platform.SENSOR,),
            category="sensors",
            examples="FMS55SB",
        ),
        DeviceModel(
            "multisensor_contact",
            _ref("D2-14-41:std"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            category="sensors",
            options=(OPT_DEVICE_CLASS, OPT_INVERT),
            examples="FMMS44SB",
        ),
        DeviceModel(
            "digital_input",
            _ref("A5-30-01:std"),
            (Platform.BINARY_SENSOR,),
            category="buttons",
            options=(OPT_DEVICE_CLASS, OPT_INVERT),
            examples="FSM60B",
        ),
        DeviceModel(
            "digital_inputs",
            _ref("A5-30-03:std"),
            (Platform.BINARY_SENSOR, Platform.SENSOR),
            category="buttons",
            examples="FHMB",
        ),
        DeviceModel(
            "co2",
            _ref("A5-09-04:std"),
            (Platform.SENSOR,),
            category="sensors",
            interval=1800,
            examples="FCO2TF65",
        ),
        DeviceModel(
            "heating_actuator",
            _ref("M5-10-06:eltako"),
            (Platform.CLIMATE, Platform.SENSOR),
            category="climate",
            senders=(HEATING_CONTROLLER, COOLING_SWITCH),
            options=(OPT_TEMPERATURE_SENSOR, OPT_SEND_INTERVAL),
            examples="FHK14, FAE14, F4HK14, FHK61",
        ),
        DeviceModel(
            "room_controller",
            _ref("A5-10-06:eltako"),
            (Platform.CLIMATE, Platform.SENSOR),
            category="climate",
            interval=1800,
            examples="FUTH, FTR65HS, FTAF55D",
        ),
        DeviceModel(
            "weather",
            _ref("A5-13-01:eltako"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            category="sensors",
            interval=600,
            examples="FWS61, FWG14",
        ),
        # other manufacturers: same behaviour as the Eltako entry named in base
        DeviceModel(
            "enocean_rocker",
            _ref("F6-02-01:std"),
            (Platform.EVENT,),
            category="buttons",
            group=GROUP_ENOCEAN,
            base="rocker",
            options=(OPT_LONG_PRESS, OPT_DOUBLE_PRESS),
            manufacturer="EnOcean",
            examples="NodOn, PEHA, Jung",
        ),
        DeviceModel(
            "enocean_window_handle",
            _ref("F6-10-00:std"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            category="buttons",
            group=GROUP_ENOCEAN,
            base="window_handle",
            manufacturer="EnOcean",
            options=(OPT_INVERT,),
            examples="Hoppe SecuSignal",
        ),
        DeviceModel(
            "enocean_contact",
            _ref("D5-00-01:std"),
            (Platform.BINARY_SENSOR,),
            category="buttons",
            group=GROUP_ENOCEAN,
            base="contact",
            options=(OPT_DEVICE_CLASS, OPT_INVERT),
            manufacturer="EnOcean",
            examples="NodOn SDO",
        ),
        DeviceModel(
            "vld_switch",
            _ref("D2-01-00:std"),
            (Platform.LIGHT, Platform.SWITCH),
            category="lighting",
            group=GROUP_ENOCEAN,
            senders=(VLD_SWITCH,),
            options=(OPT_CHANNEL, OPT_STATUS_REQUEST),
            manufacturer="EnOcean",
            examples="NodOn SIN-2-1-01",
        ),
        DeviceModel(
            "vld_cover",
            _ref("D2-05-00:std"),
            (Platform.COVER,),
            category="covers",
            group=GROUP_ENOCEAN,
            senders=(VLD_BLIND,),
            options=(OPT_CHANNEL, OPT_STATUS_REQUEST),
            manufacturer="EnOcean",
            examples="NodOn SIN-2-RS-01",
        ),
        DeviceModel(
            "virtual_contact",
            None,
            (Platform.BUTTON, Platform.SENSOR),
            category="virtual",
            group=GROUP_VIRTUAL,
            senders=(VIRTUAL_CONTACT,),
            manufacturer="Home Assistant",
            options=(OPT_SOURCE, OPT_INVERT, OPT_SEND_INTERVAL, OPT_WHEN_UNAVAILABLE, OPT_PRIORITY),
            examples="FTK",
        ),
        DeviceModel(
            "virtual_temperature",
            None,
            (Platform.BUTTON, Platform.SENSOR),
            category="virtual",
            group=GROUP_VIRTUAL,
            senders=(VIRTUAL_TEMPERATURE,),
            manufacturer="Home Assistant",
            options=(OPT_SOURCE, OPT_SEND_INTERVAL),
            examples="FTR55",
        ),
        DeviceModel(
            "virtual_motion",
            None,
            (Platform.BUTTON, Platform.SENSOR),
            category="virtual",
            group=GROUP_VIRTUAL,
            senders=(VIRTUAL_MOTION,),
            manufacturer="Home Assistant",
            options=(OPT_SOURCE, OPT_INVERT, OPT_SEND_INTERVAL),
            examples="FBH",
        ),
        DeviceModel(
            "virtual_brightness",
            None,
            (Platform.BUTTON, Platform.SENSOR),
            category="virtual",
            group=GROUP_VIRTUAL,
            senders=(VIRTUAL_BRIGHTNESS,),
            manufacturer="Home Assistant",
            options=(OPT_SOURCE, OPT_SEND_INTERVAL),
            examples="FAH60",
        ),
        DeviceModel(
            "virtual_weather",
            None,
            (Platform.BUTTON, Platform.SENSOR),
            category="virtual",
            group=GROUP_VIRTUAL,
            senders=(VIRTUAL_WEATHER,),
            manufacturer="Home Assistant",
            options=(*WEATHER_SOURCES, OPT_SEND_INTERVAL),
            examples="FWS61",
        ),
        DeviceModel(
            "virtual_scene",
            None,
            (Platform.BUTTON,),
            category="virtual",
            group=GROUP_VIRTUAL,
            senders=(ROCKER,),
            manufacturer="Home Assistant",
            examples="FT55 as scene button",
        ),
        DeviceModel(
            "virtual_rocker",
            None,
            (Platform.BUTTON,),
            category="virtual",
            group=GROUP_VIRTUAL,
            senders=(ROCKER,),
            manufacturer="Home Assistant",
            options=(OPT_BUTTONS,),
            examples="FT55, FTS14EM",
        ),
    )
}

# Flow "by EEP": standard profiles become a generic receive-only device; the other choices
# open the catalog entry that decodes that profile. Option value -> EEP reference.
# FEATURED_EEPS have a translated name and come first; phase 5 adds every other standard
# profile (labelled with its code) after them.
FEATURED_EEPS = (
    "A5-04-02",
    "A5-08-01",
    "A5-09-04",
    "A5-10-06",
    "A5-12-01",
    "A5-12-02",
    "A5-12-03",
    "A5-13-01",
    "A5-13-02",
)
EEP_TO_MODEL: dict[str, str] = {
    "std_d2_01_09": "psc",
    "std_d5_00_01": "enocean_contact",
    "std_f6_02_01": "enocean_rocker",
    "std_f6_10_00": "enocean_window_handle",
    "eltako_m5_38_08": "switch",
    "eltako_a5_38_08": "dimmer",
    "eltako_g5_3f_7f": "cover",
    "eltako_a5_08_01": "fbh",
    "eltako_m5_10_06": "heating_actuator",
    "eltako_a5_10_06": "room_controller",
    "eltako_a5_12_01": "meter",
    "eltako_a5_12_02": "gas_meter",
    "eltako_a5_12_03": "water_meter",
    "eltako_a5_13_01": "weather",
}


def eep_option(ref: EEPRef) -> str:
    """Selector value of an EEP reference: A5-04-02:std -> std_a5_04_02."""
    return f"{ref.variant}_{ref.eep.lower().replace('-', '_')}"


def _option_ref(option: str) -> EEPRef:
    variant, _, eep = option.partition("_")
    return EEPRef.parse(f"{eep.replace('_', '-')}:{variant}")


GENERIC_SKIPPED_FIELDS = {"LRN", "LRNB"}  # teach-in bits are no reading


def _readable(eep: str) -> bool:
    return any(
        f.shortcut not in GENERIC_SKIPPED_FIELDS
        for case in PROFILES[eep].cases
        for f in case.fields
    )


_BY_CATALOG = {_option_ref(o).eep for o in EEP_TO_MODEL if o.startswith("std_")}
GENERIC_EEPS: tuple[str, ...] = (
    *FEATURED_EEPS,
    *sorted(
        e for e in PROFILES if e not in FEATURED_EEPS and e not in _BY_CATALOG and _readable(e)
    ),
)
# translated choices first (flow texts), then every other standard profile by its code
FEATURED_OPTIONS: tuple[str, ...] = (
    *(eep_option(EEPRef(eep, "std")) for eep in FEATURED_EEPS),
    *EEP_TO_MODEL,
)
EEP_OPTIONS: dict[str, EEPRef] = {
    **{
        eep_option(EEPRef(eep, "std")): EEPRef(eep, "std")
        for eep in GENERIC_EEPS[: len(FEATURED_EEPS)]
    },
    **{option: _option_ref(option) for option in EEP_TO_MODEL},
    **{
        eep_option(EEPRef(eep, "std")): EEPRef(eep, "std")
        for eep in GENERIC_EEPS[len(FEATURED_EEPS) :]
    },
}


def eep_choice(text: str) -> str | None:
    """Option value of a selection or of a typed code ("A5-04-02", "a50402"); None if unknown."""
    if text in EEP_OPTIONS:
        return text
    digits = "".join(c for c in text.upper() if c.isalnum())
    if len(digits) == 6:
        option = eep_option(EEPRef(f"{digits[:2]}-{digits[2:4]}-{digits[4:]}", "std"))
        if option in EEP_OPTIONS:
            return option
    return None


def generic_fields(eep: str) -> list[tuple[str, Field]]:
    """(sensor key, field) for every value of a standard profile, first case wins."""
    seen: dict[str, Field] = {}
    for case in PROFILES[eep].cases:
        for f in case.fields:
            if f.shortcut not in GENERIC_SKIPPED_FIELDS:
                seen.setdefault(f.shortcut, f)
    return [(f"eep_{_key(shortcut)}", f) for shortcut, f in seen.items()]


def custom_key(shortcut: str) -> str:
    """I8: entity key of a field of the user's definition."""
    return f"custom_{_key(shortcut)}"


def _key(shortcut: str) -> str:
    """Entity key part: "TMP" -> "tmp", "Acceleration Status" -> "acceleration_status"."""
    return "_".join("".join(c if c.isalnum() else " " for c in shortcut.lower()).split())


def generic_model(ref: EEPRef) -> DeviceModel:
    """Receive-only device with one sensor per field of a standard profile."""
    return DeviceModel(
        GENERIC_EEP, ref, (Platform.SENSOR,), group=GROUP_ENOCEAN, manufacturer="EnOcean"
    )


def custom_model(definition: CustomDevice) -> DeviceModel:
    """I8: receive-only device with the sensors of the user's definition."""
    platforms = (
        *((Platform.SENSOR,) if definition.sensors else ()),
        *((Platform.BINARY_SENSOR,) if definition.binary_sensors else ()),
    )
    return DeviceModel(
        CUSTOM,
        definition.eep,
        platforms,
        group=GROUP_ENOCEAN,
        interval=definition.interval,
        manufacturer=definition.manufacturer,
        examples=definition.name,
    )


def custom_definition(data: Mapping[str, Any]) -> CustomDevice | None:
    return DEFINITIONS.get(data.get(CONF_CUSTOM, "")) if data[CONF_MODEL] == CUSTOM else None


def model_for(data: Mapping[str, Any]) -> DeviceModel:
    """Catalog entry of a device subentry, or its generic model when added by EEP.

    A device of the user's definitions falls back to the generic model of its EEP when the
    definition is gone (or broken), so it keeps its radio and its raw data.
    """
    if data[CONF_MODEL] == CUSTOM:
        if (definition := custom_definition(data)) is not None:
            return custom_model(definition)
        return generic_model(EEPRef.parse(data[CONF_EEP]))
    if data[CONF_MODEL] == GENERIC_EEP:
        return generic_model(EEPRef.parse(data[CONF_EEP]))
    return CATALOG[data[CONF_MODEL]]


def models_in(group: str, category: str) -> list[DeviceModel]:
    return [m for m in CATALOG.values() if m.group == group and m.category == category]


def categories_of(group: str) -> list[str]:
    return [c for c in CATEGORIES if models_in(group, c)]


# Platforms an entry may need; actuators additionally get a teach-in button.
PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
)
