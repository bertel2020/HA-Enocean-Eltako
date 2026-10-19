"""Device catalog: device kinds with receive/send profiles and platforms.

Every model names its EEP variant explicitly (EEPRef), there is no silent default.
Phase 2 covers the device kinds of the reference system; names are translated
(config_subentries.device.step.user selector "model").
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import Platform

from .protocol.eep import EEPRef
from .protocol.eep.eltako import shutter, switching
from .protocol.telegram import Rorg

OPT_PLATFORM = "platform"
OPT_TIME_OPENS = "time_opens"
OPT_TIME_CLOSES = "time_closes"
OPT_INVERT = "invert"
OPT_DEVICE_CLASS = "device_class"


@dataclass(frozen=True, slots=True)
class DeviceModel:
    id: str
    receive: EEPRef | None
    platforms: tuple[Platform, ...]  # first is the default; a choice when more than one
    send: EEPRef | None = None
    send_rorg: int | None = None
    teach_in: bytes | None = None  # telegram the teach-in button sends
    options: tuple[str, ...] = ()
    examples: str = ""  # Eltako models, shown in the flow

    @property
    def actuator(self) -> bool:
        return self.send is not None


def _ref(text: str) -> EEPRef:
    return EEPRef.parse(text)


CATALOG: dict[str, DeviceModel] = {
    m.id: m
    for m in (
        DeviceModel(
            "switch",
            _ref("M5-38-08:eltako"),
            (Platform.LIGHT, Platform.SWITCH),
            send=_ref("A5-38-08:eltako"),
            send_rorg=Rorg.BS4,
            teach_in=switching.TEACH_IN,
            examples="FSR61, FSR14, FL62, FSR71",
        ),
        DeviceModel(
            "dimmer",
            _ref("A5-38-08:eltako"),
            (Platform.LIGHT,),
            send=_ref("A5-38-08:eltako"),
            send_rorg=Rorg.BS4,
            teach_in=switching.TEACH_IN,
            examples="FUD14, FUD61, FD62",
        ),
        DeviceModel(
            "cover",
            _ref("G5-3F-7F:eltako"),
            (Platform.COVER,),
            send=_ref("H5-3F-7F:eltako"),
            send_rorg=Rorg.BS4,
            teach_in=shutter.TEACH_IN,
            options=(OPT_TIME_OPENS, OPT_TIME_CLOSES),
            examples="FSB14, FSB61, FSB71, FJ62",
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
            "meter", _ref("A5-12-01:eltako"), (Platform.SENSOR,), examples="FWZ12, FSDG14, DSZ14"
        ),
        DeviceModel(
            "temp_humidity", _ref("A5-04-02:std"), (Platform.SENSOR,), examples="FAFT60, FFT65B"
        ),
        DeviceModel(
            "fbh",
            _ref("A5-08-01:eltako"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            examples="FBH65, FBH65S, FABH65S",
        ),
        DeviceModel("co2", _ref("A5-09-04:std"), (Platform.SENSOR,), examples="FCO2TF65"),
        DeviceModel(
            "room_controller",
            _ref("A5-10-06:eltako"),
            (Platform.SENSOR,),
            examples="FUTH, FTR65HS, FTAF55D",
        ),
        DeviceModel(
            "weather",
            _ref("A5-13-01:eltako"),
            (Platform.SENSOR, Platform.BINARY_SENSOR),
            examples="FWS61, FWG14",
        ),
    )
}

# Platforms an entry may need; actuators additionally get a teach-in button.
PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.COVER,
    Platform.EVENT,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
)
