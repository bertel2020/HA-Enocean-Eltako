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

from .const import CONF_EEP, CONF_MODEL
from .protocol.eep import EEPRef
from .protocol.eep.eltako import heating, shutter, switching
from .protocol.eep.model import Field, encode
from .protocol.eep.std.profiles import PROFILES
from .protocol.telegram import Rorg

OPT_PLATFORM = "platform"
OPT_TIME_OPENS = "time_opens"
OPT_TIME_CLOSES = "time_closes"
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
OPT_ROUTING = "routing"  # cover: which sender moves it (controller | direction_rocker | both)


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


GROUP_ELTAKO = "eltako"
GROUP_ENOCEAN = "enocean"  # other manufacturers
GROUPS = (GROUP_ELTAKO, GROUP_ENOCEAN)
CATEGORIES = ("lighting", "covers", "climate", "buttons", "sensors", "meters")
GENERIC_EEP = "eep"  # model id of a device added by EEP alone (receive-only sensors)


@dataclass(frozen=True, slots=True)
class DeviceModel:
    id: str
    receive: EEPRef | None
    platforms: tuple[Platform, ...]  # first is the default; a choice when more than one
    category: str = ""  # flow menu, one of CATEGORIES
    group: str = GROUP_ELTAKO
    base: str | None = None  # catalog entry whose behaviour this one shares
    senders: tuple[SenderProfile, ...] = ()  # first is the primary (required) profile
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
            senders=(CENTRAL, ROCKER),
            options=(OPT_STATUS_REQUEST,),
            examples="FSR61, FSR14, FL62, FSR71",
        ),
        DeviceModel(
            "dimmer",
            _ref("A5-38-08:eltako"),
            (Platform.LIGHT,),
            category="lighting",
            senders=(CENTRAL, ROCKER),
            options=(OPT_STATUS_REQUEST,),
            examples="FUD14, FUD61, FD62",
        ),
        DeviceModel(
            "cover",
            _ref("G5-3F-7F:eltako"),
            (Platform.COVER,),
            category="covers",
            senders=(CONTROLLER, DIRECTION_ROCKER),
            options=(OPT_TIME_OPENS, OPT_TIME_CLOSES, OPT_ROUTING, OPT_CALIBRATION),
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
    )
}

# Flow "by EEP": standard sensor profiles become a generic receive-only device; the other
# choices open the catalog entry that decodes that profile. Option value -> EEP reference.
GENERIC_EEPS = (
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


EEP_OPTIONS: dict[str, EEPRef] = {
    **{eep_option(EEPRef(eep, "std")): EEPRef(eep, "std") for eep in GENERIC_EEPS},
    **{option: _option_ref(option) for option in EEP_TO_MODEL},
}


GENERIC_SKIPPED_FIELDS = {"LRN", "LRNB"}  # teach-in bits are no reading


def generic_fields(eep: str) -> list[tuple[str, Field]]:
    """(sensor key, field) for every value of a standard profile, first case wins."""
    seen: dict[str, Field] = {}
    for case in PROFILES[eep].cases:
        for f in case.fields:
            if f.shortcut not in GENERIC_SKIPPED_FIELDS:
                seen.setdefault(f.shortcut, f)
    return [(f"eep_{shortcut.lower()}", f) for shortcut, f in seen.items()]


def generic_model(ref: EEPRef) -> DeviceModel:
    """Receive-only device with one sensor per field of a standard profile."""
    return DeviceModel(
        GENERIC_EEP, ref, (Platform.SENSOR,), group=GROUP_ENOCEAN, manufacturer="EnOcean"
    )


def model_for(data: Mapping[str, Any]) -> DeviceModel:
    """Catalog entry of a device subentry, or its generic model when added by EEP."""
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
