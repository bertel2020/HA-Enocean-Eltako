"""Device catalog: device kinds with receive/send profiles and platforms.

Every model names its EEP variant explicitly (EEPRef), there is no silent default.
Phase 2 covers the device kinds of the reference system; names are translated
(config_subentries.device.step.user selector "model").
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.const import Platform

from .protocol.eep import EEPRef
from .protocol.eep.eltako import heating, shutter, switching
from .protocol.eep.model import encode
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
OPT_UNAVAILABLE_WHEN_SILENT = "unavailable_when_silent"  # E5: entities unavailable when silent
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
DIRECTION_ROCKER = SenderProfile(
    "direction_rocker", EEPRef("F6-02-01", "std"), Rorg.RPS, ROCKER_PRESS_UP
)


@dataclass(frozen=True, slots=True)
class DeviceModel:
    id: str
    receive: EEPRef | None
    platforms: tuple[Platform, ...]  # first is the default; a choice when more than one
    senders: tuple[SenderProfile, ...] = ()  # first is the primary (required) profile
    receive_extra: tuple[EEPRef, ...] = ()  # further profiles sent under the same ID
    interval: int | None = None  # expected seconds between telegrams; None = only on change
    manufacturer: str = "Eltako"
    options: tuple[str, ...] = ()
    examples: str = ""  # Eltako models, shown in the flow

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
            senders=(CENTRAL, ROCKER),
            examples="FSR61, FSR14, FL62, FSR71",
        ),
        DeviceModel(
            "dimmer",
            _ref("A5-38-08:eltako"),
            (Platform.LIGHT,),
            senders=(CENTRAL, ROCKER),
            examples="FUD14, FUD61, FD62",
        ),
        DeviceModel(
            "cover",
            _ref("G5-3F-7F:eltako"),
            (Platform.COVER,),
            senders=(CONTROLLER, DIRECTION_ROCKER),
            options=(OPT_TIME_OPENS, OPT_TIME_CLOSES, OPT_ROUTING),
            examples="FSB14, FSB61, FSB71, FJ62",
        ),
        DeviceModel(
            "psc",
            _ref("D2-01-09:std"),
            (Platform.SWITCH, Platform.LIGHT, Platform.SENSOR),
            senders=(PSC_CONTROLLER,),
            # D2-01-09 needs an ESP3 gateway; behind an ESP2 gateway (FAM-USB) the state
            # comes only from RPS 0x70/0x50 telegrams as today in the old integration
            receive_extra=(_ref("A5-12-01:std"), _ref("M5-38-08:eltako")),
            interval=600,  # power repeated every 10 min
            manufacturer="Permundo",
            examples="Permundo PSC132, PSC234",
        ),
        DeviceModel(
            "window_handle",
            _ref("F6-10-00:std"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            examples="FTKE, FFG7B, Hoppe",
        ),
        DeviceModel(
            "contact",
            _ref("D5-00-01:std"),
            (Platform.BINARY_SENSOR,),
            options=(OPT_DEVICE_CLASS, OPT_INVERT),
            examples="FTK, FTKB, FTS14EM",
        ),
        DeviceModel(
            "rocker", _ref("F6-02-01:std"), (Platform.EVENT,), examples="F4T55E, FT55, NodOn"
        ),
        DeviceModel(
            "rocker_contact",
            _ref("F6-02-01:std"),
            (Platform.BINARY_SENSOR,),
            options=(OPT_ON_BUTTON, OPT_OFF_BUTTON, OPT_DEVICE_CLASS, OPT_INVERT),
            examples="FTS14EM, FSM61, garage door controllers",
        ),
        DeviceModel(
            "meter",
            _ref("A5-12-01:eltako"),
            (Platform.SENSOR,),
            interval=600,
            examples="FWZ12, FSDG14, DSZ14",
        ),
        DeviceModel(
            "temp_humidity",
            _ref("A5-04-02:std"),
            (Platform.SENSOR,),
            interval=1800,
            examples="FAFT60, FFT65B",
        ),
        DeviceModel(
            "fbh",
            _ref("A5-08-01:eltako"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            interval=1800,
            examples="FBH65, FBH65S, FABH65S",
        ),
        DeviceModel(
            "co2", _ref("A5-09-04:std"), (Platform.SENSOR,), interval=1800, examples="FCO2TF65"
        ),
        DeviceModel(
            "heating_actuator",
            _ref("M5-10-06:eltako"),
            (Platform.CLIMATE, Platform.SENSOR),
            senders=(HEATING_CONTROLLER,),
            options=(OPT_TEMPERATURE_SENSOR, OPT_SEND_INTERVAL),
            examples="FHK14, FAE14, F4HK14, FHK61",
        ),
        DeviceModel(
            "room_controller",
            _ref("A5-10-06:eltako"),
            (Platform.CLIMATE, Platform.SENSOR),
            interval=1800,
            examples="FUTH, FTR65HS, FTAF55D",
        ),
        DeviceModel(
            "weather",
            _ref("A5-13-01:eltako"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            interval=600,
            examples="FWS61, FWG14",
        ),
    )
}

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
